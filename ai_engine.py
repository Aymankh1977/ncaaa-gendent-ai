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
# JSON CLEANING
# ==============================================================================

def clean_json_response(text: str) -> str:
    match = re.search(r"```(?:json)?\s*(.*?)\s*```", text, re.DOTALL)
    if match:
        text = match.group(1)
    start = text.find('{')
    end   = text.rfind('}')
    if start != -1 and end != -1:
        return text[start:end + 1]
    return text


# ==============================================================================
# EVIDENCE EXTRACTION  — unchanged from last fix
# ==============================================================================

def _extract_relevant_passages(client, topic: str, keywords: list, chunks: list) -> str:
    relevant_passages = []
    for i, chunk in enumerate(chunks):
        if not chunk.strip():
            continue
        hint = f"Keyword hints: {', '.join(keywords)}\n" if keywords else ""
        prompt = f"""You are a document analyst extracting evidence for an accreditation review.

TOPIC: {topic}
{hint}
DOCUMENT CHUNK {i+1}:
\"\"\"
{chunk}
\"\"\"

INSTRUCTIONS:
- Extract ALL text from this chunk that is relevant to the topic.
- Include full sentences, table rows, numbered items — do not truncate.
- Do NOT paraphrase. Copy exact text.
- Do NOT invent anything.
- If nothing is relevant, respond with exactly: NO_RELEVANT_CONTENT
- Start your response with [CHUNK-{i+1}] on its own line.
"""
        try:
            response = client.messages.create(
                model=MODEL_ID, max_tokens=2000,
                messages=[{"role": "user", "content": prompt}]
            )
            result = response.content[0].text.strip()
            if result and result != "NO_RELEVANT_CONTENT":
                relevant_passages.append(result)
        except Exception:
            continue

    return "\n\n".join(relevant_passages) if relevant_passages else "NO_RELEVANT_CONTENT_FOUND_IN_ANY_DOCUMENT"


# ==============================================================================
# TAB 2 — COMPLIANCE AUDIT  (full rubric-based, per-component scoring)
# ==============================================================================

def _format_rubric_for_prompt(criterion_info: dict) -> str:
    """Formats the full 4-level rubric for a criterion into a readable prompt block."""
    lines = [f"Criterion Description: {criterion_info['description']}", ""]
    lines.append("RUBRIC COMPONENTS AND SCORING LEVELS:")
    lines.append("=" * 60)
    for comp in criterion_info['components']:
        lines.append(f"\nComponent: {comp['component']}")
        lines.append(f"  Score 4 — Full Compliance:        {comp['full_4']}")
        lines.append(f"  Score 3 — Substantial Compliance: {comp['sub_3']}")
        lines.append(f"  Score 2 — Minimal Compliance:     {comp['min_2']}")
        lines.append(f"  Score 1 — Non-Compliance:         {comp['non_1']}")
    return "\n".join(lines)


