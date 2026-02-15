import os
import json
import re
from anthropic import Anthropic
from dotenv import load_dotenv
from config import SYSTEM_PROMPT_EXTRACTOR, SYSTEM_PROMPT_GENERATOR

load_dotenv()

def get_client():
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("API Key not found. Please check your .env file.")
    return Anthropic(api_key=api_key)

def repair_json(broken_json_str):
    """ Emergency repair if AI cuts off JSON. """
    try:
        if "}" not in broken_json_str[-5:]:
            if broken_json_str.strip().endswith(","):
                broken_json_str = broken_json_str.strip()[:-1]
            if broken_json_str.count('"') % 2 != 0:
                broken_json_str += '"'
            broken_json_str += "}"
            if broken_json_str.count('{') > broken_json_str.count('}'):
                broken_json_str += "}"
        return json.loads(broken_json_str)
    except:
        return {
            "definition": "Data truncated.",
            "indicators": ["Data truncated."],
            "pitfalls": ["Data truncated."],
            "best_practice": "Raw Output: " + broken_json_str[:500]
        }

def analyze_chunk(client, chunk: str, req_title: str, req_def: str) -> str:
    prompt = f"""
    TARGET STANDARD: {req_title}
    DEFINITION: "{req_def}"
    
    DOCUMENT EXCERPT:
    "{chunk}"
    
    TASK:
    Identify if this text provides evidence of compliance or non-compliance with the 2025 General Dentistry Standards.
    Look for specific keywords: "KLO", "SKU", "Clinical Training", "Assessment Methods".
    If found, extract the evidence verbatim.
    If unrelated, return "NO_DATA".
    """
    try:
        response = client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=1024,
            temperature=0,
            system=SYSTEM_PROMPT_EXTRACTOR,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.content[0].text.strip()
    except Exception as e:
        return f"Error: {e}"

def generate_compliance_report(client, all_evidence: list, req_title: str, req_def: str) -> dict:
    combined_evidence = "\n".join(all_evidence)
    if len(combined_evidence) > 100000:
        combined_evidence = combined_evidence[:100000] + "\n[...TRUNCATED...]"
    
    prompt = f"""
    TARGET STANDARD: {req_title}
    DEFINITION: "{req_def}"
    
    EVIDENCE EXTRACTED:
    {combined_evidence}
    
    TASK:
    Generate a Compliance Report against ETEC 2025 General Dentistry Standards.
    
    OUTPUT JSON FORMAT:
    {{
        "definition": "Summary of the standard...",
        "indicators": ["Evidence of alignment found...", "Specific KLOs mentioned..."],
        "pitfalls": ["Gaps in curriculum...", "Missing SKUs...", "Outdated assessment methods..."],
        "best_practice": "Strongest point of compliance found in the documents..."
    }}
    
    IMPORTANT: Output ONLY valid JSON.
    """
    try:
        response = client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=4096,
            temperature=0.2,
            system=SYSTEM_PROMPT_GENERATOR,
            messages=[{"role": "user", "content": prompt}]
        )
        content = response.content[0].text.strip()
        if content.startswith("```json"):
            content = content.replace("```json", "").replace("```", "")
        return json.loads(content)
    except json.JSONDecodeError:
        return repair_json(content)
    except Exception as e:
        return {"definition": f"Error: {e}", "indicators": [], "pitfalls": [], "best_practice": ""}

def query_documents(client, full_context: str, user_question: str) -> str:
    if len(full_context) > 500000:
        full_context = full_context[:500000] + "...(truncated)"

    system_prompt = "You are an AI Research Assistant for Dental Education. Answer based strictly on the uploaded text."
    prompt = f"CONTEXT:\n{full_context}\n\nQUESTION: {user_question}"
    
    try:
        response = client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=1024,
            temperature=0.4,
            system=system_prompt,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.content[0].text
    except Exception as e:
        return f"Error: {e}"
