from __future__ import annotations

from datetime import date
from io import BytesIO

from flask import abort, current_app, flash, redirect, render_template, request, send_file, url_for

from camdesign.blueprints.projects import projects
from camdesign.db import get_db
from camdesign.domain.bom import build_bom
from camdesign.domain.catalog import load_catalog
from camdesign.exports import bom_filename, render_bom_pdf
from camdesign.repositories.projects import SQLiteProjectRepository
from camdesign.services.projects import InvalidProject, create_project


@projects.get("/")
def index():
    repository = SQLiteProjectRepository(get_db())
    return render_template("projects/index.html", projects=repository.list_recent())


@projects.get("/projects/new")
def new():
    return render_template("projects/new.html")


@projects.post("/projects")
def create():
    repository = SQLiteProjectRepository(get_db())
    try:
        project = create_project(
            repository,
            current_app.config["UPLOAD_DIR"],
            name=request.form.get("name"),
            client_name=request.form.get("client_name"),
            site_address=request.form.get("site_address"),
            notes=request.form.get("notes"),
            image=request.files.get("site_image"),
        )
    except InvalidProject as error:
        flash(str(error), "error")
        return render_template("projects/new.html", form=request.form), 422
    return redirect(url_for("editor.workspace", project_id=project.id))


@projects.get("/projects/<uuid:project_id>/asset")
def asset(project_id):
    repository = SQLiteProjectRepository(get_db())
    project = repository.get(str(project_id))
    if project is None:
        abort(404)
    data_root = current_app.config["DATA_DIR"].resolve()
    asset_path = (data_root / project.image_path).resolve()
    if data_root not in asset_path.parents or not asset_path.is_file():
        abort(404)
    return send_file(asset_path, mimetype=project.image_mime, conditional=True)


@projects.get("/projects/<uuid:project_id>/export/bom.pdf")
def export_bom(project_id):
    project = SQLiteProjectRepository(get_db()).get(str(project_id))
    if project is None:
        abort(404)
    bom = build_bom(project.document, load_catalog(current_app.config["CATALOG_DIR"]))
    pdf = render_bom_pdf(project, bom, generated_on=date.today())
    return send_file(
        BytesIO(pdf),
        mimetype="application/pdf",
        as_attachment=True,
        download_name=bom_filename(project.name),
    )
