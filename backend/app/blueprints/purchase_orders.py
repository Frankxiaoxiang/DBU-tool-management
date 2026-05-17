"""
PurchaseOrder Blueprint — /api/purchase-orders

端点：
  POST   /api/purchase-orders/            新建 PO 头
  GET    /api/purchase-orders/            PO 列表
  GET    /api/purchase-orders/:id         PO 详情（含 items + supplier_name）
  POST   /api/purchase-orders/:id/items   添加明细项
  PUT    /api/purchase-orders/:id         编辑 PO 头（含 version 乐观锁）
  PATCH  /api/purchase-orders/:id/cancel  作废 PO

铁律：
- 核心表：禁 DELETE 路由（§e.3）
- POST / GET 根路由加尾部斜杠（§h）；子资源/命名路由禁止加尾部斜杠
- Blueprint 定义无 url_prefix（§d Rule 3）
- 乐观锁 version 必传，body['version'] 不得用 body.get()（§e.5 / §d Rule 5）
- JWT identity 强转 int
"""
from flask import Blueprint, request
from flask_jwt_extended import jwt_required, get_jwt_identity

from app.utils.decorators import require_role
from app.services.purchase_order_service import PurchaseOrderService
from app.utils.response import success_response
from app.exceptions import ValidationError

purchase_orders_bp = Blueprint('purchase_orders', __name__)


# ─── 序列化辅助 ──────────────────────────────────────────────────────

def _serialize_item(item):
    """PurchaseOrderItem → dict（仅 Model 实际有的字段）。"""
    return {
        'id': item.id,
        'purchase_order_id': item.purchase_order_id,
        'fixture_id': item.fixture_id,
        'unit_price': str(item.unit_price) if item.unit_price is not None else None,
        'item_lead_time_days': item.item_lead_time_days,
        'created_at': item.created_at.isoformat() if item.created_at else None,
        # Known Gap：item_name / quantity / unit / remark / line_total 字段 Model 不存在
    }


def _serialize_po(po, include_items=False):
    """PurchaseOrder → dict。"""
    data = {
        'id': po.id,
        'po_no': po.po_no,
        'supplier_id': po.supplier_id,
        'supplier_name': po.supplier.name if po.supplier else None,
        'contract_no': po.contract_no,
        'order_date': po.order_date.isoformat() if po.order_date else None,
        # planned_delivery_date 不在 Model（Q-012 决策 A），响应中不含
        'total_lead_time_days': po.total_lead_time_days,
        'total_amount': str(po.total_amount) if po.total_amount is not None else None,
        'remark': po.remark,
        'status': po.status,
        'cancel_reason': po.cancel_reason,
        'cancelled_at': po.cancelled_at.isoformat() if po.cancelled_at else None,
        'cancelled_by': po.cancelled_by,
        'created_by': po.created_by,
        'created_at': po.created_at.isoformat() if po.created_at else None,
        'updated_at': po.updated_at.isoformat() if po.updated_at else None,
        'version': po.version,
    }
    if include_items:
        data['items'] = [_serialize_item(i) for i in po.items]
    return data


# ─── 端点 ────────────────────────────────────────────────────────────

@purchase_orders_bp.route('/', methods=['POST'])
@jwt_required()
@require_role('super_admin', 'purchaser')
def create_purchase_order():
    """POST /api/purchase-orders/ — 新建 PO 头
    # fixture 绑定请在 PO 创建后单独调用 POST /api/purchase-orders/:id/items
    """
    operator_id = int(get_jwt_identity())
    body = request.get_json(silent=True) or {}

    po = PurchaseOrderService.create_purchase_order(
        supplier_id=body.get('supplier_id'),
        order_date_str=body.get('order_date'),
        contract_no=body.get('contract_no'),
        total_lead_time_days=body.get('total_lead_time_days'),
        total_amount=body.get('total_amount'),
        remark=body.get('remark'),
        operator_id=operator_id,
    )
    return success_response(_serialize_po(po, include_items=True), code=201)


@purchase_orders_bp.route('/', methods=['GET'])
@jwt_required()
def list_purchase_orders():
    """GET /api/purchase-orders/ — PO 列表（过滤 + 分页）"""
    args = request.args
    supplier_id = args.get('supplier_id', type=int)
    status = args.get('status')
    order_date_start = args.get('order_date_start')
    order_date_end = args.get('order_date_end')
    page = args.get('page', 1, type=int)
    page_size = args.get('page_size', 20, type=int)

    rows, total, page, page_size = PurchaseOrderService.list_purchase_orders(
        supplier_id=supplier_id,
        status=status,
        order_date_start=order_date_start,
        order_date_end=order_date_end,
        page=page,
        page_size=page_size,
    )
    return success_response({
        'items': [_serialize_po(po) for po in rows],
        'total': total,
        'page': page,
        'page_size': page_size,
    })


@purchase_orders_bp.route('/<int:po_id>', methods=['GET'])
@jwt_required()
def get_purchase_order(po_id):
    """GET /api/purchase-orders/:id — PO 详情（含 items + supplier_name）"""
    po = PurchaseOrderService.get_purchase_order(po_id)
    return success_response(_serialize_po(po, include_items=True))


@purchase_orders_bp.route('/<int:po_id>/items', methods=['POST'])
@jwt_required()
@require_role('super_admin', 'purchaser')
def add_item(po_id):
    """POST /api/purchase-orders/:id/items — 添加明细项"""
    operator_id = int(get_jwt_identity())
    body = request.get_json(silent=True) or {}

    item = PurchaseOrderService.add_item(
        po_id=po_id,
        fixture_id=body.get('fixture_id'),
        unit_price=body.get('unit_price'),
        item_lead_time_days=body.get('item_lead_time_days'),
        operator_id=operator_id,
    )
    return success_response(_serialize_item(item), code=201)


@purchase_orders_bp.route('/<int:po_id>', methods=['PUT'])
@jwt_required()
@require_role('super_admin', 'purchaser')
def update_purchase_order(po_id):
    """PUT /api/purchase-orders/:id — 编辑 PO 头（含 version 乐观锁）"""
    operator_id = int(get_jwt_identity())
    body = request.get_json(silent=True) or {}

    if 'version' not in body:
        raise ValidationError('version 为必填项')

    po = PurchaseOrderService.update_purchase_order(po_id, body, operator_id)
    return success_response(_serialize_po(po))


@purchase_orders_bp.route('/<int:po_id>/cancel', methods=['PATCH'])
@jwt_required()
@require_role('super_admin', 'purchaser')
def cancel_purchase_order(po_id):
    """PATCH /api/purchase-orders/:id/cancel — 作废 PO（核心表禁 DELETE，§e.3）"""
    operator_id = int(get_jwt_identity())
    body = request.get_json(silent=True) or {}

    if 'version' not in body:
        raise ValidationError('version 为必填项')

    po = PurchaseOrderService.cancel_purchase_order(po_id, body, operator_id)
    return success_response({
        'id': po.id,
        'status': po.status,
        'cancel_reason': po.cancel_reason,
        'cancelled_at': po.cancelled_at.isoformat() if po.cancelled_at else None,
        'cancelled_by': po.cancelled_by,
        'version': po.version,
    })
