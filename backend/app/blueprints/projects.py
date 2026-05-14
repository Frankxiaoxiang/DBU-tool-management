from flask import Blueprint, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from app.exceptions import ValidationError
from app.utils.decorators import require_role
from app.utils.response import success_response
from app.services.snapshot_service import sync_missing_templates
import app.services.project_service as project_service

projects_bp = Blueprint('projects', __name__)  # 不带 url_prefix，注册时统一加 /api/projects


@projects_bp.route('/', methods=['GET'])
@jwt_required()
def list_projects():
    per_page = min(int(request.args.get('per_page', 20)), 100)
    filters = {
        'product_type': request.args.get('product_type'),
        'status':       request.args.get('status'),
        'owner_id':     request.args.get('owner_id', type=int),
        'keyword':      request.args.get('keyword'),
    }
    result = project_service.list_projects(
        filters=filters,
        page=int(request.args.get('page', 1)),
        per_page=per_page,
    )
    return success_response(result)


@projects_bp.route('/', methods=['POST'])
@jwt_required()
@require_role('pm', 'super_admin')
def create_project():
    body = request.get_json(silent=True) or {}
    operator_id = int(get_jwt_identity())
    result = project_service.create_project(body, operator_id)
    return success_response(result, code=201)


@projects_bp.route('/<int:project_id>', methods=['GET'])
@jwt_required()
def get_project(project_id):
    result = project_service.get_project_by_id(project_id)
    return success_response(result)


@projects_bp.route('/<int:project_id>', methods=['PUT'])
@jwt_required()
@require_role('pm', 'super_admin')
def update_project(project_id):
    body = request.get_json(silent=True) or {}
    if 'version' not in body:
        raise ValidationError('version 为必填项', field='version')
    operator_id = int(get_jwt_identity())
    result = project_service.update_project(project_id, body, operator_id)
    return success_response(result)


@projects_bp.route('/<int:project_id>/cancel', methods=['PATCH'])
@jwt_required()
@require_role('pm', 'super_admin')
def cancel_project(project_id):
    body = request.get_json(silent=True) or {}
    if 'version' not in body:
        raise ValidationError('version 为必填项', field='version')
    if not body.get('reason', '').strip():
        raise ValidationError('reason 不能为空', field='reason')
    operator_id = int(get_jwt_identity())
    result = project_service.cancel_project(
        project_id,
        reason=body['reason'].strip(),
        operator_id=operator_id,
        request_version=body['version'],
    )
    return success_response(result)


@projects_bp.route('/<int:project_id>/owner', methods=['PUT'])
@jwt_required()
@require_role('super_admin')
def transfer_owner(project_id):
    body = request.get_json(silent=True) or {}
    if 'version' not in body:
        raise ValidationError('version 为必填项', field='version')
    if 'new_owner_id' not in body:
        raise ValidationError('new_owner_id 为必填项', field='new_owner_id')
    operator_id = int(get_jwt_identity())
    result = project_service.transfer_project_owner(
        project_id,
        new_owner_id=body['new_owner_id'],
        operator_id=operator_id,
        request_version=body['version'],
    )
    return success_response(result)


@projects_bp.route('/<int:project_id>/sync-templates', methods=['POST'])
@jwt_required()
@require_role('super_admin')
def sync_templates(project_id):
    operator_id = int(get_jwt_identity())
    result = sync_missing_templates(project_id, operator_id)
    return success_response(result)
