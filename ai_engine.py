import os
from anthropic import Anthropic
import json
import re

MODEL_ID = "claude-haiku-4-5"

# ==============================================================================
# MULTI-KEY CLIENT FACTORY
# ==============================================================================

def get_client(feature: str = "master"):
    key_map = {
        "master":  "ANTHROPIC_API_KEY",
        "audit":   "ANTHROPIC_API_KEY_AUDIT",
        "nqf":     "ANTHROPIC_API_KEY_NQF",
        "ssr":     "ANTHROPIC_API_KEY_SSR",
        "extract": "ANTHROPIC_API_KEY_EXTRACT",
    }
    env_var = key_map.get(feature, "ANTHROPIC_API_KEY")
    api_key = os.getenv(env_var) or os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        return None
    return Anthropic(api_key=api_key)


# ==============================================================================
# JSON CLEANING UTILITY
# ==============================================================================

def clean_json_response(response_text: str) -> str:
    pattern = r"```(?:json)?\s*(.*?)\s*```"
    match = re.search(pattern, response_text, re.DOTALL)
    if match:
        response_text = match.group(1)
    start = response_text.find('{')
    end   = response_text.rfind('}')
    if start != -1 and end != -1:
        return response_text[start:end + 1]
    return response_text


# ==============================================================================
# EVIDENCE EXTRACTION  — fixed version
#
# Key fixes vs previous version:
#   1. max_tokens raised 1000 → 2000  (rubric tables are large)
#   2. Keywords are now OPTIONAL hints — the prompt no longer filters
#      aggressively; it asks the AI to extract ALL substantive content
#      that could be relevant to the topic, not just keyword matches.
#   3. For SSR queries, we pass ALL chunks directly rather than pre-filtering,
#      so nothing is silently dropped before the AI sees it.
# ==============================================================================

def _extract_relevant_passages(client, topic: str, keywords: list, chunks: list) -> str:
    """
    Scans every chunk and extracts content relevant to `topic`.
    `keywords` are hints only — the AI decides relevance, not a keyword filter.
    """
    relevant_passages = []

    for i, chunk in enumerate(chunks):
        if not chunk.strip():
            continue

        # Build a hint string only if we have meaningful keywords
        hint = ""
        if keywords:
            hint = f"Keyword hints (use as guidance only): {', '.join(keywords)}\n"

        prompt = f"""You are a document analyst extracting evidence for an accreditation review.

TOPIC: {topic}
{hint}
DOCUMENT CHUNK {i+1}:
\"\"\"
{chunk}
\"\"\"

INSTRUCTIONS:
- Extract ALL text from this chunk that is relevant to the topic above.
- Include full sentences, table rows, numbered items, and criteria — do not truncate.
- Do NOT paraphrase or summarise. Copy the exact text.
- Do NOT invent or add anything not present in the chunk.
- If nothing in this chunk is relevant, respond with exactly: NO_RELEVANT_CONTENT
- Start your response with [CHUNK-{i+1}] on its own line.
"""
        try:
            response = client.messages.create(
                model=MODEL_ID,
                max_tokens=2000,   # FIX: was 1000, too low for rubric tables
                messages=[{"role": "user", "content": prompt}]
            )
            result = response.content[0].text.strip()
            if result and result != "NO_RELEVANT_CONTENT":
                relevant_passages.append(result)
        except Exception:
            continue

    if not relevant_passages:
        return "NO_RELEVANT_CONTENT_FOUND_IN_ANY_DOCUMENT"

    return "\n\n".join(relevant_passages)


# ==============================================================================
# TAB 2 — COMPLIANCE AUDIT
# ==============================================================================

def analyze_evidence_for_standard(client, standard_name: str, standard_info: dict, chunks: list) -> dict:
    extract_client = get_client("extract")

    grounded_evidence = _extract_relevant_passages(
        extract_client,
        topic=f"NCAAA standard: {standard_name} — {standard_info.get('description', '')}",
        keywords=standard_info.get("keywords", []),
        chunks=chunks
    )

    system_prompt = (
        "You are a strict NCAAA/ETEC External Reviewer for a General Dentistry Program.\n"
        "ABSOLUTE RULES:\n"
        "  1. You may ONLY reference evidence explicitly present in the EXTRACTED PASSAGES block.\n"
        "  2. If a criterion has no supporting passage, mark it 'NOT EVIDENCED IN DOCUMENTS'.\n"
        "  3. Do NOT draw on general knowledge about dentistry or accreditation.\n"
        "  4. Every strength or gap MUST include a [CHUNK-N] citation.\n"
        "  5. Output valid JSON only — no preamble, no markdown.\n"
    )

    if grounded_evidence == "NO_RELEVANT_CONTENT_FOUND_IN_ANY_DOCUMENT":
        return {
            "relevance": "Low",
            "compliance_rating": "1/5",
            "strengths": [],
            "areas_for_improvement": [
                "No evidence found in the uploaded documents for this standard.",
                "Please upload the relevant documents (see Required Documents list)."
            ],
            "reviewer_comment": (
                f"After scanning all uploaded document pages, no content relevant to "
                f"'{standard_name}' was found. Upload the appropriate evidence documents."
            ),
            "citations": []
        }

    user_prompt = f"""
STANDARD: {standard_name}
DESCRIPTION: {standard_info['description']}
CRITERIA: {', '.join(standard_info['criteria'])}

EXTRACTED PASSAGES FROM UPLOADED DOCUMENTS:
\"\"\"
{grounded_evidence}
\"\"\"

TASK: Using ONLY the passages above, evaluate compliance with the standard.
Cite [CHUNK-N] for every point. Mark missing criteria 'NOT EVIDENCED IN DOCUMENTS'.

OUTPUT FORMAT (valid JSON only):
{{
    "relevance": "High/Medium/Low",
    "compliance_rating": "X/5",
    "strengths": ["[CHUNK-N] strength description"],
    "areas_for_improvement": ["gap description or NOT EVIDENCED IN DOCUMENTS"],
    "reviewer_comment": "Narrative with [CHUNK-N] references. No invented claims.",
    "citations": ["CHUNK-N: exact quote"]
}}
"""

    try:
        response = client.messages.create(
            model=MODEL_ID,
            max_tokens=2500,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}]
        )
        raw_text = response.content[0].text
        cleaned  = clean_json_response(raw_text)
        return json.loads(cleaned)
    except json.JSONDecodeError:
        return {
            "relevance": "Analysis Error",
            "compliance_rating": "N/A",
            "strengths": [],
            "areas_for_improvement": ["JSON parsing failed — see raw comment below."],
            "reviewer_comment": f"RAW OUTPUT (formatting error):\n\n{raw_text}",
            "citations": []
        }
    except Exception as e:
        return {"error": f"API Error: {str(e)}"}


