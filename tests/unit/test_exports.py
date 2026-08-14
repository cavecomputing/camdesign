from __future__ import annotations

from types import SimpleNamespace

from reportlab.platypus import KeepTogether, Paragraph

from camdesign.domain.bom import Bom, BomCameraNote
from camdesign.exports import _notes


def _paragraphs(flowables: list) -> list[Paragraph]:
    paragraphs: list[Paragraph] = []
    for flowable in flowables:
        if isinstance(flowable, Paragraph):
            paragraphs.append(flowable)
        elif isinstance(flowable, KeepTogether):
            paragraphs.extend(_paragraphs(flowable._content))
    return paragraphs


def test_notes_section_contains_project_and_camera_notes_with_safe_line_breaks():
    project = SimpleNamespace(notes="Confirm roof access.\nBring a lift & spotter.")
    bom = Bom(
        sections=(),
        camera_notes=(BomCameraNote(label="C01", text="Mount below <awning>."),),
    )

    paragraphs = _paragraphs(_notes(project, bom))

    assert [paragraph.getPlainText() for paragraph in paragraphs] == [
        "Notes",
        "Project notes",
        "Confirm roof access.Bring a lift & spotter.",
        "Camera notes",
        "C01",
        "Mount below <awning>.",
    ]
    assert paragraphs[2].text == "Confirm roof access.<br/>Bring a lift &amp; spotter."


def test_notes_section_is_omitted_when_all_notes_are_empty():
    assert _notes(SimpleNamespace(notes=""), Bom(sections=())) == []
