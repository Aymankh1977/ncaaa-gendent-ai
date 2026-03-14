import io
import re
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, PageBreak, KeepTogether
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY, TA_RIGHT

# ── Brand & Colour palette ─────────────────────────────────────────────────────
BRAND_NAME  = "DentEdTech"
DARK_BLUE   = colors.HexColor("#1a3a5c")
MID_BLUE    = colors.HexColor("#2e6da4")
LIGHT_BLUE  = colors.HexColor("#dce9f5")
TEAL        = colors.HexColor("#00695c")
GREEN       = colors.HexColor("#2e7d32")
AMBER       = colors.HexColor("#e65100")
LIGHT_GREY  = colors.HexColor("#f5f5f5")
MID_GREY    = colors.HexColor("#9e9e9e")
DARK_GREY   = colors.HexColor("#424242")
WHITE       = colors.white
BLACK       = colors.black

PAGE_W = 17 * cm   # usable width on A4 with 2 cm margins each side


# ── Styles ─────────────────────────────────────────────────────────────────────

def _build_styles():
    base = getSampleStyleSheet()
    s = {}

    s["brand"] = ParagraphStyle(
        "brand", parent=base["Normal"],
        fontSize=11, textColor=TEAL, alignment=TA_CENTER,
        fontName="Helvetica-Bold", spaceAfter=2
    )
    s["cover_title"] = ParagraphStyle(
        "cover_title", parent=base["Title"],
        fontSize=26, leading=32, textColor=WHITE,
        alignment=TA_CENTER, spaceAfter=6
    )
    s["cover_sub"] = ParagraphStyle(
        "cover_sub", parent=base["Normal"],
        fontSize=13, textColor=LIGHT_BLUE,
        alignment=TA_CENTER, spaceAfter=4
    )
    s["cover_meta"] = ParagraphStyle(
        "cover_meta", parent=base["Normal"],
        fontSize=10, textColor=MID_GREY, alignment=TA_CENTER
    )
    s["section_heading"] = ParagraphStyle(
        "section_heading", parent=base["Heading1"],
        fontSize=13, leading=17, textColor=DARK_BLUE,
        spaceBefore=14, spaceAfter=5, fontName="Helvetica-Bold"
    )
    s["sub_heading"] = ParagraphStyle(
        "sub_heading", parent=base["Heading2"],
        fontSize=11, leading=14, textColor=MID_BLUE,
        spaceBefore=10, spaceAfter=4, fontName="Helvetica-Bold"
    )
    s["sub_sub_heading"] = ParagraphStyle(
        "sub_sub_heading", parent=base["Heading3"],
        fontSize=10, leading=13, textColor=DARK_GREY,
        spaceBefore=7, spaceAfter=3, fontName="Helvetica-Bold"
    )
    s["body"] = ParagraphStyle(
        "body", parent=base["Normal"],
        fontSize=10, leading=15, textColor=BLACK,
        alignment=TA_JUSTIFY, spaceAfter=5
    )
    s["bullet"] = ParagraphStyle(
        "bullet", parent=base["Normal"],
        fontSize=10, leading=14, textColor=BLACK,
        leftIndent=18, spaceAfter=3
    )
    s["table_header"] = ParagraphStyle(
        "table_header", parent=base["Normal"],
        fontSize=9, leading=12, textColor=WHITE,
        fontName="Helvetica-Bold", alignment=TA_CENTER
    )
    s["table_cell"] = ParagraphStyle(
        "table_cell", parent=base["Normal"],
        fontSize=9, leading=12, textColor=BLACK, alignment=TA_LEFT
    )
    s["table_cell_center"] = ParagraphStyle(
        "table_cell_center", parent=base["Normal"],
        fontSize=9, leading=12, textColor=BLACK, alignment=TA_CENTER
    )
    s["caption"] = ParagraphStyle(
        "caption", parent=base["Normal"],
        fontSize=8, textColor=MID_GREY, alignment=TA_CENTER, spaceAfter=4
    )
    s["footer_text"] = ParagraphStyle(
        "footer_text", parent=base["Normal"],
        fontSize=8, textColor=MID_GREY, alignment=TA_CENTER
    )
    s["request_box"] = ParagraphStyle(
        "request_box", parent=base["Normal"],
        fontSize=10, textColor=MID_BLUE,
        leftIndent=12, leading=14, backColor=LIGHT_BLUE
    )
    return s


