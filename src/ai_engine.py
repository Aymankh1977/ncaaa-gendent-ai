# ai_engine.py
import os
from anthropic import Anthropic
import json
import re

def get_client():
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        return None
    return Anthropic(api_key=api_key)

def clean_json_response(response_text):
    """
    Robust cleaner: Finds the first '{' and the last '}' to extract valid JSON,
    ignoring any conversational text before or after.
    """
    # 1. Attempt to find JSON inside Markdown code blocks first (e.g., ```json ... ```)
    pattern = r"```(?:json)?\s*(.*?)\s*```"
    match = re.search(pattern, response_text, re.DOTALL)
    if match:
        response_text = match.group(1)

    # 2. "Brace Finder" - Find the first { and the last }
    start_index = response_text.find('{')
    end_index = response_text.rfind('}')

    if start_index != -1 and end_index != -1:
        # Extract only the JSON part
        return response_text[start_index : end_index + 1]
    
    # If no braces found, return original text (which will likely fail parsing)
    return response_text

def analyze_evidence_for_standard(client, standard_name, standard_info, document_text):
    """
    Analyzes specific evidence against a specific NCAAA standard.
    """
    system_prompt = (
        "You are an expert NCAAA/ETEC External Reviewer for a General Dentistry Program. "
        "Your job is to evaluate evidence against the 2022 Program Accreditation Standards. "
        "IMPORTANT: Output ONLY valid JSON. Do not include markdown formatting (```), "
        "do not include introductions, and do not include concluding remarks."
    )

    user_prompt = f"""
    STANDARDS TO EVALUATE: {standard_name}
    DESCRIPTION: {standard_info['description']}
    CRITERIA: {', '.join(standard_info['criteria'])}

    EVIDENCE CONTENT (Excerpt):
    {document_text[:25000]} 

    TASK:
    1. Identify if this evidence supports the standard.
    2. Rate the compliance level (1 to 5) based on NCAAA Self-Evaluation Scales.
    3. Identify Gaps.
    4. Provide Recommendations.

    OUTPUT FORMAT:
    {{
        "relevance": "High/Medium/Low",
        "compliance_rating": "X/5",
        "strengths": ["point 1", "point 2"],
        "areas_for_improvement": ["gap 1", "gap 2"],
        "reviewer_comment": "Professional narrative..."
    }}
    """

    try:
        response = client.messages.create(
            model="claude-3-5-sonnet-20240620",
            max_tokens=2000,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}]
        )
        
        raw_text = response.content[0].text
        
        # --- CLEANING STEP ---
        cleaned_json = clean_json_response(raw_text)
        
        return json.loads(cleaned_json)
        
    except json.JSONDecodeError as e:
        # Return the specific error and the text that caused it for debugging
        return {
            "error": "JSON Parsing Failed", 
            "details": str(e),
            "raw_response": raw_text[:200] + "..." # Show first 200 chars to debug
        }
    except Exception as e:
        return {"error": str(e)}

def check_nqf_alignment(client, plo_text, nqf_domains):
    """
    Checks if Program Learning Outcomes (PLOs) align with NQF Level 6 (Bachelor).
    """
    prompt = f"""
    Review these Dentistry Program Learning Outcomes (PLOs):
    {plo_text}

    Compare them against Saudi NQF Level 6 Domains:
    {json.dumps(nqf_domains)}

    Task:
    1. Are the Knowledge, Skills, and Values properly categorized?
    2. Are the verbs used appropriate for a Bachelor's degree (e.g., Analyze, Evaluate vs. Define)?
    3. Is there alignment with professional dentistry standards?

    Provide a structured analysis.
    """
    try:
        response = client.messages.create(
            model="claude-3-5-sonnet-20240620",
            max_tokens=1500,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.content[0].text
    except Exception as e:
        return f"Error: {str(e)}"

def chat_with_ssr_expert(client, context, user_query):
    """
    Context-aware chat for writing the SSR.
    """
    system_prompt = (
        "You are a specialized Accreditation Consultant for a Dental School. "
        "You help write the Self-Study Report (SSR). "
        "Use the provided evidence to write professional, evidence-based narratives. "
        "If evidence is missing, flag it immediately."
    )
    
    messages = [
        {"role": "user", "content": f"Context Evidence:\n{context[:50000]}"},
        {"role": "assistant", "content": "I have reviewed the evidence. Ready to assist with the SSR."},
        {"role": "user", "content": user_query}
    ]

    try:
        response = client.messages.create(
            model="claude-3-5-sonnet-20240620",
            max_tokens=3000,
            system=system_prompt,
            messages=messages
        )
        return response.content[0].text
    except Exception as e:
        return f"Error: {str(e)}"