from __future__ import annotations

import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATA_DIR = PROJECT_ROOT / "data"


class Config:
    DATA_DIR = Path(os.environ.get("CAMDESIGN_DATA_DIR", DEFAULT_DATA_DIR)).resolve()
    # Committed reference data, not user data, so it lives beside the code rather than
    # under DATA_DIR. See catalog/README.md for the file layout.
    CATALOG_DIR = Path(os.environ.get("CAMDESIGN_CATALOG_DIR", PROJECT_ROOT / "catalog")).resolve()
    DATABASE = DATA_DIR / "camdesign.sqlite3"
    UPLOAD_DIR = DATA_DIR / "uploads"
    SECRET_KEY = os.environ.get("CAMDESIGN_SECRET_KEY")
    MAX_CONTENT_LENGTH = 20 * 1024 * 1024
    MAX_FORM_MEMORY_SIZE = 512 * 1024
    MAX_FORM_PARTS = 20
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
