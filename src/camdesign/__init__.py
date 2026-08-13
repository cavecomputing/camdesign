from __future__ import annotations

import secrets
from collections.abc import Mapping
from datetime import UTC, datetime, timezone
from pathlib import Path
from typing import Any

from flask import Flask, jsonify, render_template, request
from werkzeug.exceptions import HTTPException

from camdesign import db
from camdesign.blueprints.api import api
from camdesign.blueprints.editor import editor
from camdesign.blueprints.projects import projects
from camdesign.config import Config
from camdesign.security import csrf_token, protect_csrf


def friendly_timestamp(value: str, tz: timezone | None = None) -> str:
    """Format a SQLite UTC timestamp for humans; defaults to the server's local timezone."""
    try:
        parsed = datetime.strptime(value, "%Y-%m-%d %H:%M:%S").replace(tzinfo=UTC)
    except (TypeError, ValueError):
        return value if isinstance(value, str) else ""
    local = parsed.astimezone(tz)
    return f"{local.day} {local.strftime('%b %Y')}, {local.strftime('%I:%M %p').lstrip('0')}"


def create_app(test_config: Mapping[str, Any] | None = None) -> Flask:
    app = Flask(__name__)
    app.config.from_object(Config)
    if test_config:
        app.config.update(test_config)

    if not app.config.get("SECRET_KEY"):
        app.config["SECRET_KEY"] = secrets.token_hex(32)

    app.config["DATA_DIR"].mkdir(parents=True, exist_ok=True)
    app.config["UPLOAD_DIR"].mkdir(parents=True, exist_ok=True)

    db.init_app(app)
    db.migrate_database(Path(app.config["DATABASE"]))
    app.before_request(protect_csrf)
    app.context_processor(lambda: {"csrf_token": csrf_token})
    app.add_template_filter(friendly_timestamp)

    app.register_blueprint(projects)
    app.register_blueprint(editor)
    app.register_blueprint(api)

    @app.after_request
    def add_security_headers(response):
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("Referrer-Policy", "same-origin")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault(
            "Content-Security-Policy",
            "default-src 'self'; img-src 'self' data:; style-src 'self'; "
            "script-src 'self'; connect-src 'self'; object-src 'none'; "
            "base-uri 'self'; form-action 'self'; frame-ancestors 'none'",
        )
        return response

    @app.errorhandler(HTTPException)
    def handle_http_error(error: HTTPException):
        if request.path.startswith("/api/"):
            return jsonify(error={"code": error.name, "message": error.description}), error.code
        return render_template("errors/http.html", error=error), error.code

    return app
