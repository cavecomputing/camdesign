from __future__ import annotations

from pathlib import Path

from camdesign.config import Config
from camdesign.domain.catalog import load_catalog


def write_catalog(root: Path, cameras: str, licenses: str | None = None) -> Path:
    (root / "cameras").mkdir(parents=True)
    (root / "cameras" / "Hanwha.csv").write_text(cameras, encoding="utf-8")
    if licenses is not None:
        (root / "licenses").mkdir(parents=True)
        (root / "licenses" / "Hanwha.csv").write_text(licenses, encoding="utf-8")
    return root


def test_brand_is_read_from_the_file_name(tmp_path: Path):
    write_catalog(
        tmp_path,
        "model,series,type,resolution,fov\nXND-A9084RV,X series AI,Dome,8MP,113°-47°\n",
        "sku,name,detail\nWAVE-PRO-01,WAVE Professional 1ch,1 recording channel\n",
    )

    [brand] = load_catalog(tmp_path)

    assert brand["make"] == "Hanwha"
    assert brand["models"] == [
        {
            "model": "XND-A9084RV",
            "series": "X series AI",
            "type": "Dome",
            "resolution": "8MP",
            "fov": "113°-47°",
        }
    ]
    assert brand["licenses"] == [
        {"sku": "WAVE-PRO-01", "name": "WAVE Professional 1ch", "detail": "1 recording channel"}
    ]


def test_a_brand_without_licenses_still_loads(tmp_path: Path):
    write_catalog(tmp_path, "model\nXNO-A9084R\n")

    [brand] = load_catalog(tmp_path)

    assert brand["licenses"] == []
    # Absent columns are blank rather than missing, so the browser never sees undefined.
    assert brand["models"] == [
        {"model": "XNO-A9084R", "series": "", "type": "", "resolution": "", "fov": ""}
    ]


def test_hand_editing_slips_are_skipped_not_fatal(tmp_path: Path):
    write_catalog(
        tmp_path,
        "model,type\n  XNO-A9084R  ,Bullet\n,Dome\nXNO-A9084R,Bullet\nXNV-A9084R,Vandal dome\n",
    )

    [brand] = load_catalog(tmp_path)

    # Trimmed, the blank row dropped, and the repeat of an earlier model ignored.
    assert [model["model"] for model in brand["models"]] == ["XNO-A9084R", "XNV-A9084R"]


def test_missing_catalog_directory_is_empty(tmp_path: Path):
    assert load_catalog(tmp_path / "absent") == []


def test_shipped_catalog_parses():
    # The CSVs are meant to be hand-edited, so a typo that empties a brand or leaves a
    # model without its spec line should fail here rather than on a job.
    brands = {brand["make"]: brand for brand in load_catalog(Config.CATALOG_DIR)}

    assert set(brands) == {"Generic", "Hanwha", "UniFi"}
    for make in ("Hanwha", "UniFi"):
        brand = brands[make]
        assert len(brand["models"]) > 20
        assert all(
            model["fov"] and model["resolution"] and model["type"] and model["series"]
            for model in brand["models"]
        )

    # Hanwha sells the VMS licenses separately; UniFi Protect bundles recording with the
    # console, so it has no license file and gets no License dropdown.
    assert any(license["sku"].startswith("WAVE-PRO-") for license in brands["Hanwha"]["licenses"])
    assert brands["UniFi"]["licenses"] == []
    assert brands["Generic"] == {
        "make": "Generic",
        "models": [
            {
                "model": "Generic camera",
                "series": "Placeholder",
                "type": "Camera",
                "resolution": "Not specified",
                "fov": "Not specified",
            }
        ],
        "licenses": [],
    }
