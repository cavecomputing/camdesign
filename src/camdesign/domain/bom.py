"""Roll a saved plan up into the ordered, grouped lines a bill of materials prints.

Kept free of Flask and of the PDF library so the grouping can be tested on its own, and
so a second export format later renders the same numbers rather than recounting them.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

NOT_SPECIFIED = "Not specified"
# Below this, spelling the names out is shorter than a range and easier to scan.
MIN_RUN = 3

# A trailing number is what makes a name part of a run: C01, C02, Door 3.
_NUMBERED = re.compile(r"^(.*?)(\d+)$")


@dataclass(frozen=True, slots=True)
class BomLine:
    manufacturer: str
    part: str
    description: str
    quantity: int
    # The names of the cameras this line covers, as they read on the plan.
    reference: str


@dataclass(frozen=True, slots=True)
class BomSection:
    title: str
    lines: tuple[BomLine, ...]

    @property
    def quantity(self) -> int:
        return sum(line.quantity for line in self.lines)


@dataclass(frozen=True, slots=True)
class BomCameraNote:
    label: str
    text: str


@dataclass(frozen=True, slots=True)
class Bom:
    sections: tuple[BomSection, ...]
    camera_notes: tuple[BomCameraNote, ...] = ()

    @property
    def is_empty(self) -> bool:
        return not self.sections


def _sort_key(label: str) -> tuple[int, str, int, str]:
    """Order names the way a person reads them, so C9 lands before C10."""
    match = _NUMBERED.match(label)
    if match:
        return (0, match.group(1).lower(), int(match.group(2)), label)
    return (1, label.lower(), 0, label)


def _follows(previous: str, current: str) -> bool:
    before = _NUMBERED.match(previous)
    after = _NUMBERED.match(current)
    if not before or not after:
        return False
    # Same prefix and the same digit width: C09 → C10 continues a run, C09 → C9 does not.
    return (
        before.group(1) == after.group(1)
        and len(before.group(2)) == len(after.group(2))
        and int(before.group(2)) + 1 == int(after.group(2))
    )


def _reference(labels: list[str]) -> str:
    """Collapse a line's camera names into runs: C01, C02, C04–C07."""
    named = sorted({label for label in labels if label}, key=_sort_key)
    if not named:
        return ""
    parts: list[str] = []
    run = [named[0]]
    for label in named[1:]:
        if _follows(run[-1], label):
            run.append(label)
            continue
        # A run too short to be worth a dash is spelled out rather than dropped.
        parts.extend(run if len(run) < MIN_RUN else [f"{run[0]}–{run[-1]}"])
        run = [label]
    parts.extend(run if len(run) < MIN_RUN else [f"{run[0]}–{run[-1]}"])
    return ", ".join(parts)


def _catalog_index(makes: list[dict[str, Any]]) -> tuple[dict, dict]:
    models: dict[tuple[str, str], str] = {}
    licenses: dict[tuple[str, str], str] = {}
    for brand in makes:
        make = brand["make"]
        for model in brand["models"]:
            # The same spec line the editor's Model dropdown shows, so the quote and the
            # screen it was picked on describe the camera identically.
            models[(make, model["model"])] = " · ".join(
                value for value in (model["resolution"], model["fov"], model["type"]) if value
            )
        for entry in brand["licenses"]:
            licenses[(make, entry["sku"])] = " · ".join(
                value for value in (entry["name"], entry["detail"]) if value
            )
    return models, licenses


def _lines(groups: dict[tuple[str, str], list[str]], descriptions: dict) -> tuple[BomLine, ...]:
    def order(key: tuple[str, str]) -> tuple[int, str, str]:
        make, part = key
        # Equipment nobody has chosen yet sinks to the bottom of its section, where it
        # reads as the outstanding decision it is rather than as a supplier called "N".
        return (0 if make else 1, make.lower(), part.lower())

    return tuple(
        BomLine(
            manufacturer=make or NOT_SPECIFIED,
            part=part or NOT_SPECIFIED,
            description=descriptions.get((make, part), ""),
            quantity=len(labels),
            reference=_reference(labels),
        )
        for (make, part), labels in sorted(groups.items(), key=lambda item: order(item[0]))
    )


def build_bom(document: dict[str, Any], makes: list[dict[str, Any]]) -> Bom:
    """Group a plan's cameras and their licenses into printable sections.

    `makes` is `load_catalog`'s output, used only to describe a part. A model that has
    since been dropped from the catalog still bills; it just prints without its spec.
    """
    models, licenses = _catalog_index(makes)
    cameras: dict[tuple[str, str], list[str]] = {}
    licensing: dict[tuple[str, str], list[str]] = {}
    camera_notes: list[BomCameraNote] = []
    camera_number = 0

    for item in document.get("items", []):
        if item.get("type") != "camera":
            continue
        camera_number += 1
        make = item.get("make", "")
        label = item.get("label", "")
        cameras.setdefault((make, item.get("model", "")), []).append(label)
        if item.get("license"):
            licensing.setdefault((make, item["license"]), []).append(label)
        if item.get("note"):
            camera_notes.append(
                BomCameraNote(
                    label=label or f"Camera {camera_number}",
                    text=item["note"],
                )
            )

    sections = [
        BomSection(title=title, lines=_lines(groups, descriptions))
        for title, groups, descriptions in (
            ("Cameras", cameras, models),
            ("Licenses", licensing, licenses),
        )
        if groups
    ]
    return Bom(
        sections=tuple(sections),
        camera_notes=tuple(sorted(camera_notes, key=lambda note: _sort_key(note.label))),
    )
