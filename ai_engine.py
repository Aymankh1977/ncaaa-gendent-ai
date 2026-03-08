import os
from anthropic import Anthropic
import json

def get_client():
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key: return None
    return Anthropic(api_key=api_key)

def analyze_evidence_for_standard(client, standard_name, standard_info, document_text):
    prompt = f"""
    You are an NCAAA External Reviewer. Evaluate this evidence against: {standard_name}
    Criteria: {standard_info['criteria']}
    Evidence: {document_text[:20000]}
    
    Return JSON format:
    {{
        "compliance_rating": "X/5",
        "reviewer_comment": "Summary...",
        "strengths": ["list"],
        "areas_for_improvement": ["list"]
    }}
    """
    try:
        msg = client.messages.create(
            model="claude-3-haiku-20240307", max_tokens=2000,
            messages=[{"role": "user", "content": prompt}]
        )
        return json.loads(msg.content[0].text)
    except:
        return {"error": "Failed to analyze or parse JSON."}

def check_nqf_alignment(client, plo_text, nqf_domains):
    prompt = f"""
    Check these Dentistry PLOs against Saudi NQF Level 6:
    {plo_text[:15000]}
    Domains: {nqf_domains}
    
    Provide a markdown report on alignment gaps.
    """
    msg = client.messages.create(
        model="claude-3-haiku-20240307", max_tokens=2000,
        messages=[{"role": "user", "content": prompt}]
    )
    return msg.content[0].text

def chat_with_ssr_expert(client, context, user_query):
    messages = [
        {"role": "user", "content": f"Evidence:\n{context[:30000]}"},
        {"role": "assistant", "content": "I have read the evidence."},
        {"role": "user", "content": user_query}
    ]
    msg = client.messages.create(
        model="claude-3-haiku-20240307", max_tokens=2000,
        messages=messages
    )
    return msg.content[0].text
