"""
PurchaseRequisition Blueprint — /api/purchase-requisitions

端点：
  POST  /api/purchase-requisitions/            新建采购申请单
  GET   /api/purchase-requisitions/            查询治具申请单列表（?fixture_id= 必填）
  PATCH /api/purchase-requisitions/:id/confirm PM 确认申请单

铁律：
  - business_record 无 DELETE、无通用 PUT
  - 扁平化资源，fixture_id 在 body 中传
  - POST / GET 根路由加尾部斜杠（§h）
  - 命名路由 /confirm 禁止加尾部斜杠（§h）
  - 不调 state_machine.transition()，不改 current_status
"""
from flask import Blueprint, request
from flask_jwt_extended import jwt_required, get_jwt_identity

from app.exceptions import ValidationError
from app.utils.decorators import require_role
from app.utils.response import success_response
from app.services.purchase_requisition_service import PurchaseRequisitionService

purchase_requisitions_bp = Blueprint('purchase_requisitions', __name__)


def _serialize_pr(pr):
    return {
        'id': pr.id,
        'fixture_id': pr.fixture_id,
        'requisition_no': pr.requisition_no,
        'drawing_id': pr.drawing_id,
        'quantity': pr.quantity,
        'spec_note': pr.spec_note,
        'required_date': pr.required_date.isoformat() if pr.required_date else None,
        'confirm_status': pr.confirm_status,
        'created_by': pr.created_by,
        'confirmed_by': pr.confirmed_by,
        'confirmed_at': pr.confirmed_at.isoformat() if pr.confirmed_at else None,
        'created_at': pr.created_at.isoformat() if pr.created_at else None,
    }


@purchase_requisitions_bp.route('/', methods=['POST'])
@jwt_required()
@require_role('super_admin', 'design_engineer', 'pm')
def create_purchase_requisition():
    """POST /api/purchase-requisitions/ — 新建采购申请单"""
    operator_id = int(get_jwt_identity())
    body = request.get_json(silent=True) or {}

    fixture_id = body.get('fixture_id')
    drawing_id = body.get('drawing_id')
    quantity = body.get('quantity')
    spec_note = body.get('spec_note')
    required_date = body.get('required_date')

    pr = PurchaseRequisitionService.create_purchase_requisition(
        fixture_id=fixture_id,
        drawing_id=drawing_id,
        quantity=quantity,
        spec_note=spec_note,
        required_date=required_date,
        operator_id=operator_id,
    )
    return success_response(_serialize_pr(pr), code=201)


@purchase_requisitions_bp.route('/', methods=['GET'])
@jwt_required()
@require_role('super_admin', 'design_engineer', 'pm', 'purchaser')
def list_purchase_requisitions():
    """GET /api/purchase-requisitions/?fixture_id= — 查询采购申请单列表"""
    fixture_id_raw = request.args.get('fixture_id')
    if not fixture_id_raw:
        raise ValidationError('fixture_id 为必填项')
    try:
        fixture_id = int(fixture_id_raw)
    except ValueError:
        raise ValidationError('fixture_id 须为整数')

    prs = PurchaseRequisitionService.list_purchase_requisitions(fixture_id)
    return success_response([_serialize_pr(pr) for pr in prs])


@purchase_requisitions_bp.route('/<int:pr_id>/confirm', methods=['PATCH'])
@jwt_required()
@require_role('super_admin', 'pm')
def confirm_purchase_requisition(pr_id):
    """PATCH /api/purchase-requisitions/:id/confirm — PM 确认申请单"""
    operator_id = int(get_jwt_identity())
    pr = PurchaseRequisitionService.confirm_purchase_requisition(pr_id, operator_id)
    return success_response({
        'id': pr.id,
        'confirm_status': pr.confirm_status,
        'confirmed_by': pr.confirmed_by,
        'confirmed_at': pr.confirmed_at.isoformat() if pr.confirmed_at else None,
    })
