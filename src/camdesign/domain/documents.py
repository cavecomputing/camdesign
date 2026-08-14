from __future__ import annotations

from typing import Any

SCHEMA_VERSION = 1
MAX_ITEMS = 1_000


class InvalidDocument(ValueError):
    pass


def empty_document() -> dict[str, Any]:
    return {"schema_version": SCHEMA_VERSION, "items": []}


def _number(value: Any, name: str, minimum: float, maximum: float) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise InvalidDocument(f"{name} must be a number")
    number = float(value)
    if not minimum <= number <= maximum:
        raise InvalidDocument(f"{name} must be between {minimum} and {maximum}")
    return number


def _text(value: Any, name: str, maximum: int) -> str:
    if not isinstance(value, str):
        raise InvalidDocument(f"{name} must be text")
    if len(value) > maximum:
        raise InvalidDocument(f"{name} is too long")
    return value.strip()


def _validate_camera(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": _text(item.get("id"), "camera id", 64),
        "type": "camera",
        "x": _number(item.get("x"), "camera x", 0, 1),
        "y": _number(item.get("y"), "camera y", 0, 1),
        "direction_degrees": _number(item.get("direction_degrees"), "camera direction", -360, 360),
        "fov_degrees": _number(item.get("fov_degrees"), "camera field of view", 15, 180),
        "range": _number(item.get("range"), "camera range", 0.01, 2),
        "label": _text(item.get("label", ""), "camera label", 80),
        "note": _text(item.get("note", ""), "camera note", 1_000),
        # Equipment lives in hand-edited CSVs under catalog/, so these stay free text
        # rather than an enum: a plan drawn today must still open after a model is
        # renamed or retired there.
        "make": _text(item.get("make", ""), "camera make", 60),
        "model": _text(item.get("model", ""), "camera model", 60),
        "license": _text(item.get("license", ""), "camera license", 60),
    }


def validate_document(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise InvalidDocument("document must be an object")
    if value.get("schema_version") != SCHEMA_VERSION:
        raise InvalidDocument(f"schema_version must be {SCHEMA_VERSION}")
    items = value.get("items")
    if not isinstance(items, list):
        raise InvalidDocument("items must be an array")
    if len(items) > MAX_ITEMS:
        raise InvalidDocument(f"documents may contain at most {MAX_ITEMS} items")

    normalized: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for item in items:
        if not isinstance(item, dict):
            raise InvalidDocument("each item must be an object")
        if item.get("type") != "camera":
            raise InvalidDocument("only camera items are supported in this release")
        camera = _validate_camera(item)
        if not camera["id"] or camera["id"] in seen_ids:
            raise InvalidDocument("item ids must be non-empty and unique")
        seen_ids.add(camera["id"])
        normalized.append(camera)

    return {"schema_version": SCHEMA_VERSION, "items": normalized}
