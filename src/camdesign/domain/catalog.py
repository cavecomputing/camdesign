from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

# The catalog is hand-edited, so bound what a slip of the keyboard can push at the
# browser. These ceilings sit far above any real vendor lineup.
MAX_MAKES = 50
MAX_ROWS = 500
MAX_FIELD = 60
MAX_DETAIL = 120


def _cell(row: dict[str, Any], column: str, limit: int) -> str:
    value = row.get(column)
    return value.strip()[:limit] if isinstance(value, str) else ""


def _read(path: Path, key: str, columns: dict[str, int]) -> list[dict[str, str]]:
    # utf-8-sig so a file Excel saved with a byte-order mark still parses.
    with path.open(encoding="utf-8-sig", newline="") as handle:
        rows = []
        seen: set[str] = set()
        for row in csv.DictReader(handle):
            identifier = _cell(row, key, MAX_FIELD)
            if not identifier or identifier in seen:
                continue
            seen.add(identifier)
            rows.append(
                {key: identifier}
                | {column: _cell(row, column, limit) for column, limit in columns.items()}
            )
            if len(rows) >= MAX_ROWS:
                break
    return rows


def _brands(directory: Path) -> list[str]:
    if not directory.is_dir():
        return []
    return sorted(path.stem for path in directory.glob("*.csv") if path.is_file())


def load_catalog(catalog_dir: Path) -> list[dict[str, Any]]:
    """Read every brand's CSV into the shape the editor's dropdowns consume.

    Read on demand rather than cached, so hand-editing a CSV takes effect on the next
    page load instead of waiting for a restart.
    """
    cameras_dir = catalog_dir / "cameras"
    licenses_dir = catalog_dir / "licenses"

    makes = []
    for make in _brands(cameras_dir)[:MAX_MAKES]:
        models = _read(
            cameras_dir / f"{make}.csv",
            "model",
            {"series": MAX_FIELD, "type": MAX_FIELD, "resolution": MAX_FIELD, "fov": MAX_FIELD},
        )
        if not models:
            continue
        license_file = licenses_dir / f"{make}.csv"
        licenses = (
            _read(license_file, "sku", {"name": MAX_FIELD, "detail": MAX_DETAIL})
            if license_file.is_file()
            else []
        )
        makes.append({"make": make, "models": models, "licenses": licenses})
    return makes
