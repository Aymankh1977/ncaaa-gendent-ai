from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.enums import TA_JUSTIFY
import io
from datetime import datetime

# ETEC Purple and Teal
ETEC_PURPLE = colors.Color(75/255, 0/255, 130/255)
ETEC_TEAL = colors.Color(0/255, 128/255, 128/255)

def create_styles():
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name='ETEC_Title', parent=styles['Title'], 
        fontName='Helvetica-Bold', fontSize=22, 
        textColor=ETEC_PURPLE, spaceAfter=20, alignment=0
    ))
    styles.add(ParagraphStyle(
        name='ETEC_Header', parent=styles['Heading2'], 
        fontName='Helvetica-Bold', fontSize=14, 
        textColor=ETEC_TEAL, spaceBefore=15, spaceAfter=10
    ))
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
    
    story.append(Paragraph("ETEC 2025 Compliance Report", styles['ETEC_Title']))
    story.append(Paragraph(f"Standard: {req_title}", styles['Heading3']))
    story.append(Paragraph(f"Date: {datetime.now().strftime('%Y-%m-%d')}", styles['Normal']))
    story.append(Spacer(1, 20))
    
    sections = [
        ("1. Standard Definition (2025 Ver 2.0)", 'definition'),
        ("2. Evidence of Compliance", 'indicators'),
        ("3. Gaps & Pitfalls", 'pitfalls'),
        ("4. Best Practice / Highlight", 'best_practice')
    ]
    
    for title, key in sections:
        story.append(Paragraph(title, styles['ETEC_Header']))
        content = data_dict.get(key, 'N/A')
        
        if isinstance(content, list):
            for item in content:
                story.append(Paragraph(f"• {item}", styles['ETEC_Body']))
        else:
            story.append(Paragraph(str(content), styles['ETEC_Body']))
        
        story.append(Spacer(1, 10))
        
    doc.build(story)
    buffer.seek(0)
    return buffer
