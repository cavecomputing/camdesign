from flask import Blueprint

editor = Blueprint("editor", __name__)

from camdesign.blueprints.editor import routes  # noqa: E402, F401
