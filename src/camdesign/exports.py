"""Render a saved plan's bill of materials as a PDF.

Built from the stored document rather than from anything on screen, so the same plan
exports the same bytes from any browser, or from none.
"""

from __future__ import annotations

import re
from datetime import date
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from camdesign.domain.bom import Bom
from camdesign.repositories.projects import Project

INK = colors.HexColor("#0c2148")
INK_MUTED = colors.HexColor("#49607c")
LINE = colors.HexColor("#d3cec5")
BAND = colors.HexColor("#e8f1ff")
STRIPE = colors.HexColor("#f7f5f1")

MARGIN = 0.6 * inch
# LINE, MANUFACTURER, MODEL / SKU, DESCRIPTION, QTY, CAMERAS — 525pt across a letter page.
COLUMNS = (28, 78, 105, 155, 30, 129)
COLUMN_HEADINGS = ("#", "MANUFACTURER", "MODEL / SKU", "DESCRIPTION", "QTY", "CAMERAS")

_TITLE = ParagraphStyle("title", fontName="Helvetica-Bold", fontSize=17, textColor=INK, leading=20)
_META = ParagraphStyle("meta", fontName="Helvetica", fontSize=9, textColor=INK_MUTED, leading=13)
_HEAD = ParagraphStyle(
    "head", fontName="Helvetica-Bold", fontSize=7, textColor=colors.white, leading=9
)
_HEAD_NUMBER = ParagraphStyle("head-number", parent=_HEAD, alignment=TA_RIGHT)
_BAND = ParagraphStyle("band", fontName="Helvetica-Bold", fontSize=8.5, textColor=INK, leading=11)
_CELL = ParagraphStyle("cell", fontName="Helvetica", fontSize=8, textColor=INK, leading=10.5)
_STRONG = ParagraphStyle("strong", parent=_CELL, fontName="Helvetica-Bold")
_MUTED = ParagraphStyle("muted", parent=_CELL, textColor=INK_MUTED)
_NUMBER = ParagraphStyle("number", parent=_STRONG, alignment=TA_RIGHT)
_FOOT = ParagraphStyle("foot", fontName="Helvetica", fontSize=8, textColor=INK_MUTED, leading=12)


def bom_filename(project_name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", project_name.lower()).strip("-")
    return f"{slug or 'plan'}-bom.pdf"


def _cell(text: str, style: ParagraphStyle) -> Paragraph:
    # Every value here is user- or catalog-supplied, and a stray & or < is a hard parse
    # error inside a Paragraph's mini-markup rather than a stray character on the page.
    escaped = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return Paragraph(escaped, style)


def _page_furniture(canvas, document) -> None:
    canvas.saveState()
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(INK_MUTED)
    canvas.drawRightString(LETTER[0] - MARGIN, MARGIN - 22, f"Page {canvas.getPageNumber()}")
    canvas.drawString(MARGIN, MARGIN - 22, "Quantities are drawn from the marked-up plan.")
    canvas.restoreState()


def _heading(project: Project, generated_on: date) -> list:
    rows = [
        (label, value)
        for label, value in (
            ("Customer", project.client_name),
            ("Site", project.site_address),
            ("Project", project.name),
            ("Generated", generated_on.strftime("%d %B %Y")),
        )
        if value
    ]
    meta = Table(
        [[_cell(label, _META), _cell(value, _META)] for label, value in rows],
        colWidths=(60, sum(COLUMNS) - 60),
        style=TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 1),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
            ]
        ),
    )
    return [
        Paragraph("Bill of materials", _TITLE),
        Spacer(1, 8),
        meta,
        Spacer(1, 14),
    ]


def _table(bom: Bom) -> Table:
    # QTY's heading is right-aligned like the numbers it sits over.
    headings = [_cell(text, _HEAD_NUMBER if text == "QTY" else _HEAD) for text in COLUMN_HEADINGS]
    rows: list[list] = [headings]
    style = [
        ("BACKGROUND", (0, 0), (-1, 0), INK),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("LINEBELOW", (0, 1), (-1, -1), 0.4, LINE),
    ]

    number = 0
    for section in bom.sections:
        # A full-width band rather than one more column of "Camera", so the eye can find
        # where the licenses start without reading every row.
        band = len(rows)
        rows.append([_cell(section.title.upper(), _BAND), "", "", "", "", ""])
        style += [
            ("SPAN", (0, band), (-1, band)),
            ("BACKGROUND", (0, band), (-1, band), BAND),
            ("TOPPADDING", (0, band), (-1, band), 7),
            ("LINEBELOW", (0, band), (-1, band), 0, colors.white),
        ]
        for line in section.lines:
            number += 1
            index = len(rows)
            # Striped by line number rather than row position, so a section band in
            # between cannot land two shaded rows against each other.
            if not number % 2:
                style.append(("BACKGROUND", (0, index), (-1, index), STRIPE))
            rows.append(
                [
                    _cell(str(number), _MUTED),
                    _cell(line.manufacturer, _CELL),
                    _cell(line.part, _STRONG),
                    _cell(line.description, _MUTED),
                    _cell(str(line.quantity), _NUMBER),
                    _cell(line.reference, _MUTED),
                ]
            )

    return Table(rows, colWidths=COLUMNS, repeatRows=1, style=TableStyle(style))


def _totals(bom: Bom) -> list:
    counts = ", ".join(f"{section.quantity} {section.title.lower()}" for section in bom.sections)
    return [
        Spacer(1, 10),
        Paragraph(f"Total: {counts}.", _FOOT),
        Spacer(1, 4),
        Paragraph(
            "Confirm model availability, mounting accessories and cable quantities "
            "before ordering.",
            _FOOT,
        ),
    ]


def render_bom_pdf(project: Project, bom: Bom, generated_on: date) -> bytes:
    buffer = BytesIO()
    document = SimpleDocTemplate(
        buffer,
        pagesize=LETTER,
        leftMargin=MARGIN,
        rightMargin=MARGIN,
        topMargin=MARGIN,
        bottomMargin=MARGIN,
        title=f"{project.name} — Bill of materials",
        author="CamDesign",
    )
    story = _heading(project, generated_on)
    if bom.is_empty:
        # An honest empty page beats a table of nothing: the plan genuinely has no
        # equipment on it yet, and saying so is the useful answer.
        story.append(
            Paragraph("No cameras have been placed on this plan yet.", _META),
        )
    else:
        story.append(_table(bom))
        # The totals belong on the same page as the last line they add up.
        story.append(KeepTogether(_totals(bom)))
    document.build(story, onFirstPage=_page_furniture, onLaterPages=_page_furniture)
    return buffer.getvalue()
