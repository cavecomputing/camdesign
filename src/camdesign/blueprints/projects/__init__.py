from flask import Blueprint

projects = Blueprint("projects", __name__)

from camdesign.blueprints.projects import routes  # noqa: E402, F401
