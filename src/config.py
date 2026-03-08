# config.py

# Based on the "Standards for Program Accreditation 2022" and Self-Evaluation Scales
NCAAA_STANDARDS = {
    "1. Mission and Goals": {
        "description": "The program mission must be consistent with the institution's mission and guide all operations.",
        "criteria": [
            "1.1 Program Management",
            "1.2 Program Quality Assurance"
        ],
        "keywords": ["mission", "goals", "strategic plan", "KPIs", "advisory board"]
    },
    "2. Teaching and Learning": {
        "description": "Graduate attributes and learning outcomes must be precisely defined and consistent with NQF.",
        "criteria": [
            "2.1 Student Learning Outcomes (NQF Alignment)",
            "2.2 Curriculum Design",
            "2.3 Quality of Teaching and Assessment"
        ],
        "keywords": ["learning outcomes", "NQF", "curriculum", "assessment", "field training", "internship"]
    },
    "3. Students": {
        "description": "Clear admission criteria, fair treatment, and effective guidance/counseling services.",
        "criteria": [
            "3.1 Student Admissions",
            "3.2 Guidance and Counseling",
            "3.3 Appeals and Complaints"
        ],
        "keywords": ["admission", "student handbook", "counseling", "grievance", "alumni"]
    },
    "4. Faculty": {
        "description": "Sufficient qualified teaching staff with necessary competence and professional development.",
        "criteria": [
            "4.1 Faculty Qualifications",
            "4.2 Professional Development",
            "4.3 Faculty Evaluation"
        ],
        "keywords": ["CV", "faculty load", "professional development", "research output", "promotion"]
    },
    "5. Learning Resources": {
        "description": "Adequate facilities, equipment, and digital resources to meet program needs.",
        "criteria": [
            "5.1 Learning Resources",
            "5.2 Facilities and Equipment",
            "5.3 Safety and Risk Management"
        ],
        "keywords": ["library", "laboratories", "clinics", "safety manual", "IT support"]
    },
    "6. Research and Projects": {
        "description": "Encouraging faculty and students to produce research and innovation.",
        "criteria": [
            "6.1 Research Activities",
            "6.2 Student Research"
        ],
        "keywords": ["publications", "citations", "research plan", "funding", "ethics"]
    }
}

# Based on National Qualifications Framework (NQF) - Level 6 (Bachelor)
NQF_DOMAINS = {
    "Knowledge and Understanding": "Deep understanding of facts, concepts, and theories in Dentistry.",
    "Skills": "Application of knowledge, critical thinking, and practical clinical skills.",
    "Values, Autonomy, and Responsibility": "Professional ethics, patient safety, and lifelong learning."
}

REQUIRED_DOCUMENTS = [
    "Program Specification",
    "Course Specifications",
    "Field Experience Specifications",
    "Annual Program Report",
    "Key Performance Indicators (KPIs) Report",
    "Self-Study Report (SSR)",
    "Student Handbook",
    "Faculty Handbook",
    "Advisory Board Minutes"
]