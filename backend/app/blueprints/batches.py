from flask import Blueprint, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from app.exceptions import ValidationError
from app.utils.decorators import require_role
from app.utils.response import error_response, success_response
import app.services.batch_service as batch_service

batch_bp = Blueprint('batch', __name__)  # 不带 url_prefix，注册时统一加 /api/batches


@batch_bp.route('/', methods=['GET'])
@jwt_required()
def list_batches():
    page_size = min(int(request.args.get('per_page', 20)), 100)
    filters = {
        'project_id': request.args.get('project_id', type=int),
        'batch_type': request.args.get('batch_type'),
        'status':     request.args.get('status'),
    }
    result = batch_service.list_batches_with_filter(
        filters=filters,
        page=int(request.args.get('page', 1)),
        page_size=page_size,
    )
    return success_response(result)


@batch_bp.route('/', methods=['POST'])
@jwt_required()
@require_role('pm', 'super_admin')
def create_batch():
    body = request.get_json(silent=True) or {}
    operator_id = int(get_jwt_identity())
    result = batch_service.create_batch(body, operator_id)
    return success_response(result, code=201)


@batch_bp.route('/<int:batch_id>', methods=['GET'])
@jwt_required()
def get_batch(batch_id):
    result = batch_service.get_batch_by_id(batch_id)
    return success_response(result)


@batch_bp.route('/<int:batch_id>', methods=['PUT'])
@jwt_required()
@require_role('pm', 'super_admin')
def update_batch(batch_id):
    body = request.get_json(silent=True) or {}
    if 'version' not in body:
        raise ValidationError('version 为必填项', field='version')
    operator_id = int(get_jwt_identity())
    result = batch_service.update_batch(batch_id, body, operator_id)
    return success_response(result)


@batch_bp.route('/<int:batch_id>/cancel', methods=['PATCH'])
@jwt_required()
@require_role('pm', 'super_admin')
def cancel_batch(batch_id):
    body = request.get_json(silent=True) or {}
    if 'version' not in body:
        raise ValidationError('version 为必填项', field='version')
    if not body.get('reason', '').strip():
        raise ValidationError('reason 不得为空', field='reason')
    operator_id = int(get_jwt_identity())
    result = batch_service.cancel_batch(
        batch_id,
        reason=body['reason'].strip(),
        operator_id=operator_id,
        request_version=body['version'],
    )
    return success_response(result)


@batch_bp.route('/<int:batch_id>/fixtures', methods=['GET'])
@jwt_required()
def get_batch_fixtures(batch_id):
    # TODO(Phase 2): 依赖 fixtures 表建立后实现
    return success_response({'items': [], 'total': 0, 'page': 1, 'per_page': 20})


@batch_bp.route('/<int:batch_id>/gantt', methods=['GET'])
@jwt_required()
def get_batch_gantt(batch_id):
    return error_response('Not implemented: planned for Phase 5', 501)