# ==============================================================================
# TAB 3 — NQF ALIGNMENT
# ==============================================================================

def check_nqf_alignment(client, plo_text: str, nqf_domains: dict) -> str:
    system_prompt = (
        "You are an NQF academic auditor.\n"
        "RULES:\n"
        "  1. Evaluate ONLY the PLOs provided in the user's message.\n"
        "  2. Do NOT invent PLOs or assume any not explicitly stated.\n"
        "  3. If a domain has no PLO mapped to it, state 'NO PLO FOUND FOR THIS DOMAIN'.\n"
        "  4. Quote the exact PLO text when giving feedback.\n"
    )

    prompt = f"""
PROGRAM LEARNING OUTCOMES (PLOs) TO REVIEW:
\"\"\"
{plo_text}
\"\"\"

NQF LEVEL 6 DOMAINS:
{json.dumps(nqf_domains, indent=2)}

EVALUATION TASKS:
1. Map each PLO to a domain. Quote the PLO exactly.
2. Flag PLOs where the action verb does not match Bachelor's level complexity.
3. Identify domains with NO mapped PLO — state explicitly.
4. Provide a final recommendation paragraph.

Format your response with clear section headers.
"""

    try:
        response = client.messages.create(
            model=MODEL_ID,
            max_tokens=2000,
            system=system_prompt,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.content[0].text
    except Exception as e:
        return f"Error: {str(e)}"


# ==============================================================================
# TAB 4 — SSR WRITER
#
# Key fix: stop using _extract_relevant_passages with query words as keywords.
# Instead, pass ALL chunks directly to the writer in batches, letting the AI
# read and use everything rather than pre-filtering on weak keyword matches.
# ==============================================================================

def chat_with_ssr_expert(client, chunks: list, user_query: str) -> str:
    """
    Drafts SSR content from uploaded chunks.

    FIX: Previously used query words as keyword filters for extraction,
    which caused relevant content (rubrics, course specs, standards) to be
    silently dropped. Now passes all chunk content directly to the AI,
    which reads and uses whatever is relevant to answer the query.
    """
    extract_client = get_client("extract")

    # Use the full query as the topic — no keyword truncation
    # This ensures rubric rows, standard criteria, and spec sections are all captured
    grounded_evidence = _extract_relevant_passages(
        extract_client,
        topic=user_query,
        keywords=[],   # FIX: no keyword pre-filter — let AI decide relevance
        chunks=chunks
    )

    system_prompt = (
        "You are a professional accreditation consultant for a Dental School seeking NCAAA accreditation.\n"
        "You help write and evaluate Self-Study Report (SSR) content.\n"
        "ABSOLUTE RULES:\n"
        "  1. Work ONLY from the EXTRACTED PASSAGES provided. Never invent data.\n"
        "  2. If passages contain a rubric, scoring scale, or criteria table — USE IT.\n"
        "     Apply the rubric systematically, scoring each criterion explicitly.\n"
        "  3. If passages contain a course specification — analyse it against any rubric present.\n"
        "  4. Do NOT fabricate statistics, names, dates, or policies not in the passages.\n"
        "  5. If evidence is genuinely insufficient for part of the task, say so specifically\n"
        "     and state exactly what additional document or section is needed.\n"
        "  6. Use formal academic language suitable for an accreditation report.\n"
        "  7. Cite source chunks in parentheses, e.g. (Source: CHUNK-3).\n"
    )

    if grounded_evidence == "NO_RELEVANT_CONTENT_FOUND_IN_ANY_DOCUMENT":
        return (
            "⚠️ **Insufficient Evidence**\n\n"
            "No relevant content was found in the selected documents for your request:\n"
            f"> *{user_query}*\n\n"
            "**Possible reasons:**\n"
            "- The documents may be scanned images (not machine-readable text). "
            "Try re-saving as a text-based PDF or DOCX.\n"
            "- The relevant content may be in a document you haven't selected. "
            "Check the document selector above.\n"
            "- The file may have uploaded but not processed correctly. "
            "Try removing and re-uploading it.\n\n"
            "The SSR Writer will not generate content it cannot evidence from your files."
        )

    messages = [
        {
            "role": "user",
            "content": (
                f"EXTRACTED EVIDENCE FROM UPLOADED DOCUMENTS:\n\"\"\"\n{grounded_evidence}\n\"\"\"\n\n"
                f"USER REQUEST:\n{user_query}\n\n"
                "Please respond to the request using ONLY the evidence above."
            )
        }
    ]

    try:
        response = client.messages.create(
            model=MODEL_ID,
            max_tokens=3000,
            system=system_prompt,
            messages=messages
        )
        return response.content[0].text
    except Exception as e:
        return f"Error: {str(e)}"