def analyze_evidence_for_standard(client, criterion_key: str, criterion_info: dict, chunks: list) -> dict:
    """
    Full rubric-based audit:
      Phase 1 — extract all relevant evidence passages from documents.
      Phase 2 — score EVERY component against the 4-level rubric.
    """
    extract_client = get_client("extract")

    # Build search topic from criterion description + all component names
    component_names = [c['component'] for c in criterion_info.get('components', [])]
    topic = f"{criterion_key} — {criterion_info.get('description', '')} — Components: {'; '.join(component_names)}"

    grounded_evidence = _extract_relevant_passages(
        extract_client, topic=topic, keywords=[], chunks=chunks
    )

    system_prompt = (
        "You are a strict NCAAA/ETEC External Reviewer for a General Dentistry Program.\n"
        "ABSOLUTE RULES:\n"
        "  1. Score EVERY component listed in the rubric — never skip one.\n"
        "  2. Base scores ONLY on evidence in the EXTRACTED PASSAGES. Never use general knowledge.\n"
        "  3. If a component has no evidence in the passages, score it 1 (Non-Compliance) and state 'NOT EVIDENCED IN DOCUMENTS'.\n"
        "  4. For each component, cite the exact [CHUNK-N] reference that supports your score.\n"
        "  5. Output valid JSON only — no preamble, no markdown fences.\n"
    )

    rubric_text = _format_rubric_for_prompt(criterion_info)
    num_components = len(criterion_info.get('components', []))

    if grounded_evidence == "NO_RELEVANT_CONTENT_FOUND_IN_ANY_DOCUMENT":
        components_result = [
            {
                "component": c['component'],
                "score": 1,
                "level": "Non-Compliance",
                "finding": "NOT EVIDENCED IN DOCUMENTS — no relevant content found in uploaded files.",
                "citation": "N/A"
            }
            for c in criterion_info.get('components', [])
        ]
        return {
            "criterion": criterion_key,
            "description": criterion_info.get('description', ''),
            "overall_score": "1/4",
            "overall_level": "Non-Compliance",
            "components": components_result,
            "summary": f"No evidence found in uploaded documents for {criterion_key}. Upload the relevant evidence documents.",
            "strengths": [],
            "gaps": ["No evidence found in uploaded documents for this criterion."],
            "citations": []
        }

    user_prompt = f"""
CRITERION: {criterion_key}
{rubric_text}

EXTRACTED PASSAGES FROM UPLOADED DOCUMENTS:
\"\"\"
{grounded_evidence}
\"\"\"

TASK:
Score EVERY component (there are {num_components} components) against the rubric above.
Use ONLY the extracted passages as evidence.
For each component, determine which score level (1-4) best matches the evidence.

OUTPUT — valid JSON only:
{{
    "criterion": "{criterion_key}",
    "description": "...",
    "overall_score": "X/4",
    "overall_level": "Full/Substantial/Minimal/Non-Compliance",
    "components": [
        {{
            "component": "exact component name from rubric",
            "score": 1,
            "level": "Non-Compliance",
            "finding": "What the evidence shows, citing [CHUNK-N]. If absent: NOT EVIDENCED IN DOCUMENTS.",
            "citation": "[CHUNK-N]: brief quote"
        }}
    ],
    "summary": "Overall narrative citing chunks. No invented claims.",
    "strengths": ["[CHUNK-N] specific strength found in documents"],
    "gaps": ["specific gap or NOT EVIDENCED IN DOCUMENTS"],
    "citations": ["CHUNK-N: exact short quote from evidence"]
}}
"""

    try:
        response = client.messages.create(
            model=MODEL_ID, max_tokens=3500,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}]
        )
        raw  = response.content[0].text
        return json.loads(clean_json_response(raw))

    except json.JSONDecodeError:
        return {
            "criterion": criterion_key,
            "description": criterion_info.get('description', ''),
            "overall_score": "N/A",
            "overall_level": "Parse Error",
            "components": [],
            "summary": f"JSON parsing failed. Raw output:\n\n{raw}",
            "strengths": [], "gaps": ["See summary for raw output."], "citations": []
        }
    except Exception as e:
        return {"error": f"API Error: {str(e)}"}


# ==============================================================================
# TAB 3 — NQF ALIGNMENT
# ==============================================================================

