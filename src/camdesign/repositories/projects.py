from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class Project:
    id: str
    name: str
    client_name: str
    site_address: str
    notes: str
    image_path: str
    image_original_name: str
    image_mime: str
    document: dict[str, Any]
    revision: int
    created_at: str
    updated_at: str


def _project_from_row(row: sqlite3.Row) -> Project:
    return Project(
        id=row["id"],
        name=row["name"],
        client_name=row["client_name"],
        site_address=row["site_address"],
        notes=row["notes"],
        image_path=row["image_path"],
        image_original_name=row["image_original_name"],
        image_mime=row["image_mime"],
        document=json.loads(row["document_json"]),
        revision=row["revision"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


class SQLiteProjectRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    def list_recent(self, limit: int = 50) -> list[Project]:
        rows = self.connection.execute(
            "SELECT * FROM projects ORDER BY updated_at DESC, id DESC LIMIT ?", (limit,)
        ).fetchall()
        return [_project_from_row(row) for row in rows]

    def get(self, project_id: str) -> Project | None:
        row = self.connection.execute(
            "SELECT * FROM projects WHERE id = ?", (project_id,)
        ).fetchone()
        return _project_from_row(row) if row else None

    def delete(self, project_id: str) -> bool:
        cursor = self.connection.execute("DELETE FROM projects WHERE id = ?", (project_id,))
        self.connection.commit()
        return cursor.rowcount == 1

    def create(
        self,
        *,
        project_id: str,
        name: str,
        client_name: str,
        site_address: str,
        notes: str,
        image_path: str,
        image_original_name: str,
        image_mime: str,
        document: dict[str, Any],
    ) -> Project:
        self.connection.execute(
            """
            INSERT INTO projects (
                id, name, client_name, site_address, notes, image_path,
                image_original_name, image_mime, document_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                project_id,
                name,
                client_name,
                site_address,
                notes,
                image_path,
                image_original_name,
                image_mime,
                json.dumps(document, separators=(",", ":")),
            ),
        )
        self.connection.commit()
        project = self.get(project_id)
        if project is None:
            raise RuntimeError("project was not persisted")
        return project

    def update_document(
        self,
        project_id: str,
        *,
        expected_revision: int,
        document: dict[str, Any],
        notes: str,
    ) -> Project | None:
        cursor = self.connection.execute(
            """
            UPDATE projects
            SET document_json = ?, notes = ?, revision = revision + 1,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ? AND revision = ?
            """,
            (
                json.dumps(document, separators=(",", ":")),
                notes,
                project_id,
                expected_revision,
            ),
        )
        self.connection.commit()
        return self.get(project_id) if cursor.rowcount == 1 else None
