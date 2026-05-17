from flask import Blueprint

watchlist_bp = Blueprint('watchlist', __name__, url_prefix='/')

from . import routes  # noqa: E402, F401
