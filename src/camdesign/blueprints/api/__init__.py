from flask import Blueprint

api = Blueprint("api", __name__, url_prefix="/api/v1")

from camdesign.blueprints.api import routes  # noqa: E402, F401
