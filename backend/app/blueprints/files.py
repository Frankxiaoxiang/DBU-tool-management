from flask import Blueprint, send_from_directory, abort
from flask_jwt_extended import jwt_required

from app.utils.upload import _get_upload_base

files_bp = Blueprint('files', __name__)


@files_bp.route('/<path:relpath>')
@jwt_required()
def serve_file(relpath: str):
    upload_base = _get_upload_base()
    try:
        target = (upload_base / relpath).resolve()
        target.relative_to(upload_base.resolve())  # raises ValueError on path traversal
    except ValueError:
        abort(403)
    if not target.exists() or not target.is_file():
        abort(404)
    return send_from_directory(str(upload_base), relpath, as_attachment=False)
