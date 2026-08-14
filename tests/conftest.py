from __future__ import annotations

from pathlib import Path

import pytest

from camdesign import create_app


@pytest.fixture()
def app(tmp_path: Path):
    data_dir = tmp_path / "data"
    database = data_dir / "test.sqlite3"
    upload_dir = data_dir / "uploads"
    application = create_app(
        {
            "TESTING": True,
            "SECRET_KEY": "test-only-secret",
            "DATA_DIR": data_dir,
            "DATABASE": database,
            "UPLOAD_DIR": upload_dir,
        }
    )
    yield application


@pytest.fixture()
def client(app):
    return app.test_client()