# ── Cover page ─────────────────────────────────────────────────────────────────

def _cover_page(story, styles, title: str, subtitle: str, report_type: str):
    # Brand name above banner
    story.append(Spacer(1, 2.5 * cm))
    story.append(Paragraph(BRAND_NAME, styles["brand"]))
    story.append(Spacer(1, 0.3 * cm))

    # Dark banner
    banner = Table([[Paragraph(title, styles["cover_title"])]], colWidths=[PAGE_W])
    banner.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), DARK_BLUE),
        ("TOPPADDING",    (0, 0), (-1, -1), 28),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 28),
        ("LEFTPADDING",   (0, 0), (-1, -1), 20),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 20),
    ]))
    story.append(banner)
    story.append(Spacer(1, 0.6 * cm))

    story.append(Paragraph(subtitle, styles["cover_sub"]))
    story.append(Spacer(1, 0.3 * cm))
    story.append(HRFlowable(width="60%", color=TEAL, thickness=2))
    story.append(Spacer(1, 0.3 * cm))

    for line in [
        f"Report Type: {report_type}",
        f"Generated: {datetime.now().strftime('%d %B %Y, %H:%M')}",
        f"Powered by {BRAND_NAME} — Accreditation Intelligence Platform",
    ]:
        story.append(Paragraph(line, styles["cover_meta"]))
        story.append(Spacer(1, 0.12 * cm))

    story.append(PageBreak())


# ── Footer helper ──────────────────────────────────────────────────────────────

def _footer(story, styles):
    story.append(Spacer(1, 0.6 * cm))
    story.append(HRFlowable(width="100%", color=LIGHT_GREY, thickness=1))
    story.append(Spacer(1, 0.2 * cm))
    story.append(Paragraph(
        f"{BRAND_NAME} — Accreditation Intelligence Platform  |  "
        f"{datetime.now().strftime('%d %B %Y')}",
        styles["footer_text"]
    ))


# ── Metric cards ───────────────────────────────────────────────────────────────

