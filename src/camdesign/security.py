from __future__ import annotations

import hmac
import secrets

from flask import abort, request, session

SAFE_METHODS = {"GET", "HEAD", "OPTIONS", "TRACE"}


def csrf_token() -> str:
    token = session.get("_csrf_token")
    if token is None:
        token = secrets.token_urlsafe(32)
        session["_csrf_token"] = token
    return token


def protect_csrf() -> None:
    if request.method in SAFE_METHODS:
        return
    expected = session.get("_csrf_token")
    provided = request.headers.get("X-CSRF-Token") or request.form.get("csrf_token")
    if not expected or not provided or not hmac.compare_digest(expected, provided):
        abort(400, description="The form expired. Refresh the page and try again.")
