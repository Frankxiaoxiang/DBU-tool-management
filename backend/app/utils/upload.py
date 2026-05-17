import uuid
from pathlib import Path
from datetime import datetime

from flask import current_app

from app.exceptions import ValidationError

ALLOWED_EXTENSIONS = {'pdf', 'jpg', 'jpeg', 'png', 'xlsx', 'xls', 'docx', 'doc', 'zip'}
MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024  # 50 MB


def _get_upload_base() -> Path:
    base = current_app.config.get('UPLOAD_BASE', 'uploads')
    base_path = Path(base)
    if not base_path.is_absolute():
        base_path = Path(current_app.root_path).parent / base_path
    return base_path


def save_upload(file_storage, subdir: str) -> str:
    """Save an uploaded file to UPLOAD_BASE/subdir/YYYY/MM/<uuid>.<ext>.

    Returns the relative path using forward slashes (§e.2 iron rule).
    Raises ValidationError for invalid filename, extension, or file size.
    """
    filename = file_storage.filename or ''
    if not filename:
        raise ValidationError('上传文件名不能为空', field='file')

    suffix = Path(filename).suffix.lower().lstrip('.')
    if suffix not in ALLOWED_EXTENSIONS:
        raise ValidationError(
            f'不支持的文件类型 .{suffix}，允许：{", ".join(sorted(ALLOWED_EXTENSIONS))}',
            field='file',
        )

    # Check file size by reading into memory (Werkzeug FileStorage)
    file_storage.seek(0, 2)  # seek to end
    size = file_storage.tell()
    file_storage.seek(0)      # rewind
    if size > MAX_FILE_SIZE_BYTES:
        raise ValidationError(
            f'文件超过大小限制 50 MB（当前 {size // (1024 * 1024)} MB）',
            field='file',
        )

    now = datetime.now()
    year_month = now.strftime('%Y/%m')
    dest_dir = _get_upload_base() / subdir / now.strftime('%Y') / now.strftime('%m')
    dest_dir.mkdir(parents=True, exist_ok=True)

    unique_name = f'{uuid.uuid4().hex}.{suffix}'
    file_storage.save(str(dest_dir / unique_name))

    # Always return forward-slash relative path for DB storage (§e.2)
    return f'{subdir}/{year_month}/{unique_name}'
