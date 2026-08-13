from __future__ import annotations

from flask import abort, render_template

from camdesign.blueprints.editor import editor
from camdesign.db import get_db
from camdesign.repositories.projects import SQLiteProjectRepository


@editor.get("/projects/<uuid:project_id>/editor")
def workspace(project_id):
    project = SQLiteProjectRepository(get_db()).get(str(project_id))
    if project is None:
        abort(404)
    return render_template("editor/workspace.html", project=project)
