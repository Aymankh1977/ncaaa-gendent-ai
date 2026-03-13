import os
from anthropic import Anthropic
import json
import re

# --- MODEL: Updated to current supported model ---
MODEL_ID = "claude-haiku-4-5"

# ==============================================================================
# MULTI-KEY CLIENT FACTORY
# Each feature uses its own API key to isolate usage and avoid rate limits.
# Keys are read from environment variables. Fall back to the master key if
# a dedicated key is not set.
# ==============================================================================

def get_client(feature: str = "master") -> Anthropic | None:
    """
    Returns an Anthropic client for a specific feature.

    Environment variables (set these in your .env file):
        ANTHROPIC_API_KEY          → master / fallback key
        ANTHROPIC_API_KEY_AUDIT    → Standard Reviewer (Tab 2)
        ANTHROPIC_API_KEY_NQF      → NQF Alignment (Tab 3)
        ANTHROPIC_API_KEY_SSR      → SSR Writer (Tab 4)
        ANTHROPIC_API_KEY_EXTRACT  → PDF pre-processing extraction step

    If a dedicated key is not set, the master key is used automatically.
    """
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
    """Extracts valid JSON from a response that may contain markdown fences."""
    pattern = r"```(?:json)?\s*(.*?)\s*```"
    match = re.search(pattern, response_text, re.DOTALL)
    if match:
        response_text = match.group(1)
    start = response_text.find('{')
    end = response_text.rfind('}')
    if start != -1 and end != -1:
        return response_text[start:end + 1]
    return response_text


# ==============================================================================
# STEP 1 — EVIDENCE EXTRACTION (per chunk, grounded)
# Called internally before the main audit. Prevents truncation hallucination.
# ==============================================================================

def _extract_relevant_passages(client: Anthropic, standard_name: str, standard_keywords: list, chunks: list[str]) -> str:
    """
    Scans every text chunk and extracts only passages that are directly
    relevant to the given standard. Returns a condensed, grounded evidence
    string for use in the main audit.
    """
    relevant_passages = []

    for i, chunk in enumerate(chunks):
        if not chunk.strip():
            continue

        prompt = f"""You are a document analyst. Your ONLY job is to copy-paste relevant sentences.

STANDARD: {standard_name}
KEYWORDS TO LOOK FOR: {', '.join(standard_keywords)}

DOCUMENT CHUNK (pages {i+1}):
\"\"\"
{chunk}
\"\"\"

INSTRUCTIONS:
- Read the chunk carefully.
- Copy-paste ONLY the sentences or paragraphs that are directly relevant to the standard above.
- Do NOT paraphrase, summarise, or add any commentary.
- Do NOT invent or infer anything.
- If nothing is relevant, respond with exactly: NO_RELEVANT_CONTENT
- Prefix each extracted passage with [CHUNK-{i+1}] on a new line.
"""
        try:
            response = client.messages.create(
                model=MODEL_ID,
                max_tokens=1000,
                messages=[{"role": "user", "content": prompt}]
            )
            result = response.content[0].text.strip()
            if result and result != "NO_RELEVANT_CONTENT":
                relevant_passages.append(result)
        except Exception:
            continue  # skip chunk on error, do not hallucinate

    if not relevant_passages:
        return "NO_RELEVANT_CONTENT_FOUND_IN_ANY_DOCUMENT"

    return "\n\n".join(relevant_passages)


# ==============================================================================
# TAB 2 — COMPLIANCE AUDIT  (uses ANTHROPIC_API_KEY_AUDIT)
# ==============================================================================

