import io
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, PageBreak
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY


# ── Colour palette ─────────────────────────────────────────────────────────────
DARK_BLUE   = colors.HexColor("#1a3a5c")
MID_BLUE    = colors.HexColor("#2e6da4")
LIGHT_BLUE  = colors.HexColor("#dce9f5")
GREEN       = colors.HexColor("#2e7d32")
AMBER       = colors.HexColor("#e65100")
LIGHT_GREY  = colors.HexColor("#f5f5f5")
MID_GREY    = colors.HexColor("#9e9e9e")
WHITE       = colors.white
BLACK       = colors.black


def _build_styles():
    base = getSampleStyleSheet()
    styles = {}

    styles["cover_title"] = ParagraphStyle(
        "cover_title", parent=base["Title"],
        fontSize=26, leading=32, textColor=WHITE,
        alignment=TA_CENTER, spaceAfter=6
    )
    styles["cover_sub"] = ParagraphStyle(
        "cover_sub", parent=base["Normal"],
        fontSize=13, textColor=LIGHT_BLUE,
        alignment=TA_CENTER, spaceAfter=4
    )
    styles["cover_meta"] = ParagraphStyle(
        "cover_meta", parent=base["Normal"],
        fontSize=10, textColor=MID_GREY,
        alignment=TA_CENTER
    )
    styles["section_heading"] = ParagraphStyle(
        "section_heading", parent=base["Heading1"],
        fontSize=14, leading=18, textColor=DARK_BLUE,
        spaceBefore=14, spaceAfter=6
    )
    styles["sub_heading"] = ParagraphStyle(
        "sub_heading", parent=base["Heading2"],
        fontSize=11, leading=14, textColor=MID_BLUE,
        spaceBefore=10, spaceAfter=4
    )
    styles["body"] = ParagraphStyle(
        "body", parent=base["Normal"],
        fontSize=10, leading=15, textColor=BLACK,
        alignment=TA_JUSTIFY, spaceAfter=6
    )
    styles["bullet"] = ParagraphStyle(
        "bullet", parent=base["Normal"],
        fontSize=10, leading=14, textColor=BLACK,
        leftIndent=16, spaceAfter=3,
        bulletIndent=4
    )
    styles["caption"] = ParagraphStyle(
        "caption", parent=base["Normal"],
        fontSize=8, textColor=MID_GREY,
        alignment=TA_CENTER, spaceAfter=4
    )
    styles["footer_text"] = ParagraphStyle(
        "footer_text", parent=base["Normal"],
        fontSize=8, textColor=MID_GREY,
        alignment=TA_CENTER
    )
    return styles


def _cover_page(story, styles, title, subtitle, report_type):
    banner_data = [[Paragraph(title, styles["cover_title"])]]
    banner = Table(banner_data, colWidths=[17 * cm])
    banner.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), DARK_BLUE),
        ("TOPPADDING",    (0, 0), (-1, -1), 30),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 30),
        ("LEFTPADDING",   (0, 0), (-1, -1), 20),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 20),
    ]))
    story.append(Spacer(1, 3 * cm))
    story.append(banner)
    story.append(Spacer(1, 0.6 * cm))
    story.append(Paragraph(subtitle, styles["cover_sub"]))
    story.append(Spacer(1, 0.3 * cm))
    story.append(HRFlowable(width="60%", color=MID_BLUE, thickness=1))
    story.append(Spacer(1, 0.3 * cm))
    for line in [f"Report Type: {report_type}",
                 f"Generated: {datetime.now().strftime('%d %B %Y, %H:%M')}",
                 "Accreditation Intelligence Platform"]:
        story.append(Paragraph(line, styles["cover_meta"]))
        story.append(Spacer(1, 0.15 * cm))
    story.append(PageBreak())


