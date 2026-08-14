from __future__ import annotations

from flask import abort, current_app, jsonify, request

from camdesign.blueprints.api import api
from camdesign.db import get_db
from camdesign.domain.catalog import load_catalog
from camdesign.domain.documents import InvalidDocument, validate_document
from camdesign.repositories.projects import SQLiteProjectRepository


@api.get("/catalog")
def equipment_catalog():
    return jsonify(makes=load_catalog(current_app.config["CATALOG_DIR"]))


@api.get("/projects/<uuid:project_id>/document")
def project_document(project_id):
    project = SQLiteProjectRepository(get_db()).get(str(project_id))
    if project is None:
        abort(404)
    return jsonify(
        project={
            "id": project.id,
            "name": project.name,
            "client_name": project.client_name,
            "site_address": project.site_address,
            "notes": project.notes,
        },
        document=project.document,
        revision=project.revision,
    )


@api.patch("/projects/<uuid:project_id>/document")
def update_project_document(project_id):
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        abort(400, description="Expected a JSON object")
    revision = payload.get("revision")
    if isinstance(revision, bool) or not isinstance(revision, int) or revision < 1:
        abort(400, description="revision must be a positive integer")
    notes = payload.get("notes", "")
    if not isinstance(notes, str) or len(notes) > 5_000:
        abort(400, description="notes must be at most 5000 characters")
    try:
        document = validate_document(payload.get("document"))
    except InvalidDocument as error:
        abort(400, description=str(error))

    repository = SQLiteProjectRepository(get_db())
    existing = repository.get(str(project_id))
    if existing is None:
        abort(404)
    updated = repository.update_document(
        str(project_id),
        expected_revision=revision,
        document=document,
        notes=notes.strip(),
    )
    if updated is None:
        current = repository.get(str(project_id))
        return (
            jsonify(
                error={
                    "code": "Revision conflict",
                    "message": "This project changed elsewhere. Reload before saving again.",
                },
                revision=current.revision if current else None,
            ),
            409,
        )
    return jsonify(revision=updated.revision, saved_at=updated.updated_at)
