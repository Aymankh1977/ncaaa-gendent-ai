# src/config.py

# ETEC Academic Standards for General Dentistry Programs (Version 2.0 - 2025)
ETEC_STANDARDS_2025 = {
    "KLO": {
        "title": "Key Learning Outcomes (KLOs)",
        "definition": "The program must demonstrate that graduates achieve the 9 KLOs mapped to the NQF. Includes: KLO1 (Biomedical/Clinical Sciences), KLO2 (Critical Thinking), KLO3 (Research), KLO4 (Diagnosis/Treatment Planning), KLO5 (Clinical Skills/Safety), KLO6 (Communication), KLO7 (Digital Tools), KLO8 (Ethics/Law), KLO9 (Professionalism/Leadership). (Source: ETEC 2025, p.4)"
    },
    "EKU": {
        "title": "Essential Knowledge Units (EKUs)",
        "definition": "Curriculum must include at least 14 credit hours of: English Language (10 hrs), Chemistry (2 hrs), and Biology (2 hrs). These are prerequisites for the dental program. (Source: ETEC 2025, p.5)"
    },
    "GKU_1": {
        "title": "GKU 1: Knowledge (Basic Sciences)",
        "definition": "Must cover ~25% of the core curriculum. Includes: General Anatomy & Physiology (7%), Dental Anatomy (2%), Dental Biomaterials (3%), Pharmacology (2%), General Pathology (3%), Oral Pathology (3%), Oral Histology (2%), Oral Biology (3%)."
    },
    "GKU_2": {
        "title": "GKU 2: Ethics and Professionalism",
        "definition": "Must cover ~2% of curriculum. Focus on: Dental Health Regulations & Safety Practices (1%) and Patient Advocacy/Privacy/Confidentiality (1%)."
    },
    "GKU_3": {
        "title": "GKU 3: Communication",
        "definition": "Must cover ~2% of curriculum. Focus on: Patient & Family Communication (1%) and Interprofessional Collaboration/Community Health Promotion (1%)."
    },
    "GKU_4": {
        "title": "GKU 4: Health Promotion",
        "definition": "Must cover ~2% of curriculum. Focus on: Prevention Programs for Oral Diseases (1%) and General Health Promotion Strategies (1%)."
    },
    "GKU_5": {
        "title": "GKU 5: Practice Management & Informatics",
        "definition": "Must cover ~2% of curriculum. Focus on: Emerging IT/Documentation (1%) and Resource Utilization/Business Management in Dentistry (1%)."
    },
    "GKU_6": {
        "title": "GKU 6: Patient Care (Clinical)",
        "definition": "The core of the program (~67% weight). Includes: Examination/Diagnosis (10%), Radiology (4%), Restorative/Endo (19%), Surgery/Emergencies (11%), Prosthodontics (14%), Periodontics (9%). (Source: ETEC 2025, p.6)"
    }
}

SYSTEM_PROMPT_EXTRACTOR = """
You are an expert ETEC/NCAAA Accreditation Reviewer for Dentistry.
Your task is to analyze documents (Course Specs, Annual Reports, Self-Studies) against the 'Academic Standards for General Dentistry Programs 2025 (Version 2.0)'.

Your goal is to extract EVIDENCE of:
1. Alignment with the 9 Key Learning Outcomes (KLOs).
2. Coverage of the Specific Knowledge Units (SKUs).
3. Implementation of specific clinical skills (e.g., Implantology, Digital Dentistry).
4. Any Gaps or weaknesses compared to the 2025 Standards.

If the text provided does not contain relevant evidence, return 'NO_DATA'.
"""

SYSTEM_PROMPT_GENERATOR = """
You are a Senior Consultant for ETEC Accreditation.
Your goal is to synthesize evidence into a 'Compliance Report'.
You must be objective, referencing the 2025 Standards (Version 2.0).
You output ONLY valid JSON.
"""
