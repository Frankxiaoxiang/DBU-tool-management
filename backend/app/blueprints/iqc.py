"""
IQC 相关 Blueprint 聚合文件

包含三个独立 Blueprint：
  - goods_receipts_bp  → 注册到 /api/goods-receipts
  - iqc_reports_bp     → 注册到 /api/iqc-reports
  - emergency_auth_bp  → 注册到 /api/emergency-auth-records

铁律：
  - business_record：只 POST + GET，无 DELETE、无通用 PUT（§e.3）
  - 三组端点均加尾部斜杠（POST / GET 根路由，§h）
  - 不调 transition()，不改 current_status（§e.4）
  - 审批-gated 流转 → TODO Phase 4（§e.6）
  - goods-receipts + emergency-auth-records：JSON body（request.get_json()）
  - iqc-reports：multipart（request.form / request.files）
"""
from flask import Blueprint, request
from flask_jwt_extended import jwt_required, get_jwt_identity

from app.utils.decorators import require_role
from app.services.goods_receipt_service import GoodsReceiptService
from app.services.iqc_service import IqcService
from app.services.emergency_auth_service import EmergencyAuthService
from app.utils.response import success_response


# ════════════════════════════════════════════════════════════════
# Blueprint 1：goods_receipts_bp
# ════════════════════════════════════════════════════════════════
goods_receipts_bp = Blueprint('goods_receipts', __name__)   # 无 url_prefix


def _serialize_receipt(r):
    return {
        'id': r.id,
        'fixture_id': r.fixture_id,
        'purchase_order_id': r.purchase_order_id,
        'actual_arrival_date': r.actual_arrival_date.isoformat()
                               if r.actual_arrival_date else None,
        'received_qty': r.received_qty,
        'received_by': r.received_by,
        'remark': r.remark,
        'created_at': r.created_at.isoformat() if r.created_at else None,
    }


@goods_receipts_bp.route('/', methods=['POST'])
@jwt_required()
@require_role('super_admin', 'warehouse')
def create_goods_receipt():
    """
    POST /api/goods-receipts/ — 到货签收（JSON body，无文件）
    状态流转（→ pending_iqc）由前端另发 PATCH /api/fixtures/:id/status（Q-011 决策 A）
    """
    operator_id = int(get_jwt_identity())
    body = request.get_json(silent=True) or {}

    fixture_id_raw = body.get('fixture_id')
    if not fixture_id_raw:
        from app.exceptions import ValidationError
        raise ValidationError('fixture_id 为必填项')
    fixture_id = int(fixture_id_raw)

    purchase_order_id_raw = body.get('purchase_order_id')
    purchase_order_id = int(purchase_order_id_raw) if purchase_order_id_raw else None

    receipt = GoodsReceiptService.create_goods_receipt(
        fixture_id=fixture_id,
        purchase_order_id=purchase_order_id,
        actual_arrival_date_str=body.get('actual_arrival_date', ''),
        received_qty=body.get('received_qty'),
        remark=body.get('remark'),
        operator_id=operator_id,
    )
    return success_response(_serialize_receipt(receipt), code=201)


@goods_receipts_bp.route('/', methods=['GET'])
@jwt_required()
@require_role('super_admin', 'warehouse', 'pm', 'iqc')
def list_goods_receipts():
    """GET /api/goods-receipts/?fixture_id= — 查询到货签收单列表"""
    from app.exceptions import ValidationError
    fixture_id_raw = request.args.get('fixture_id')
    if not fixture_id_raw:
        raise ValidationError('fixture_id 为必填项')
    receipts = GoodsReceiptService.list_goods_receipts(int(fixture_id_raw))
    return success_response([_serialize_receipt(r) for r in receipts])


# ════════════════════════════════════════════════════════════════
# Blueprint 2：iqc_reports_bp
# ════════════════════════════════════════════════════════════════
iqc_reports_bp = Blueprint('iqc_reports', __name__)   # 无 url_prefix


def _serialize_iqc_report(r):
    return {
        'id': r.id,
        'fixture_id': r.fixture_id,
        'result': r.result,
        'inspection_date': r.inspection_date.isoformat() if r.inspection_date else None,
        'inspector_id': r.inspector_id,
        'defect_description': r.defect_description,
        'file_path': r.file_path,
        'remark': r.remark,
        'created_at': r.created_at.isoformat() if r.created_at else None,
    }


