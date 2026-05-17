"""
Drawing Blueprint — /api/drawings

端点：
  POST  /api/drawings/               上传图纸/DFM（multipart/form-data）
  GET   /api/drawings/               查询治具图纸列表（?fixture_id= 必填）
  PATCH /api/drawings/:id/confirm    PM 确认图纸

铁律：
  - business_record 无 DELETE、无通用 PUT
  - 扁平化资源，fixture_id 在 body/form 中传
  - POST / GET 根路由加尾部斜杠（§h）
  - 命名路由 /confirm 禁止加尾部斜杠（§h）
  - multipart 从 request.files / request.form 读，非 request.get_json()
  - 不调 state_machine.transition()，不改 current_status
"""
from flask import Blueprint, request
from flask_jwt_extended import jwt_required, get_jwt_identity

from app.exceptions import ValidationError
from app.utils.decorators import require_role
from app.utils.response import success_response
from app.services.drawing_service import DrawingService

drawings_bp = Blueprint('drawings', __name__)


def _serialize_drawing(d):
    return {
        'id': d.id,
        'fixture_id': d.fixture_id,
        'version_code': d.version_code,
        'drawing_type': d.drawing_type,
        'file_path': d.file_path,
        'acceptance_standard': d.acceptance_standard,
        'bom_info': d.bom_info,
        'is_copied': d.is_copied,
        'source_drawing_id': d.source_drawing_id,
        'uploaded_by': d.uploaded_by,
        'confirmed_by': d.confirmed_by,
        'confirmed_at': d.confirmed_at.isoformat() if d.confirmed_at else None,
        'created_at': d.created_at.isoformat() if d.created_at else None,
    }


@drawings_bp.route('/', methods=['POST'])
@jwt_required()
@require_role('super_admin', 'design_engineer')
def create_drawing():
    """POST /api/drawings/ — 上传图纸/DFM（multipart/form-data）"""
    operator_id = int(get_jwt_identity())

    fixture_id_raw = request.form.get('fixture_id')
    if not fixture_id_raw:
        raise ValidationError('fixture_id 为必填项')
    try:
        fixture_id = int(fixture_id_raw)
    except ValueError:
        raise ValidationError('fixture_id 须为整数')

    version_code = request.form.get('version_code', '').strip()
    drawing_type = request.form.get('drawing_type', '').strip()
    acceptance_standard = request.form.get('acceptance_standard') or None
    bom_info = request.form.get('bom_info') or None
    is_copied = request.form.get('is_copied', 'false').lower() in ('true', '1', 'yes')
    source_drawing_id_raw = request.form.get('source_drawing_id')
    source_drawing_id = int(source_drawing_id_raw) if source_drawing_id_raw else None

    file_storage = request.files.get('file')

    drawing = DrawingService.create_drawing(
        fixture_id=fixture_id,
        version_code=version_code,
        drawing_type=drawing_type,
        file_storage=file_storage,
        acceptance_standard=acceptance_standard,
        bom_info=bom_info,
        is_copied=is_copied,
        source_drawing_id=source_drawing_id,
        operator_id=operator_id,
    )
    return success_response(_serialize_drawing(drawing), code=201)


@drawings_bp.route('/', methods=['GET'])
@jwt_required()
@require_role('super_admin', 'design_engineer', 'pm', 'me', 'iqc')
def list_drawings():
    """GET /api/drawings/?fixture_id= — 查询治具图纸列表"""
    fixture_id_raw = request.args.get('fixture_id')
    if not fixture_id_raw:
        raise ValidationError('fixture_id 为必填项')
    try:
        fixture_id = int(fixture_id_raw)
    except ValueError:
        raise ValidationError('fixture_id 须为整数')

    drawings = DrawingService.list_drawings(fixture_id)
    return success_response([_serialize_drawing(d) for d in drawings])


@drawings_bp.route('/<int:drawing_id>/confirm', methods=['PATCH'])
@jwt_required()
@require_role('super_admin', 'pm')
def confirm_drawing(drawing_id):
    """PATCH /api/drawings/:id/confirm — PM 确认图纸（无请求体，由 JWT 取操作人）"""
    operator_id = int(get_jwt_identity())
    drawing = DrawingService.confirm_drawing(drawing_id, operator_id)
    return success_response({
        'id': drawing.id,
        'confirmed_by': drawing.confirmed_by,
        'confirmed_at': drawing.confirmed_at.isoformat() if drawing.confirmed_at else None,
    })
