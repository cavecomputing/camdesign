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

# The editor's palette (static/css/tokens.css): brand-ink, ink-2, line, brand-soft, bg,
# raised and brand.
INK = colors.HexColor("#0b1f3a")
INK_MUTED = colors.HexColor("#475569")
LINE = colors.HexColor("#e2e8f0")
BAND = colors.HexColor("#e9f0f9")
STRIPE = colors.HexColor("#f4f7fb")
RAISED = colors.HexColor("#f7f9fc")
BRAND = colors.HexColor("#1d4e89")

MARGIN = 0.6 * inch
# LINE, MANUFACTURER, MODEL / SKU, DESCRIPTION, QTY, CAMERAS — 525pt across a letter page.
COLUMNS = (28, 78, 105, 155, 30, 129)
COLUMN_HEADINGS = ("#", "MANUFACTURER", "MODEL / SKU", "DESCRIPTION", "QTY", "CAMERAS")

_KIND = ParagraphStyle(
    "kind", fontName="Helvetica-Bold", fontSize=7, textColor=INK_MUTED, leading=9
)
_TITLE = ParagraphStyle("title", fontName="Helvetica-Bold", fontSize=19, textColor=INK, leading=23)
_SUBTITLE = ParagraphStyle(
    "subtitle", fontName="Helvetica", fontSize=10, textColor=INK_MUTED, leading=13
)
_META_LABEL = ParagraphStyle(
    "meta-label", fontName="Helvetica-Bold", fontSize=6.5, textColor=INK_MUTED, leading=9
)
_META_VALUE = ParagraphStyle(
    "meta-value", fontName="Helvetica-Bold", fontSize=9, textColor=INK, leading=12
)
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
_SECTION = ParagraphStyle(
    "section", fontName="Helvetica-Bold", fontSize=11, textColor=INK, leading=14
)
_NOTE_LABEL = ParagraphStyle(
    "note-label", fontName="Helvetica-Bold", fontSize=8.5, textColor=INK, leading=11
)
_NOTE = ParagraphStyle("note", fontName="Helvetica", fontSize=8.5, textColor=INK, leading=12)


def bom_filename(project_name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", project_name.lower()).strip("-")
    return f"{slug or 'plan'}-bom.pdf"


def _cell(text: str, style: ParagraphStyle) -> Paragraph:
    # Every value here is user- or catalog-supplied, and a stray & or < is a hard parse
    # error inside a Paragraph's mini-markup rather than a stray character on the page.
    escaped = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    escaped = "<br/>".join(escaped.splitlines())
    return Paragraph(escaped, style)


def _page_furniture(canvas, document) -> None:
    canvas.saveState()
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(INK_MUTED)
    canvas.drawRightString(LETTER[0] - MARGIN, MARGIN - 22, f"Page {canvas.getPageNumber()}")
    canvas.drawString(MARGIN, MARGIN - 22, "Quantities are drawn from the marked-up plan.")
    canvas.restoreState()


def _heading(project: Project, generated_on: date) -> list:
    # The document header the editor's cards share: a raised panel under a brand rule,
    # saying what kind of document this is before naming the project it is for.
    meta = [
        (label, value)
        for label, value in (
            ("CUSTOMER", project.client_name),
            ("SITE", project.site_address),
            ("GENERATED", generated_on.strftime("%d %B %Y")),
        )
        if value
    ]
    meta_table = Table(
        [
            [_cell(label, _META_LABEL) for label, _ in meta],
            [_cell(value, _META_VALUE) for _, value in meta],
        ],
        colWidths=[150] * len(meta),
        hAlign="LEFT",
        style=TableStyle(
            [
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 12),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
            ]
        ),
    )
    subtitle = " · ".join(value for value in (project.client_name, project.site_address) if value)
    rows = [[_cell("BILL OF MATERIALS", _KIND)], [_cell(project.name, _TITLE)]]
    if subtitle:
        rows.append([_cell(subtitle, _SUBTITLE)])
    rows.append([meta_table])
    last = len(rows) - 1
    panel = Table(
        rows,
        colWidths=(sum(COLUMNS),),
        style=TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), RAISED),
                ("BOX", (0, 0), (-1, -1), 0.5, LINE),
                ("LINEABOVE", (0, 0), (-1, 0), 3, BRAND),
                ("LEFTPADDING", (0, 0), (-1, -1), 16),
                ("RIGHTPADDING", (0, 0), (-1, -1), 16),
                ("TOPPADDING", (0, 0), (-1, -1), 2),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                ("TOPPADDING", (0, 0), (-1, 0), 12),
                ("TOPPADDING", (0, 1), (-1, 1), 8),
                ("LINEABOVE", (0, last), (-1, last), 0.5, LINE),
                ("TOPPADDING", (0, last), (-1, last), 9),
                ("BOTTOMPADDING", (0, last), (-1, last), 11),
            ]
        ),
    )
    return [panel, Spacer(1, 16)]


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


def _notes(project: Project, bom: Bom) -> list:
    if not project.notes and not bom.camera_notes:
        return []

    story = [Spacer(1, 18), Paragraph("Notes", _SECTION), Spacer(1, 7)]
    if project.notes:
        story += [
            Paragraph("Project notes", _NOTE_LABEL),
            Spacer(1, 2),
            _cell(project.notes, _NOTE),
        ]
    if bom.camera_notes:
        if project.notes:
            story.append(Spacer(1, 10))
        story += [Paragraph("Camera notes", _NOTE_LABEL), Spacer(1, 3)]
        for note in bom.camera_notes:
            story.append(
                KeepTogether(
                    [
                        _cell(note.label, _NOTE_LABEL),
                        Spacer(1, 1),
                        _cell(note.text, _NOTE),
                        Spacer(1, 6),
                    ]
                )
            )
    return story


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
    story.extend(_notes(project, bom))
    document.build(story, onFirstPage=_page_furniture, onLaterPages=_page_furniture)
    return buffer.getvalue()