def _metric_table(story, styles, items):
    col_w = 17 * cm / max(len(items), 1)
    data = [
        [Paragraph(v, ParagraphStyle("mv", fontSize=16, textColor=MID_BLUE, alignment=TA_CENTER)) for _, v in items],
        [Paragraph(l, ParagraphStyle("ml", fontSize=8,  textColor=MID_GREY, alignment=TA_CENTER)) for l, _ in items]
    ]
    t = Table(data, colWidths=[col_w] * len(items))
    t.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), LIGHT_GREY),
        ("BOX",           (0, 0), (-1, -1), 0.5, MID_GREY),
        ("INNERGRID",     (0, 0), (-1, -1), 0.3, MID_GREY),
        ("TOPPADDING",    (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(t)
    story.append(Spacer(1, 0.4 * cm))


def _bullet_list(story, styles, heading, items):
    if not items:
        return
    story.append(Paragraph(heading, styles["sub_heading"]))
    for item in items:
        story.append(Paragraph(f"• {str(item).lstrip('-• ').strip()}", styles["bullet"]))
    story.append(Spacer(1, 0.3 * cm))


def _citations_table(story, styles, citations):
    if not citations:
        return
    story.append(Paragraph("Source Citations", styles["sub_heading"]))
    rows = [
        [Paragraph(f"[{i+1}]", ParagraphStyle("cn", fontSize=8, textColor=MID_BLUE)),
         Paragraph(str(c),     ParagraphStyle("ct", fontSize=8, textColor=BLACK, leading=11))]
        for i, c in enumerate(citations)
    ]
    t = Table(rows, colWidths=[1 * cm, 16 * cm])
    t.setStyle(TableStyle([
        ("VALIGN",        (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING",    (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("ROWBACKGROUNDS",(0, 0), (-1, -1), [WHITE, LIGHT_GREY]),
        ("LINEBELOW",     (0, 0), (-1, -1), 0.3, MID_GREY),
    ]))
    story.append(t)


def build_audit_pdf(standard_name, analysis):
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
                            leftMargin=2*cm, rightMargin=2*cm,
                            topMargin=2*cm, bottomMargin=2*cm)
    styles = _build_styles()
    story  = []

    _cover_page(story, styles,
                title="Compliance Audit Report",
                subtitle=standard_name,
                report_type="Standard Compliance Review")

    _metric_table(story, styles, [
        ("Compliance Rating", analysis.get("compliance_rating", "N/A")),
        ("Relevance",         analysis.get("relevance", "N/A")),
        ("Generated",         datetime.now().strftime("%d %b %Y")),
    ])

    story.append(Paragraph("Reviewer Assessment", styles["section_heading"]))
    story.append(HRFlowable(width="100%", color=LIGHT_BLUE, thickness=1))
    story.append(Spacer(1, 0.2 * cm))
    for para in analysis.get("reviewer_comment", "No comment generated.").split("\n\n"):
        if para.strip():
            story.append(Paragraph(para.strip(), styles["body"]))

    story.append(Spacer(1, 0.4 * cm))
    _bullet_list(story, styles, "Strengths", analysis.get("strengths", []))

    story.append(Paragraph("Areas for Improvement", styles["sub_heading"]))
    for item in analysis.get("areas_for_improvement", []):
        story.append(Paragraph(f"• {str(item).lstrip('-• ').strip()}", styles["bullet"]))
    story.append(Spacer(1, 0.3 * cm))

    story.append(PageBreak())
    story.append(Paragraph("Document Evidence & Citations", styles["section_heading"]))
    story.append(HRFlowable(width="100%", color=LIGHT_BLUE, thickness=1))
    story.append(Spacer(1, 0.2 * cm))
    _citations_table(story, styles, analysis.get("citations", []))

    doc.build(story)
    return buf.getvalue()


def build_nqf_pdf(nqf_text):
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
                            leftMargin=2*cm, rightMargin=2*cm,
                            topMargin=2*cm, bottomMargin=2*cm)
    styles = _build_styles()
    story  = []

    _cover_page(story, styles,
                title="NQF Alignment Report",
                subtitle="Program Learning Outcomes — Level 6 Review",
                report_type="NQF Alignment Analysis")

    story.append(Paragraph("Alignment Analysis", styles["section_heading"]))
    story.append(HRFlowable(width="100%", color=LIGHT_BLUE, thickness=1))
    story.append(Spacer(1, 0.3 * cm))

    for line in nqf_text.split("\n"):
        stripped = line.strip()
        if not stripped:
            story.append(Spacer(1, 0.15 * cm))
        elif stripped.startswith("##") or stripped.startswith("**"):
            story.append(Paragraph(stripped.lstrip("#* ").rstrip("*: "), styles["sub_heading"]))
        elif stripped.startswith("- ") or stripped.startswith("• "):
            story.append(Paragraph(f"• {stripped.lstrip('-• ')}", styles["bullet"]))
        else:
            story.append(Paragraph(stripped, styles["body"]))

    story.append(Spacer(1, 0.4 * cm))
    story.append(Paragraph(
        f"Report generated on {datetime.now().strftime('%d %B %Y at %H:%M')}",
        styles["caption"]
    ))
    doc.build(story)
    return buf.getvalue()


def build_ssr_pdf(question, ssr_text):
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
                            leftMargin=2*cm, rightMargin=2*cm,
                            topMargin=2*cm, bottomMargin=2*cm)
    styles = _build_styles()
    story  = []

    _cover_page(story, styles,
                title="Self-Study Report",
                subtitle="SSR Assistant — Drafted Section",
                report_type="SSR Narrative Draft")

    story.append(Paragraph("Request", styles["sub_heading"]))
    story.append(Paragraph(question, ParagraphStyle(
        "q_style", fontSize=10, textColor=MID_BLUE,
        leftIndent=12, leading=14, backColor=LIGHT_BLUE
    )))
    story.append(Spacer(1, 0.5 * cm))
    story.append(Paragraph("Drafted Content", styles["section_heading"]))
    story.append(HRFlowable(width="100%", color=LIGHT_BLUE, thickness=1))
    story.append(Spacer(1, 0.3 * cm))

    for line in ssr_text.split("\n"):
        stripped = line.strip()
        if not stripped:
            story.append(Spacer(1, 0.15 * cm))
        elif stripped.startswith("##") or stripped.startswith("**"):
            story.append(Paragraph(stripped.lstrip("#* ").rstrip("*: "), styles["sub_heading"]))
        elif stripped.startswith("- ") or stripped.startswith("• "):
            story.append(Paragraph(f"• {stripped.lstrip('-• ')}", styles["bullet"]))
        else:
            story.append(Paragraph(stripped, styles["body"]))

    story.append(Spacer(1, 0.6 * cm))
    story.append(HRFlowable(width="100%", color=LIGHT_GREY, thickness=1))
    story.append(Spacer(1, 0.2 * cm))
    story.append(Paragraph(
        f"Generated by Accreditation Intelligence Platform  |  {datetime.now().strftime('%d %B %Y')}",
        styles["footer_text"]
    ))
    doc.build(story)
    return buf.getvalue()