@iqc_reports_bp.route('/', methods=['POST'])
@jwt_required()
@require_role('super_admin', 'iqc')
def create_iqc_report():
    """
    POST /api/iqc-reports/ — IQC 检验结果录入（multipart/form-data）

    状态流转钩子（前端负责）：
      result='pass'       → 前端发 PATCH /status trigger=iqc_pass（无审批，可直接执行）
      result='fail'       → 前端走三方审批（return_repair），Phase 4 实现
      result='concession' → 前端走让步审批（concession_approved），Phase 4 实现
    """
    operator_id = int(get_jwt_identity())  # noqa: F841 — 操作人身份已验证，暂不写入单据

    # multipart：非文件字段从 request.form 取
    fixture_id_raw = request.form.get('fixture_id')
    if not fixture_id_raw:
        from app.exceptions import ValidationError
        raise ValidationError('fixture_id 为必填项')
    fixture_id = int(fixture_id_raw)

    inspector_id_raw = request.form.get('inspector_id')
    if not inspector_id_raw:
        from app.exceptions import ValidationError
        raise ValidationError('inspector_id 为必填项')
    inspector_id = int(inspector_id_raw)

    result = request.form.get('result', '').strip()
    inspection_date = request.form.get('inspection_date', '').strip()
    defect_description = request.form.get('defect_description') or None
    remark = request.form.get('remark') or None
    file_storage = request.files.get('file')

    report = IqcService.create_iqc_report(
        fixture_id=fixture_id,
        result=result,
        inspection_date_str=inspection_date,
        inspector_id=inspector_id,
        defect_description=defect_description,
        remark=remark,
        file_storage=file_storage,
    )
    return success_response(_serialize_iqc_report(report), code=201)


@iqc_reports_bp.route('/', methods=['GET'])
@jwt_required()
@require_role('super_admin', 'iqc', 'pm', 'me')
def list_iqc_reports():
    """GET /api/iqc-reports/?fixture_id= — 查询 IQC 报告列表"""
    from app.exceptions import ValidationError
    fixture_id_raw = request.args.get('fixture_id')
    if not fixture_id_raw:
        raise ValidationError('fixture_id 为必填项')
    reports = IqcService.list_iqc_reports(int(fixture_id_raw))
    return success_response([_serialize_iqc_report(r) for r in reports])


@iqc_reports_bp.route('/<int:report_id>/approve', methods=['PATCH'])
@jwt_required()
def approve_iqc_report(report_id):  # noqa: F841
    """PATCH /api/iqc-reports/:id/approve — IQC 不合格三方审批 [Phase 4 占位]"""
    raise NotImplementedError('IQC 不合格三方审批，将在 Phase 4 审批模块实现')


# ════════════════════════════════════════════════════════════════
# Blueprint 3：emergency_auth_bp
# ════════════════════════════════════════════════════════════════
emergency_auth_bp = Blueprint('emergency_auth', __name__)   # 无 url_prefix


def _serialize_ear(r):
    return {
        'id': r.id,
        'fixture_id': r.fixture_id,
        'iqc_report_id': r.iqc_report_id,
        'risk_description': r.risk_description,
        'authorized_by_pm': r.authorized_by_pm,
        'authorized_by_iqc': r.authorized_by_iqc,
        'authorization_date': r.authorization_date.isoformat()
                              if r.authorization_date else None,
        'remark': r.remark,
        'created_at': r.created_at.isoformat() if r.created_at else None,
    }


@emergency_auth_bp.route('/', methods=['POST'])
@jwt_required()
@require_role('super_admin', 'pm', 'iqc')
def create_emergency_auth():
    """
    POST /api/emergency-auth-records/ — 紧急上机授权单（JSON body，无文件）

    审批-gated 钩子（§e.6）：
      授权单创建后，emergency_auth 双签审批流 Phase 4 实现
      当前只落库，不触发审批
    """
    body = request.get_json(silent=True) or {}

    record = EmergencyAuthService.create_emergency_auth(
        fixture_id=body.get('fixture_id'),
        iqc_report_id=body.get('iqc_report_id'),
        risk_description=body.get('risk_description'),
        authorized_by_pm=body.get('authorized_by_pm'),
        authorized_by_iqc=body.get('authorized_by_iqc'),
        authorization_date_str=body.get('authorization_date'),
        remark=body.get('remark'),
    )
    return success_response(_serialize_ear(record), code=201)


@emergency_auth_bp.route('/', methods=['GET'])
@jwt_required()
@require_role('super_admin', 'pm', 'iqc', 'me')
def list_emergency_auth_records():
    """GET /api/emergency-auth-records/?fixture_id= — 查询紧急上机授权单列表"""
    from app.exceptions import ValidationError
    fixture_id_raw = request.args.get('fixture_id')
    if not fixture_id_raw:
        raise ValidationError('fixture_id 为必填项')
    records = EmergencyAuthService.list_emergency_auth_records(int(fixture_id_raw))
    return success_response([_serialize_ear(r) for r in records])


@emergency_auth_bp.route('/<int:record_id>/approve', methods=['PATCH'])
@jwt_required()
def approve_emergency_auth(record_id):  # noqa: F841
    """PATCH /api/emergency-auth-records/:id/approve — 紧急上机审批 [Phase 4 占位]"""
    raise NotImplementedError('紧急上机授权审批，将在 Phase 4 审批模块实现')
