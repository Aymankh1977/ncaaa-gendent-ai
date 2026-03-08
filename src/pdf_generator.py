from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable
from reportlab.lib.enums import TA_JUSTIFY, TA_CENTER
import io
from datetime import datetime

# ETEC Colors
ETEC_PURPLE = colors.Color(75/255, 0/255, 130/255)
ETEC_TEAL = colors.Color(0/255, 128/255, 128/255)
TAIBAH_BLUE = colors.Color(0/255, 105/255, 180/255) # Approx Taibah Blue

def create_styles():
    styles = getSampleStyleSheet()
    
    # Title Style
    styles.add(ParagraphStyle(
        name='ETEC_Title', parent=styles['Title'], 
        fontName='Helvetica-Bold', fontSize=22, 
        textColor=ETEC_PURPLE, spaceAfter=12, alignment=0
    ))
    
    # Acknowledgement Style
    styles.add(ParagraphStyle(
        name='Taibah_Credit', parent=styles['Normal'],
        fontName='Helvetica-Oblique', fontSize=10,
        textColor=TAIBAH_BLUE, leading=14, spaceAfter=20, alignment=0
    ))

    # Standard Headers
    styles.add(ParagraphStyle(
        name='ETEC_Header', parent=styles['Heading2'], 
        fontName='Helvetica-Bold', fontSize=14, 
        textColor=ETEC_TEAL, spaceBefore=15, spaceAfter=10
    ))
    
    # Body Text
    styles.add(ParagraphStyle(
        name='ETEC_Body', parent=styles['Normal'], 
        fontSize=11, leading=16, alignment=TA_JUSTIFY
    ))
    return styles

def generate_pdf_report(data_dict, req_title):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4, 
        rightMargin=72, leftMargin=72, topMargin=72, bottomMargin=72
    )
    styles = create_styles()
    story = []
    
    # --- TITLE SECTION ---
    story.append(Paragraph("NCAAA Accreditation Compliance Report", styles['ETEC_Title']))
    
    # --- ACKNOWLEDGEMENT SECTION ---
    credit_text = """
    <b>Framework & Methodology Acknowledgement:</b><br/>
    Quality Assurance and Academic Accreditation Unit,<br/>
    College of Dentistry, Taibah University.
    """
    story.append(Paragraph(credit_text, styles['Taibah_Credit']))
    
    story.append(HRFlowable(width="100%", thickness=1, color=colors.lightgrey))
    story.append(Spacer(1, 15))
    
    # --- REPORT METADATA ---
    story.append(Paragraph(f"<b>Target Standard:</b> {req_title}", styles['Normal']))
    story.append(Paragraph(f"<b>Date Generated:</b> {datetime.now().strftime('%Y-%m-%d')}", styles['Normal']))
    story.append(Spacer(1, 20))
    
    # --- CONTENT CONTENT ---
    # Handle different report types (Compliance vs Governance Audit)
    # We map keys loosely to ensure it works for both Tab 1 and Tab 2
    
    # 1. Definition / Status
    if 'compliance_status' in data_dict:
        story.append(Paragraph(f"Governance Status: {data_dict['compliance_status']}", styles['ETEC_Header']))
    if 'definition' in data_dict:
        story.append(Paragraph("Standard Definition", styles['ETEC_Header']))
        story.append(Paragraph(data_dict['definition'], styles['ETEC_Body']))

    # 2. Indicators / Policy Strengths
    keys_positive = ['indicators', 'policy_strengths', 'policy_evidence']
    for k in keys_positive:
        if k in data_dict and data_dict[k]:
            story.append(Paragraph("Evidence of Compliance / Policy", styles['ETEC_Header']))
            for item in data_dict[k]:
                story.append(Paragraph(f"✓ {item}", styles['ETEC_Body']))

    # 3. Pitfalls / Implementation / Gaps
    keys_implementation = ['implementation_evidence']
    for k in keys_implementation:
        if k in data_dict and data_dict[k]:
            story.append(Paragraph("Evidence of Implementation", styles['ETEC_Header']))
            for item in data_dict[k]:
                story.append(Paragraph(f"✓ {item}", styles['ETEC_Body']))

    keys_negative = ['pitfalls', 'governance_gaps', 'identified_gaps']
    for k in keys_negative:
        if k in data_dict and data_dict[k]:
            story.append(Paragraph("Gaps & Areas for Improvement", styles['ETEC_Header']))
            for item in data_dict[k]:
                story.append(Paragraph(f"⚠ {item}", styles['ETEC_Body']))

    # 4. Best Practice / Recommendation
    keys_final = ['best_practice', 'recommendation']
    for k in keys_final:
        if k in data_dict and data_dict[k]:
            story.append(Paragraph("Recommendations & Best Practices", styles['ETEC_Header']))
            story.append(Paragraph(str(data_dict[k]), styles['ETEC_Body']))
        
    doc.build(story)
    buffer.seek(0)
    return buffer