def analyze_evidence_for_standard(client: Anthropic, standard_name: str, standard_info: dict, chunks: list[str]) -> dict:
    """
    Two-phase grounded audit:
      Phase 1 — extract relevant passages from all chunks (no truncation).
      Phase 2 — rate compliance strictly from those passages only.
    """
    extract_client = get_client("extract")

    # --- Phase 1: Extract grounded evidence ---
    grounded_evidence = _extract_relevant_passages(
        extract_client, standard_name, standard_info.get("keywords", []), chunks
    )

    # --- Phase 2: Audit strictly from extracted evidence ---
    system_prompt = (
        "You are a strict NCAAA/ETEC External Reviewer for a General Dentistry Program.\n"
        "ABSOLUTE RULES — violating these makes your review invalid:\n"
        "  1. You may ONLY reference evidence explicitly present in the EXTRACTED PASSAGES block.\n"
        "  2. If a criterion has no supporting passage, you MUST mark it as 'NOT EVIDENCED IN DOCUMENTS'.\n"
        "  3. You must NOT draw on general knowledge about dentistry or accreditation.\n"
        "  4. Every strength or gap you list MUST include a [CHUNK-N] citation.\n"
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
                "REVIEWER NOTE: After scanning all uploaded document pages, no content "
                f"relevant to '{standard_name}' was found. This standard cannot be assessed "
                "without the appropriate evidence documents."
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

TASK:
Using ONLY the passages above, evaluate compliance with the standard.
For each strength and gap, you MUST cite the chunk reference (e.g. [CHUNK-3]).
If a criterion is not evidenced, state 'NOT EVIDENCED IN DOCUMENTS'.

OUTPUT FORMAT (valid JSON):
{{
    "relevance": "High/Medium/Low",
    "compliance_rating": "X/5",
    "strengths": [
        "[CHUNK-N] Description of strength found in documents"
    ],
    "areas_for_improvement": [
        "Description of gap or 'NOT EVIDENCED IN DOCUMENTS' if absent"
    ],
    "reviewer_comment": "Narrative citing [CHUNK-N] references. No invented claims.",
    "citations": ["CHUNK-N: exact quote from passage", "..."]
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
        cleaned = clean_json_response(raw_text)
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
# TAB 3 — NQF ALIGNMENT  (uses ANTHROPIC_API_KEY_NQF)
# ==============================================================================

def check_nqf_alignment(client: Anthropic, plo_text: str, nqf_domains: dict) -> str:
    """
    Checks PLO text against NQF Level 6 domains.
    If PLO text came from uploaded docs, it will be grounded.
    If manually pasted, the AI works from that text only.
    """
    system_prompt = (
        "You are an NQF academic auditor.\n"
        "RULES:\n"
        "  1. Evaluate ONLY the PLOs provided in the user's message.\n"
        "  2. Do NOT invent PLOs or assume any that are not explicitly stated.\n"
        "  3. If a domain has no PLO mapped to it, explicitly state 'NO PLO FOUND FOR THIS DOMAIN'.\n"
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
2. Flag any PLO where the action verb does not match Bachelor's level complexity.
   - Example: 'List' is too low (recall). 'Analyse' or 'Apply' is appropriate.
3. Identify which domains have NO mapped PLO — state explicitly.
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
# TAB 4 — SSR WRITER  (uses ANTHROPIC_API_KEY_SSR)
# ==============================================================================

def chat_with_ssr_expert(client: Anthropic, chunks: list[str], user_query: str) -> str:
    """
    Drafts SSR content strictly from uploaded document chunks.
    Uses a two-step approach:
      1. Find the most relevant chunks for the query.
      2. Draft the SSR section from those chunks only.
    """
    # Step 1: find relevant chunks for this specific query
    extract_client = get_client("extract")
    keywords = user_query.split()[:10]  # use first 10 words as keyword hints
    relevant_evidence = _extract_relevant_passages(extract_client, user_query, keywords, chunks)

    system_prompt = (
        "You are a professional SSR (Self-Study Report) writer for a Dental School seeking NCAAA accreditation.\n"
        "ABSOLUTE RULES:\n"
        "  1. Write ONLY from the evidence in the EXTRACTED PASSAGES below.\n"
        "  2. Do NOT fabricate statistics, dates, committee names, or policies not present in the passages.\n"
        "  3. If the evidence is insufficient to answer the user's request, say so clearly and list what documents are missing.\n"
        "  4. Use formal academic language suitable for an accreditation report.\n"
        "  5. Where you use a fact, note the source chunk in parentheses, e.g. (Source: CHUNK-3).\n"
    )

    if relevant_evidence == "NO_RELEVANT_CONTENT_FOUND_IN_ANY_DOCUMENT":
        return (
            "⚠️ **Insufficient Evidence**\n\n"
            "No relevant content was found in the uploaded documents to respond to your request:\n"
            f"> *{user_query}*\n\n"
            "**What to do:**\n"
            "- Upload the specific document that contains this information (e.g., Annual Program Report, Student Handbook).\n"
            "- Or paste the relevant text directly into the NQF tab if it is PLO-related.\n\n"
            "The SSR Writer will not generate content it cannot evidence from your uploaded files."
        )

    messages = [
        {
            "role": "user",
            "content": (
                f"EXTRACTED EVIDENCE FROM UPLOADED DOCUMENTS:\n\"\"\"\n{relevant_evidence}\n\"\"\"\n\n"
                f"USER REQUEST: {user_query}"
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