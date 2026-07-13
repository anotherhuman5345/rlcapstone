"""Generate a professional PDF capstone report for every project.

One reusable renderer (reportlab) + a content block per project, so all six
reports share a clean, consistent look. Output: dist/reports/<slug>.pdf

Body text supports **bold** markup; tables and callouts are styled per project
accent colour. Written to be readable by a general audience while still
reporting the honest metrics (including the negative results).
"""

from __future__ import annotations

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (BaseDocTemplate, Frame, HRFlowable, ListFlowable,
                                ListItem, PageBreak, PageTemplate, Paragraph,
                                Spacer, Table, TableStyle)

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "dist" / "reports"
AUTHOR = "Arel"
SITE = "RLcapstone.ai"


def esc(t: str) -> str:
    t = t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    parts = t.split("**")
    return "".join(f"<b>{p}</b>" if i % 2 else p for i, p in enumerate(parts))


# ---------------------------------------------------------------- renderer ----
def build(project: dict) -> None:
    accent = colors.HexColor(project["accent"])
    dark = colors.HexColor("#1a2b29")
    grey = colors.HexColor("#555555")
    light = colors.HexColor(project["accent"]).clone()

    styles = getSampleStyleSheet()
    body = ParagraphStyle("body", parent=styles["Normal"], fontName="Helvetica",
                          fontSize=10.5, leading=15, textColor=dark, spaceAfter=7)
    h1 = ParagraphStyle("h1", fontName="Helvetica-Bold", fontSize=14,
                        textColor=accent, spaceBefore=6, spaceAfter=4)
    h2 = ParagraphStyle("h2", fontName="Helvetica-Bold", fontSize=11.5,
                        textColor=dark, spaceBefore=6, spaceAfter=3)
    bullet_style = ParagraphStyle("bul", parent=body, spaceAfter=3)
    callout_style = ParagraphStyle("call", parent=body, textColor=dark, spaceAfter=0)

    def flow_para(t):
        return Paragraph(esc(t), body)

    def flow_table(headers, rows):
        data = [[Paragraph(esc(h), ParagraphStyle("th", fontName="Helvetica-Bold",
                fontSize=9.5, textColor=colors.white, leading=12)) for h in headers]]
        for r in rows:
            data.append([Paragraph(esc(str(c)), ParagraphStyle("td", fontName="Helvetica",
                        fontSize=9.5, textColor=dark, leading=12)) for c in r])
        t = Table(data, hAlign="LEFT", colWidths=None)
        ts = [("BACKGROUND", (0, 0), (-1, 0), accent),
              ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cfd8d6")),
              ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
              ("LEFTPADDING", (0, 0), (-1, -1), 6),
              ("RIGHTPADDING", (0, 0), (-1, -1), 6),
              ("TOPPADDING", (0, 0), (-1, -1), 4),
              ("BOTTOMPADDING", (0, 0), (-1, -1), 4)]
        for ri in range(1, len(data)):
            if ri % 2 == 0:
                ts.append(("BACKGROUND", (0, ri), (-1, ri), colors.HexColor("#f4f7f6")))
        t.setStyle(TableStyle(ts))
        return t

    def flow_callout(t):
        inner = Paragraph(esc(t), callout_style)
        tbl = Table([[inner]], colWidths=[6.6 * inch])
        tbl.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor(project["accent"] + "14")
                if False else _tint(project["accent"])),
            ("LEFTPADDING", (0, 0), (-1, -1), 10), ("RIGHTPADDING", (0, 0), (-1, -1), 10),
            ("TOPPADDING", (0, 0), (-1, -1), 8), ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ("LINEBEFORE", (0, 0), (0, -1), 3, accent)]))
        return tbl

    def flow_bullets(items):
        return ListFlowable(
            [ListItem(Paragraph(esc(it), bullet_style), leftIndent=12,
                      value="•") for it in items],
            bulletType="bullet", start="•", leftIndent=14)

    story = []
    # title page
    story += [Spacer(1, 2.1 * inch)]
    story.append(Paragraph(project["title"], ParagraphStyle("t", fontName="Helvetica-Bold",
                 fontSize=38, textColor=accent, alignment=TA_CENTER, leading=42)))
    story.append(Spacer(1, 6))
    story.append(Paragraph(project["subtitle"], ParagraphStyle("s", fontName="Helvetica",
                 fontSize=15, textColor=dark, alignment=TA_CENTER, leading=20)))
    story.append(Spacer(1, 14))
    story.append(Paragraph("Capstone Project Report", ParagraphStyle("cpr",
                 fontName="Helvetica-Oblique", fontSize=12.5, textColor=grey, alignment=TA_CENTER)))
    story.append(Spacer(1, 26))
    story.append(Paragraph(esc(project["tagline"]), ParagraphStyle("tag", fontName="Helvetica",
                 fontSize=10.5, textColor=grey, alignment=TA_CENTER, leading=15)))
    story.append(Spacer(1, 40))
    story.append(Paragraph(f"{AUTHOR} &nbsp;·&nbsp; {SITE}", ParagraphStyle("auth",
                 fontName="Helvetica-Bold", fontSize=11, textColor=dark, alignment=TA_CENTER)))
    story.append(PageBreak())

    # sections
    for i, (heading, elements) in enumerate(project["sections"], 1):
        story.append(Paragraph(f"{i}. {esc(heading)}", h1))
        story.append(HRFlowable(width="100%", thickness=0.7, color=colors.HexColor("#cccccc"),
                                spaceBefore=1, spaceAfter=6))
        for el in elements:
            if isinstance(el, str):
                story.append(flow_para(el))
            elif el[0] == "h2":
                story.append(Paragraph(esc(el[1]), h2))
            elif el[0] == "table":
                story.append(flow_table(el[1], el[2]))
                story.append(Spacer(1, 8))
            elif el[0] == "bullets":
                story.append(flow_bullets(el[1]))
                story.append(Spacer(1, 6))
            elif el[0] == "callout":
                story.append(flow_callout(el[1]))
                story.append(Spacer(1, 8))
        story.append(Spacer(1, 4))

    # page furniture
    def footer(canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(grey)
        canvas.drawString(0.9 * inch, 0.55 * inch,
                          f"{project['title']} — Capstone Report")
        canvas.drawRightString(7.6 * inch, 0.55 * inch, f"{SITE}")
        if doc.page > 1:
            canvas.drawCentredString(4.25 * inch, 0.55 * inch, str(doc.page))
        canvas.restoreState()

    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / f"{project['slug']}.pdf"
    doc = BaseDocTemplate(str(path), pagesize=letter,
                          leftMargin=0.9 * inch, rightMargin=0.9 * inch,
                          topMargin=0.8 * inch, bottomMargin=0.9 * inch,
                          title=f"{project['title']} — Capstone Report", author=AUTHOR)
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="main")
    doc.addPageTemplates([PageTemplate(id="all", frames=[frame], onPage=footer)])
    doc.build(story)
    print(f"wrote {path}")


def _tint(hex_color: str):
    """Light tint of an accent colour for callout backgrounds."""
    c = colors.HexColor(hex_color)
    return colors.Color(1 - (1 - c.red) * 0.12, 1 - (1 - c.green) * 0.12,
                        1 - (1 - c.blue) * 0.12)


# ---------------------------------------------------------------- content -----
from report_content import PROJECTS  # noqa: E402


def main() -> None:
    for p in PROJECTS:
        build(p)
    print(f"\nGenerated {len(PROJECTS)} reports in {OUT}")


if __name__ == "__main__":
    main()
