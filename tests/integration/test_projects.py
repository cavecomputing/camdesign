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


def test_delete_project_removes_record_and_uploaded_asset(client, app):
    created = create_project(client)
    project_id = project_id_from_redirect(created)
    asset_path = app.config["UPLOAD_DIR"] / project_id / "base-map.png"
    assert asset_path.is_file()

    dashboard = client.get("/")
    assert f"/projects/{project_id}/delete".encode() in dashboard.data

    confirmation = client.get(f"/projects/{project_id}/delete")
    assert confirmation.status_code == 200
    assert b"This action cannot be undone" in confirmation.data

    deleted = client.post(
        f"/projects/{project_id}/delete",
        data={"csrf_token": csrf_token(client)},
        follow_redirects=True,
    )

    assert deleted.status_code == 200
    assert b"Oak &amp; Main Market&#34; was deleted." in deleted.data
    assert not asset_path.exists()
    assert client.get(f"/projects/{project_id}/editor").status_code == 404
    assert client.get(f"/projects/{project_id}/asset").status_code == 404


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


def test_bom_export_returns_a_named_pdf_of_the_saved_plan(client):
    created = create_project(client)
    project_id = project_id_from_redirect(created)
    document_url = f"/api/v1/projects/{project_id}/document"
    client.patch(
        document_url,
        json={
            "revision": client.get(document_url).get_json()["revision"],
            "document": {
                "schema_version": 1,
                "items": [
                    {
                        "id": "camera-1",
                        "type": "camera",
                        "x": 0.25,
                        "y": 0.5,
                        "direction_degrees": -90,
                        "fov_degrees": 60,
                        "range": 0.2,
                        "label": "C01",
                        "note": "Mount below the front soffit.",
                        "make": "Hanwha",
                        "model": "XND-A9084RV",
                        "license": "WAVE-PRO-01",
                    }
                ],
            },
            "notes": "Confirm lift access before installation.",
        },
        headers={"X-CSRF-Token": csrf_token(client)},
    )

    response = client.get(f"/projects/{project_id}/export/bom.pdf")

    assert response.status_code == 200
    assert response.mimetype == "application/pdf"
    assert response.data.startswith(b"%PDF-")
    # The name reaches the browser from here, so the download is not "bom.pdf" every time.
    assert "oak-main-market-bom.pdf" in response.headers["Content-Disposition"]

    missing = client.get("/projects/00000000-0000-4000-8000-000000000000/export/bom.pdf")
    assert missing.status_code == 404


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