def _metric_table(story, styles, items: list):
    col_w = PAGE_W / max(len(items), 1)
    data = [
        [Paragraph(v, ParagraphStyle("mv", fontSize=15, textColor=MID_BLUE,
                                      alignment=TA_CENTER, fontName="Helvetica-Bold"))
         for _, v in items],
        [Paragraph(l, ParagraphStyle("ml", fontSize=8, textColor=MID_GREY,
                                      alignment=TA_CENTER))
         for l, _ in items]
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


# ── Markdown table parser ──────────────────────────────────────────────────────

def _parse_md_table(lines: list) -> list:
    """
    Given a list of raw markdown table lines (including the separator line),
    returns a list of rows where each row is a list of cell strings.
    Separator lines (---|---) are dropped.
    """
    rows = []
    for line in lines:
        line = line.strip()
        if not line or re.match(r'^[\|\s\-:]+$', line):
            continue   # skip separator rows
        cells = [c.strip() for c in line.strip('|').split('|')]
        if any(cells):
            rows.append(cells)
    return rows


def _render_md_table(story, styles, rows: list):
    """
    Renders a parsed markdown table as a proper ReportLab table.
    First row is treated as header.
    Columns are auto-sized evenly across PAGE_W.
    """
    if not rows:
        return

    num_cols = max(len(r) for r in rows)
    # Pad short rows
    rows = [r + [""] * (num_cols - len(r)) for r in rows]

    # Determine column widths — bold column 0 slightly wider if 3+ cols
    if num_cols >= 3:
        col_widths = [PAGE_W * 0.30] + [PAGE_W * 0.70 / (num_cols - 1)] * (num_cols - 1)
    else:
        col_widths = [PAGE_W / num_cols] * num_cols

    table_data = []
    for r_idx, row in enumerate(rows):
        if r_idx == 0:
            # Header row
            table_data.append([
                Paragraph(str(cell), styles["table_header"]) for cell in row
            ])
        else:
            table_data.append([
                Paragraph(str(cell), styles["table_cell"]) for cell in row
            ])

    t = Table(table_data, colWidths=col_widths, repeatRows=1)
    t.setStyle(TableStyle([
        # Header
        ("BACKGROUND",    (0, 0), (-1, 0),  DARK_BLUE),
        ("TEXTCOLOR",     (0, 0), (-1, 0),  WHITE),
        ("FONTNAME",      (0, 0), (-1, 0),  "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0), (-1, 0),  9),
        # Body
        ("BACKGROUND",    (0, 1), (-1, -1), WHITE),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [WHITE, LIGHT_GREY]),
        ("FONTNAME",      (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE",      (0, 1), (-1, -1), 9),
        ("TEXTCOLOR",     (0, 1), (-1, -1), BLACK),
        # Borders
        ("BOX",           (0, 0), (-1, -1), 0.8, MID_BLUE),
        ("INNERGRID",     (0, 0), (-1, -1), 0.4, MID_GREY),
        # Padding
        ("TOPPADDING",    (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING",   (0, 0), (-1, -1), 6),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 6),
        ("VALIGN",        (0, 0), (-1, -1), "TOP"),
    ]))
    story.append(KeepTogether([t, Spacer(1, 0.3 * cm)]))


# ── Markdown content renderer ──────────────────────────────────────────────────

def _render_markdown(story, styles, text: str):
    """
    Full markdown renderer supporting:
      - # ## ### headings
      - **bold** inline (stripped for PDF — rendered as sub_heading)
      - - bullet lists
      - | markdown tables |
      - blank lines as spacing
      - plain paragraphs
    """
    lines = text.split("\n")
    i = 0
    while i < len(lines):
        raw   = lines[i]
        stripped = raw.strip()

        # ── Blank line ──
        if not stripped:
            story.append(Spacer(1, 0.12 * cm))
            i += 1
            continue

        # ── Markdown table — collect all consecutive table lines ──
        if stripped.startswith("|") and "|" in stripped[1:]:
            table_lines = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                table_lines.append(lines[i])
                i += 1
            rows = _parse_md_table(table_lines)
            _render_md_table(story, styles, rows)
            continue

        # ── Headings ──
        if stripped.startswith("### "):
            story.append(Paragraph(stripped[4:].strip(), styles["sub_sub_heading"]))
            i += 1
            continue
        if stripped.startswith("## "):
            story.append(Paragraph(stripped[3:].strip(), styles["sub_heading"]))
            i += 1
            continue
        if stripped.startswith("# "):
            story.append(Paragraph(stripped[2:].strip(), styles["section_heading"]))
            i += 1
            continue

        # ── Horizontal rule ──
        if re.match(r'^[-=]{3,}$', stripped):
            story.append(HRFlowable(width="100%", color=LIGHT_GREY, thickness=1))
            story.append(Spacer(1, 0.1 * cm))
            i += 1
            continue

        # ── Bullet ──
        if stripped.startswith("- ") or stripped.startswith("• "):
            clean = stripped.lstrip("-• ").strip()
            # Strip inline **bold** markers for PDF
            clean = re.sub(r'\*\*(.*?)\*\*', r'\1', clean)
            story.append(Paragraph(f"• {clean}", styles["bullet"]))
            i += 1
            continue

        # ── Numbered list ──
        if re.match(r'^\d+\.\s', stripped):
            clean = re.sub(r'^\d+\.\s*', '', stripped)
            clean = re.sub(r'\*\*(.*?)\*\*', r'\1', clean)
            story.append(Paragraph(f"• {clean}", styles["bullet"]))
            i += 1
            continue

        # ── Bold-only line (treat as sub-sub-heading) ──
        if re.match(r'^\*\*(.+)\*\*$', stripped):
            heading_text = stripped.strip("*").strip()
            story.append(Paragraph(heading_text, styles["sub_sub_heading"]))
            i += 1
            continue

        # ── Plain paragraph (strip remaining inline markdown) ──
        clean = re.sub(r'\*\*(.*?)\*\*', r'\1', stripped)   # **bold**
        clean = re.sub(r'\*(.*?)\*',     r'\1', clean)       # *italic*
        clean = re.sub(r'`(.*?)`',       r'\1', clean)       # `code`
        story.append(Paragraph(clean, styles["body"]))
        i += 1


# ── Bullet list helper ─────────────────────────────────────────────────────────

def _bullet_list(story, styles, heading: str, items: list):
    if not items:
        return
    story.append(Paragraph(heading, styles["sub_heading"]))
    for item in items:
        clean = re.sub(r'\*\*(.*?)\*\*', r'\1', str(item).lstrip("-• ").strip())
        story.append(Paragraph(f"• {clean}", styles["bullet"]))
    story.append(Spacer(1, 0.3 * cm))


# ── Citations table ────────────────────────────────────────────────────────────

def _citations_table(story, styles, citations: list):
    if not citations:
        return
    story.append(Paragraph("Source Citations", styles["sub_heading"]))
    rows = [
        [Paragraph(f"[{i+1}]", ParagraphStyle("cn", fontSize=8, textColor=MID_BLUE)),
         Paragraph(str(c),     ParagraphStyle("ct", fontSize=8, textColor=BLACK, leading=11))]
        for i, c in enumerate(citations)
    ]
    t = Table(rows, colWidths=[1 * cm, PAGE_W - 1 * cm])
    t.setStyle(TableStyle([
        ("VALIGN",        (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING",    (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("ROWBACKGROUNDS",(0, 0), (-1, -1), [WHITE, LIGHT_GREY]),
        ("LINEBELOW",     (0, 0), (-1, -1), 0.3, MID_GREY),
    ]))
    story.append(t)


# ══════════════════════════════════════════════════════════════════════════════
# PUBLIC BUILDERS
# ══════════════════════════════════════════════════════════════════════════════

def build_audit_pdf(standard_name: str, analysis: dict) -> bytes:
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
    for para in analysis.get("reviewer_comment", "").split("\n\n"):
        if para.strip():
            story.append(Paragraph(re.sub(r'\*\*(.*?)\*\*', r'\1', para.strip()), styles["body"]))

    story.append(Spacer(1, 0.4 * cm))
    _bullet_list(story, styles, "Strengths",           analysis.get("strengths", []))
    _bullet_list(story, styles, "Areas for Improvement", analysis.get("areas_for_improvement", []))

    citations = analysis.get("citations", [])
    if citations:
        story.append(PageBreak())
        story.append(Paragraph("Document Evidence & Citations", styles["section_heading"]))
        story.append(HRFlowable(width="100%", color=LIGHT_BLUE, thickness=1))
        story.append(Spacer(1, 0.2 * cm))
        _citations_table(story, styles, citations)

    _footer(story, styles)
    doc.build(story)
    return buf.getvalue()


def build_nqf_pdf(nqf_text: str) -> bytes:
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
    _render_markdown(story, styles, nqf_text)

    story.append(Spacer(1, 0.4 * cm))
    story.append(Paragraph(
        f"Report generated on {datetime.now().strftime('%d %B %Y at %H:%M')}",
        styles["caption"]
    ))
    _footer(story, styles)
    doc.build(story)
    return buf.getvalue()


def build_ssr_pdf(question: str, ssr_text: str) -> bytes:
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

    # Request box
    story.append(Paragraph("Request", styles["sub_heading"]))
    story.append(Paragraph(question, styles["request_box"]))
    story.append(Spacer(1, 0.5 * cm))

    story.append(Paragraph("Drafted Content", styles["section_heading"]))
    story.append(HRFlowable(width="100%", color=LIGHT_BLUE, thickness=1))
    story.append(Spacer(1, 0.3 * cm))

    # Full markdown render — handles tables, headings, bullets, paragraphs
    _render_markdown(story, styles, ssr_text)

    _footer(story, styles)
    doc.build(story)
    return buf.getvalue()