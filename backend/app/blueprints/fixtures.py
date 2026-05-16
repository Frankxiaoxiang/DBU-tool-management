from flask import Blueprint, request
from flask_jwt_extended import get_jwt, get_jwt_identity, jwt_required

from app.exceptions import ValidationError
from app.utils.decorators import require_role
from app.utils.response import error_response, success_response
import app.services.fixture_service as fixture_service
import app.services.batch_service as batch_service

fixtures_bp = Blueprint('fixtures', __name__)  # 不带 url_prefix，注册时统一加 /api/fixtures


# ── GET /export 必须在 /<int:fixture_id> 之前注册（防止 "export" 被误作 int 匹配）────────

@fixtures_bp.route('/export', methods=['GET'])
@jwt_required()
def export_fixtures():
    # TODO Phase 6
    return error_response('Not implemented: Phase 6', 501)


# ── 6 个已实现端点 ────────────────────────────────────────────────────────────────────────

@fixtures_bp.route('/', methods=['GET'])
@jwt_required()
def list_fixtures():
    per_page = min(int(request.args.get('per_page', 20)), 100)
    filters = {
        'project_id':    request.args.get('project_id', type=int),
        'batch_id':      request.args.get('batch_id', type=int),
        'current_status': request.args.get('current_status'),
        'fixture_code':  request.args.get('fixture_code'),
    }
    result = fixture_service.list_fixtures(
        filters=filters,
        page=int(request.args.get('page', 1)),
        per_page=per_page,
    )
    return success_response(result)


@fixtures_bp.route('/', methods=['POST'])
@jwt_required()
@require_role('super_admin', 'pm', 'me')
def create_fixture():
    body = request.get_json(silent=True) or {}
    operator_id = int(get_jwt_identity())
    result = fixture_service.create_fixture(body, operator_id)
    return success_response(result, code=201)


@fixtures_bp.route('/<int:fixture_id>', methods=['GET'])
@jwt_required()
def get_fixture(fixture_id):
    result = fixture_service.get_fixture_by_id(fixture_id)
    return success_response(result)


@fixtures_bp.route('/<int:fixture_id>', methods=['PUT'])
@jwt_required()
@require_role('super_admin', 'pm', 'me')
def update_fixture(fixture_id):
    body = request.get_json(silent=True) or {}
    if 'version' not in body:
        raise ValidationError('version 为必填项', field='version')
    operator_id = int(get_jwt_identity())
    result = fixture_service.update_fixture(fixture_id, body, operator_id)
    return success_response(result)


@fixtures_bp.route('/<int:fixture_id>/status', methods=['PATCH'])
@jwt_required()
@require_role('super_admin', 'pm', 'me', 'iqc', 'production_lead', 'warehouse')
def change_fixture_status(fixture_id):
    body = request.get_json(silent=True) or {}
    if 'trigger' not in body:
        raise ValidationError('trigger 为必填项', field='trigger')
    trigger = body['trigger']
    reason = body.get('reason')
    operator_id = int(get_jwt_identity())
    claims = get_jwt()
    operator_role_codes = claims.get('role_codes', [])
    result = fixture_service.change_fixture_status(
        fixture_id, trigger, operator_id, operator_role_codes, reason=reason,
    )
    return success_response(result)


@fixtures_bp.route('/<int:fixture_id>/force-status', methods=['POST'])
@jwt_required()
@require_role('super_admin')
def force_fixture_status(fixture_id):
    body = request.get_json(silent=True) or {}
    if 'to_status' not in body:
        raise ValidationError('to_status 为必填项', field='to_status')
    if 'reason' not in body:
        raise ValidationError('reason 为必填项', field='reason')
    to_status = body['to_status']
    reason = body['reason']
    operator_id = int(get_jwt_identity())
    result = fixture_service.force_fixture_status(fixture_id, to_status, reason, operator_id)
    return success_response(result)


# ── 501 占位端点 ──────────────────────────────────────────────────────────────────────────

@fixtures_bp.route('/batch-seal', methods=['POST'])
@jwt_required()
@require_role('super_admin', 'warehouse')
def batch_seal():
    body = request.get_json(silent=True) or {}
    if 'batch_id' not in body:
        raise ValidationError('batch_id 为必填项', field='batch_id')
    if 'version' not in body:
        raise ValidationError('version 为必填项', field='version')
    operator_id = int(get_jwt_identity())
    result = batch_service.seal_batch(body['batch_id'], body['version'], operator_id)
    return success_response(result)


@fixtures_bp.route('/<int:fixture_id>/version-bump', methods=['POST'])
@jwt_required()
def version_bump(fixture_id):
    # TODO Phase 2 Step 2-4-1
    return error_response('Not implemented: Phase 2 Step 2-4-1', 501)


@fixtures_bp.route('/<int:fixture_id>/copy-to-batch', methods=['POST'])
@jwt_required()
def copy_to_batch(fixture_id):
    # TODO Phase 2 Step 2-5-1
    return error_response('Not implemented: Phase 2 Step 2-5-1', 501)


@fixtures_bp.route('/<int:fixture_id>/release-seal', methods=['POST'])
@jwt_required()
def release_seal(fixture_id):
    # TODO Phase 2 Step 2-7-1
    return error_response('Not implemented: Phase 2 Step 2-7-1', 501)


@fixtures_bp.route('/<int:fixture_id>/recalc-dates', methods=['POST'])
@jwt_required()
def recalc_dates(fixture_id):
    # TODO Phase 5
    return error_response('Not implemented: Phase 5', 501)
