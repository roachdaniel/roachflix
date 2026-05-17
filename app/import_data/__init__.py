from flask import Blueprint

import_bp = Blueprint('import_data', __name__, url_prefix='/import')

from . import routes  # noqa: E402, F401
