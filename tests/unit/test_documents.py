from __future__ import annotations

import pytest

from camdesign.domain.documents import (
    InvalidDocument,
    count_cameras,
    empty_document,
    validate_document,
)


def test_empty_document_is_valid():
    assert validate_document(empty_document()) == {"schema_version": 1, "items": []}


def test_camera_document_is_normalized():
    document = validate_document(
        {
            "schema_version": 1,
            "items": [
                {
                    "id": " camera-1 ",
                    "type": "camera",
                    "x": 0.25,
                    "y": 0.5,
                    "direction_degrees": -90,
                    "fov_degrees": 60,
                    "range": 0.2,
                    "label": " C01 ",
                }
            ],
        }
    )

    assert document["items"][0]["id"] == "camera-1"
    assert document["items"][0]["label"] == "C01"
    assert document["items"][0]["note"] == ""
    # Plans saved before equipment existed have no make/model/license and must still open.
    assert document["items"][0]["make"] == ""
    assert document["items"][0]["model"] == ""
    assert document["items"][0]["license"] == ""


def test_camera_equipment_is_kept():
    document = validate_document(
        {
            "schema_version": 1,
            "items": [
                {
                    "id": "camera-1",
                    "type": "camera",
                    "x": 0.25,
                    "y": 0.5,
                    "direction_degrees": -90,
                    "fov_degrees": 60,
                    "range": 0.2,
                    "make": "Hanwha",
                    "model": " XND-A9084RV ",
                    "license": "WAVE-PRO-01",
                }
            ],
        }
    )

    assert document["items"][0]["make"] == "Hanwha"
    assert document["items"][0]["model"] == "XND-A9084RV"
    assert document["items"][0]["license"] == "WAVE-PRO-01"


def test_overlong_equipment_is_rejected():
    camera = {
        "id": "camera-1",
        "type": "camera",
        "x": 0.25,
        "y": 0.5,
        "direction_degrees": 0,
        "fov_degrees": 60,
        "range": 0.2,
        "model": "X" * 61,
    }

    with pytest.raises(InvalidDocument, match="too long"):
        validate_document({"schema_version": 1, "items": [camera]})


@pytest.mark.parametrize(
    "field,value",
    [("x", -0.1), ("y", 1.1), ("fov_degrees", 200), ("range", 0)],
)
def test_camera_boundaries_are_enforced(field, value):
    camera = {
        "id": "camera-1",
        "type": "camera",
        "x": 0.25,
        "y": 0.5,
        "direction_degrees": 0,
        "fov_degrees": 60,
        "range": 0.2,
    }
    camera[field] = value

    with pytest.raises(InvalidDocument):
        validate_document({"schema_version": 1, "items": [camera]})


def test_duplicate_item_ids_are_rejected():
    camera = {
        "id": "duplicate",
        "type": "camera",
        "x": 0.25,
        "y": 0.5,
        "direction_degrees": 0,
        "fov_degrees": 60,
        "range": 0.2,
    }

    with pytest.raises(InvalidDocument, match="unique"):
        validate_document({"schema_version": 1, "items": [camera, camera]})


def test_count_cameras_flags_those_that_would_bill_as_not_specified():
    def camera(model: str) -> dict:
        return {"type": "camera", "model": model}

    document = {"schema_version": 1, "items": [camera("XND-A9084RV"), camera(""), camera("")]}

    assert count_cameras(document) == (3, 2)
    assert count_cameras(empty_document()) == (0, 0)
