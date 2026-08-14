from __future__ import annotations

import os
import shutil
import sqlite3
import uuid
from pathlib import Path
from typing import BinaryIO

from werkzeug.datastructures import FileStorage

from camdesign.domain.documents import empty_document
from camdesign.repositories.projects import Project, SQLiteProjectRepository

ALLOWED_IMAGES = {
    "image/jpeg": (".jpg", (b"\xff\xd8\xff",)),
    "image/png": (".png", (b"\x89PNG\r\n\x1a\n",)),
    "image/webp": (".webp", (b"RIFF",)),
}


class InvalidProject(ValueError):
    pass


def _clean_text(value: str | None, field: str, maximum: int, *, required: bool = False) -> str:
    cleaned = (value or "").strip()
    if required and not cleaned:
        raise InvalidProject(f"{field} is required")
    if len(cleaned) > maximum:
        raise InvalidProject(f"{field} is too long")
    return cleaned


def _detect_image(stream: BinaryIO) -> tuple[str, str]:
    header = stream.read(16)
    stream.seek(0)
    if header.startswith(ALLOWED_IMAGES["image/png"][1][0]):
        return "image/png", ".png"
    if header.startswith(ALLOWED_IMAGES["image/jpeg"][1][0]):
        return "image/jpeg", ".jpg"
    if header.startswith(b"RIFF") and header[8:12] == b"WEBP":
        return "image/webp", ".webp"
    raise InvalidProject("Upload a PNG, JPEG, or WebP image")


def create_project(
    repository: SQLiteProjectRepository,
    upload_root: Path,
    *,
    name: str | None,
    client_name: str | None,
    site_address: str | None,
    notes: str | None,
    image: FileStorage | None,
) -> Project:
    project_name = _clean_text(name, "Project name", 120, required=True)
    client = _clean_text(client_name, "Client name", 120)
    address = _clean_text(site_address, "Site address", 240)
    project_notes = _clean_text(notes, "Notes", 5_000)
    if image is None or not image.filename:
        raise InvalidProject("A site image is required")

    mime, extension = _detect_image(image.stream)
    project_id = str(uuid.uuid4())
    project_upload_dir = upload_root / project_id
    project_upload_dir.mkdir(parents=True, exist_ok=False)
    final_path = project_upload_dir / f"base-map{extension}"
    temporary_path = project_upload_dir / ".uploading"

    try:
        image.save(temporary_path)
        os.replace(temporary_path, final_path)
        relative_path = final_path.relative_to(upload_root.parent).as_posix()
        return repository.create(
            project_id=project_id,
            name=project_name,
            client_name=client,
            site_address=address,
            notes=project_notes,
            image_path=relative_path,
            image_original_name=Path(image.filename).name[:255],
            image_mime=mime,
            document=empty_document(),
        )
    except (OSError, sqlite3.Error):
        shutil.rmtree(project_upload_dir, ignore_errors=True)
        raise


def delete_project(
    repository: SQLiteProjectRepository,
    upload_root: Path,
    project_id: str,
) -> Project | None:
    project = repository.get(project_id)
    if project is None:
        return None

    project_upload_dir = (upload_root.parent / project.image_path).resolve().parent
    expected_upload_dir = (upload_root / project.id).resolve()
    if project_upload_dir != expected_upload_dir:
        raise RuntimeError("project asset path is outside its upload directory")

    if not repository.delete(project_id):
        return None
    shutil.rmtree(project_upload_dir, ignore_errors=True)
    return project
