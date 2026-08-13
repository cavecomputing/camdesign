from __future__ import annotations

import io
import re

PNG_HEADER = b"\x89PNG\r\n\x1a\n" + (b"\x00" * 32)


def csrf_token(client) -> str:
    with client.session_transaction() as session:
        return session["_csrf_token"]


def create_project(client):
    client.get("/projects/new")
    return client.post(
        "/projects",
        data={
            "csrf_token": csrf_token(client),
            "name": "Oak & Main Market",
            "client_name": "Oak Markets",
            "site_address": "123 Main Street",
            "notes": "Check roof access.",
            "site_image": (io.BytesIO(PNG_HEADER), "site.png"),
        },
        content_type="multipart/form-data",
    )


def project_id_from_redirect(response) -> str:
    match = re.search(r"/projects/([0-9a-f-]+)/editor", response.location)
    assert match
    return match.group(1)


def test_empty_dashboard_and_security_headers(client):
    response = client.get("/")

    assert response.status_code == 200
    assert b"Create your first project" in response.data
    assert b"/static/images/camdesign-logo.png" in response.data
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert "default-src 'self'" in response.headers["Content-Security-Policy"]

    logo = client.get("/static/images/camdesign-logo.png")
    assert logo.status_code == 200
    assert logo.mimetype == "image/png"


def test_create_resume_and_serve_project_asset(client):
    response = create_project(client)

    assert response.status_code == 302
    project_id = project_id_from_redirect(response)

    editor = client.get(response.location)
    assert editor.status_code == 200
    assert b"Oak &amp; Main Market" in editor.data
    assert b"Project notes" in editor.data

    asset = client.get(f"/projects/{project_id}/asset")
    assert asset.status_code == 200
    assert asset.mimetype == "image/png"
    assert asset.data == PNG_HEADER

    dashboard = client.get("/")
    assert b"Oak &amp; Main Market" in dashboard.data


def test_project_creation_rejects_non_image_upload(client):
    client.get("/projects/new")
    response = client.post(
        "/projects",
        data={
            "csrf_token": csrf_token(client),
            "name": "Unsafe upload",
            "site_image": (io.BytesIO(b"not an image"), "site.svg"),
        },
        content_type="multipart/form-data",
    )

    assert response.status_code == 422
    assert b"Upload a PNG, JPEG, or WebP image" in response.data


def test_document_save_uses_revision_check(client):
    created = create_project(client)
    project_id = project_id_from_redirect(created)
    document_url = f"/api/v1/projects/{project_id}/document"
    loaded = client.get(document_url).get_json()
    camera = {
        "id": "camera-1",
        "type": "camera",
        "x": 0.25,
        "y": 0.5,
        "direction_degrees": -90,
        "fov_degrees": 60,
        "range": 0.2,
        "label": "C01",
        "note": "Main entrance",
    }
    payload = {
        "revision": loaded["revision"],
        "document": {"schema_version": 1, "items": [camera]},
        "notes": "Confirm lift access.",
    }

    saved = client.patch(
        document_url,
        json=payload,
        headers={"X-CSRF-Token": csrf_token(client)},
    )
    conflict = client.patch(
        document_url,
        json=payload,
        headers={"X-CSRF-Token": csrf_token(client)},
    )

    assert saved.status_code == 200
    assert saved.get_json()["revision"] == loaded["revision"] + 1
    assert conflict.status_code == 409
    reloaded = client.get(document_url).get_json()
    assert reloaded["document"]["items"][0]["label"] == "C01"
    assert reloaded["project"]["notes"] == "Confirm lift access."


def test_state_changing_requests_require_csrf(client):
    response = client.post(
        "/projects",
        data={
            "name": "Missing CSRF",
            "site_image": (io.BytesIO(PNG_HEADER), "site.png"),
        },
        content_type="multipart/form-data",
    )

    assert response.status_code == 400
