from __future__ import annotations

from typing import Any

from camdesign.domain.bom import build_bom

CATALOG = [
    {
        "make": "Hanwha",
        "models": [
            {
                "model": "XND-A9084RV",
                "series": "X series AI",
                "type": "Dome",
                "resolution": "8MP",
                "fov": "113°-47°",
            }
        ],
        "licenses": [
            {"sku": "WAVE-PRO-01", "name": "WAVE Professional 1ch", "detail": "1 recording channel"}
        ],
    }
]


def camera(label: str, **overrides: Any) -> dict[str, Any]:
    return {
        "id": label,
        "type": "camera",
        "x": 0.5,
        "y": 0.5,
        "direction_degrees": -90,
        "fov_degrees": 90,
        "range": 0.16,
        "label": label,
        "note": "",
        "make": "Hanwha",
        "model": "XND-A9084RV",
        "license": "",
    } | overrides


def document(*items: dict[str, Any]) -> dict[str, Any]:
    return {"schema_version": 1, "items": list(items)}


def test_identical_cameras_become_one_counted_line():
    bom = build_bom(document(camera("C01"), camera("C02")), CATALOG)

    [section] = bom.sections
    [line] = section.lines
    assert section.title == "Cameras"
    assert (line.manufacturer, line.part, line.quantity) == ("Hanwha", "XND-A9084RV", 2)
    # The same spec line the estimator picked the model from in the editor.
    assert line.description == "8MP · 113°-47° · Dome"


def test_licenses_are_their_own_section_not_another_camera_line():
    bom = build_bom(
        document(
            camera("C01", license="WAVE-PRO-01"),
            camera("C02", license="WAVE-PRO-01"),
            camera("C03"),
        ),
        CATALOG,
    )

    cameras, licenses = bom.sections
    assert cameras.title == "Cameras"
    assert cameras.quantity == 3
    assert licenses.title == "Licenses"
    [line] = licenses.lines
    # Only the two cameras that carry one, not the whole camera count.
    assert (line.part, line.quantity, line.reference) == ("WAVE-PRO-01", 2, "C01, C02")
    assert line.description == "WAVE Professional 1ch · 1 recording channel"


def test_a_plan_with_no_licenses_has_no_license_section():
    bom = build_bom(document(camera("C01")), CATALOG)

    assert [section.title for section in bom.sections] == ["Cameras"]


def test_an_empty_plan_reports_nothing_to_bill():
    assert build_bom(document(), CATALOG).is_empty


def test_camera_notes_are_included_in_natural_label_order_and_empty_notes_are_omitted():
    bom = build_bom(
        document(
            camera("C10", note="Watch the loading bay."),
            camera("C02", note=""),
            camera("C01", note="Mount below the soffit."),
            camera("", note="Confirm the final position."),
        ),
        CATALOG,
    )

    assert [(note.label, note.text) for note in bom.camera_notes] == [
        ("C01", "Mount below the soffit."),
        ("C10", "Watch the loading bay."),
        ("Camera 4", "Confirm the final position."),
    ]


def test_reference_collapses_runs_but_keeps_the_gaps():
    labels = ["C01", "C02", "C04", "C05", "C06", "C07", "C09"]
    bom = build_bom(document(*(camera(label) for label in labels)), CATALOG)

    [line] = bom.sections[0].lines
    # A pair is spelled out; three or more earns the dash.
    assert line.reference == "C01, C02, C04–C07, C09"


def test_reference_orders_names_the_way_they_read():
    bom = build_bom(
        document(camera("C10"), camera("C9"), camera("Loading bay")),
        CATALOG,
    )

    [line] = bom.sections[0].lines
    # C9 before C10, and the differing digit width keeps them out of one run.
    assert line.reference == "C9, C10, Loading bay"


def test_equipment_not_yet_chosen_still_bills_and_sinks_to_the_bottom():
    bom = build_bom(
        document(
            camera("C01", make="", model=""),
            camera("C02"),
            camera("C03", model="XNO-RETIRED"),
        ),
        CATALOG,
    )

    [section] = bom.sections
    assert section.quantity == 3
    assert [(line.manufacturer, line.part) for line in section.lines] == [
        ("Hanwha", "XND-A9084RV"),
        ("Hanwha", "XNO-RETIRED"),
        ("Not specified", "Not specified"),
    ]
    # A model dropped from the catalog since the plan was drawn still bills; it just
    # prints without a spec rather than vanishing from the quote.
    assert section.lines[1].description == ""
