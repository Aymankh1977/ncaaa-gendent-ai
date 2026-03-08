import os
from anthropic import Anthropic
import json
import re

# --- CONFIGURATION ---
# We are switching to Haiku because it is the most compatible model
MODEL_ID = "claude-3-haiku-20240307"

def get_client():
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        return None
    return Anthropic(api_key=api_key)

def clean_json_response(response_text):
    """
    Robust cleaner: Finds the largest block of text between '{' and '}'.
    """
    # Remove markdown code blocks if present
    pattern = r"```(?:json)?\s*(.*?)\s*```"
    match = re.search(pattern, response_text, re.DOTALL)
    if match:
        response_text = match.group(1)

    # Find the FIRST opening brace '{'
    start_index = response_text.find('{')
    
    # Find the LAST closing brace '}'
    end_index = response_text.rfind('}')

    if start_index != -1 and end_index != -1:
        # Extract the content
        json_str = response_text[start_index : end_index + 1]
        return json_str
    
    return response_text

def analyze_evidence_for_standard(client, standard_name, standard_info, document_text):
    """
    Analyzes specific evidence against a specific NCAAA standard.
    """
    system_prompt = (
        "You are an expert NCAAA/ETEC External Reviewer for a General Dentistry Program. "
        "Your task is to evaluate the provided evidence against the standard. "
        "CRITICAL INSTRUCTION: You must output valid JSON only. "
        "Do not use trailing commas. Do not use single quotes for keys. "
        "Do not write any introductory text."
    )

    user_prompt = f"""
    STANDARDS TO EVALUATE: {standard_name}
    DESCRIPTION: {standard_info['description']}
    CRITERIA: {', '.join(standard_info['criteria'])}

    EVIDENCE CONTENT (Excerpt):
    {document_text[:25000]} 

    TASK:
    1. Identify if this evidence supports the standard.
    2. Rate the compliance level (1 to 5).
    3. Identify Gaps and Recommendations.

    REQUIRED JSON FORMAT:
    {{
        "relevance": "High/Medium/Low",
        "compliance_rating": "X/5",
        "strengths": ["point 1", "point 2"],
        "areas_for_improvement": ["gap 1", "gap 2"],
        "reviewer_comment": "Write your main narrative here."
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
        
        # Attempt to clean and parse
        cleaned_json = clean_json_response(raw_text)
        return json.loads(cleaned_json)

    except json.JSONDecodeError:
        # Fail-safe: Return raw text wrapped in JSON structure
        return {
            "relevance": "Analysis Completed (Format Error)",
            "compliance_rating": "Check Text",
            "strengths": ["See Reviewer Comment"],
            "areas_for_improvement": ["See Reviewer Comment"],
            "reviewer_comment": f"**NOTE: AI formatting failed, but here is the raw analysis:**\n\n{raw_text}"
        }
    except Exception as e:
        return {"error": f"Connection/API Error: {str(e)}"}

def check_nqf_alignment(client, plo_text, nqf_domains):
    prompt = f"""
    Review these Dentistry Program Learning Outcomes (PLOs):
    {plo_text}

    Compare them against Saudi NQF Level 6 Domains:
    {json.dumps(nqf_domains)}

    Task:
    1. Are the Knowledge, Skills, and Values properly categorized?
    2. Are the verbs used appropriate for a Bachelor's degree?
    3. Is there alignment with professional dentistry standards?
    """
    try:
        response = client.messages.create(
            model=MODEL_ID,
            max_tokens=1500,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.content[0].text
    except Exception as e:
        return f"Error: {str(e)}"

def chat_with_ssr_expert(client, context, user_query):
    system_prompt = (
        "You are a specialized Accreditation Consultant for a Dental School. "
        "Help write the Self-Study Report (SSR). Use the provided evidence."
    )
    
    messages = [
        {"role": "user", "content": f"Context Evidence:\n{context[:40000]}"},
        {"role": "assistant", "content": "I have reviewed the evidence."},
        {"role": "user", "content": user_query}
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