def check_nqf_alignment(client, plo_text: str, nqf_domains: dict) -> str:
    # Extract level guidance note and the actual domain descriptors
    level_guidance = nqf_domains.get("_level_guidance", "")
    domains_for_eval = {k: v for k, v in nqf_domains.items() if not k.startswith("_")}

    system_prompt = (
        "You are an expert NQF-KSA academic auditor (NQF Second Edition, 2023, ETEC).\n"
        "RULES:\n"
        "  1. Evaluate ONLY the PLOs explicitly provided — do NOT invent any.\n"
        "  2. First determine the correct NQF level (6 or 7) based on program duration and credit hours\n"
        "     if that information is available in the PLO text; otherwise evaluate against both levels.\n"
        "  3. For each PLO, quote it exactly, map it to the correct domain, and state whether the\n"
        "     action verb meets the complexity requirements of the determined NQF level.\n"
        "  4. Flag verbs that are too low (e.g. List, Recall, Define → below Level 6);\n"
        "     acceptable Level 6 verbs include: Apply, Analyse, Evaluate, Design, Solve, Conduct.\n"
        "     Level 7 requires: Critically assess, Synthesise, Generate, Lead, Contribute.\n"
        "  5. Identify any NQF domain that has NO mapped PLO — state this explicitly.\n"
        "  6. Conclude with a clear recommendation: state the correct NQF level for this program\n"
        "     and list specific revisions needed.\n"
    )
    prompt = f"""
NQF LEVEL GUIDANCE:
{level_guidance}

PROGRAM LEARNING OUTCOMES (PLOs) TO EVALUATE:
\"\"\"
{plo_text}
\"\"\"

NQF-KSA DOMAIN DESCRIPTORS (Level 6 and Level 7):
{json.dumps(domains_for_eval, indent=2)}

EVALUATION TASKS:
1. Determine the applicable NQF level (6 or 7) for this program, stating your reasoning.
2. For each PLO: quote it exactly, map it to its domain, assess the action verb complexity.
3. Flag any PLO where the verb does not meet the required NQF level.
4. Identify which domains have NO mapped PLO.
5. Provide a final recommendation with the determined NQF level and required revisions.

Use clear section headers. Be specific — quote the exact PLO text in every finding.
"""
    try:
        response = client.messages.create(
            model=MODEL_ID, max_tokens=2000,
            system=system_prompt,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.content[0].text
    except Exception as e:
        return f"Error: {str(e)}"


# ==============================================================================
# TAB 4 — SSR WRITER
# ==============================================================================

def chat_with_ssr_expert(client, chunks: list, user_query: str) -> str:
    extract_client = get_client("extract")
    grounded_evidence = _extract_relevant_passages(
        extract_client, topic=user_query, keywords=[], chunks=chunks
    )

    system_prompt = (
        "You are a professional accreditation consultant for a Dental School seeking NCAAA accreditation.\n"
        "ABSOLUTE RULES:\n"
        "  1. Work ONLY from the EXTRACTED PASSAGES. Never invent data.\n"
        "  2. If passages contain a rubric or criteria table — USE IT systematically.\n"
        "  3. If passages contain a course specification — analyse it against any rubric present.\n"
        "  4. Do NOT fabricate statistics, names, dates, or policies not in the passages.\n"
        "  5. If evidence is insufficient, say so specifically and state what document is needed.\n"
        "  6. Use formal academic language.\n"
        "  7. Cite source chunks in parentheses, e.g. (Source: CHUNK-3).\n"
    )

    if grounded_evidence == "NO_RELEVANT_CONTENT_FOUND_IN_ANY_DOCUMENT":
        return (
            "⚠️ **Insufficient Evidence**\n\n"
            f"No relevant content found in the selected documents for:\n> *{user_query}*\n\n"
            "**Possible reasons:**\n"
            "- Documents may be scanned images (not machine-readable). Re-save as text-based PDF/DOCX.\n"
            "- Relevant content may be in a document not currently selected.\n"
            "- File may not have processed correctly — try re-uploading.\n\n"
            "The SSR Writer will not generate content it cannot evidence from your files."
        )

    try:
        response = client.messages.create(
            model=MODEL_ID, max_tokens=3500,
            system=system_prompt,
            messages=[{
                "role": "user",
                "content": (
                    f"EXTRACTED EVIDENCE:\n\"\"\"\n{grounded_evidence}\n\"\"\"\n\n"
                    f"REQUEST:\n{user_query}\n\n"
                    "Respond using ONLY the evidence above."
                )
            }]
        )
        return response.content[0].text
    except Exception as e:
        return f"Error: {str(e)}"