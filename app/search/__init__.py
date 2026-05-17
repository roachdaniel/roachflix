from flask import Blueprint

search_bp = Blueprint('search', __name__, url_prefix='/search')

from . import routes  # noqa: E402, F401
