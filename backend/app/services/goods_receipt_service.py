"""
GoodsReceiptService — 到货签收单 Service

业务规则：
- business_record：只增不改不删，无 version，无乐观锁
- GoodsReceipt 无文件字段（API spec 未要求照片，Frank 裁决 Step 3-3-1）
- 请求体为 JSON（非 multipart）
- 本模块不调 state_machine.transition()，不改 fixture.current_status（§e.4）
- 状态流转（→ pending_iqc，trigger=normal）由前端在 POST 成功后另发 PATCH /status（Q-011 决策 A）
"""
from datetime import date, datetime

from extensions import db
from app.models.goods_receipt import GoodsReceipt
from app.models.fixture import Fixture
from app.models.purchase_order import PurchaseOrder
from app.exceptions import ValidationError, NotFoundError


class GoodsReceiptService:

    @staticmethod
    def create_goods_receipt(fixture_id, purchase_order_id, actual_arrival_date_str,
                              received_qty, remark, operator_id):
        """
        新建到货签收单。
        - purchase_order_id 可选
        - received_qty 必填（Model NOT NULL，spec 未列但业务保留）
        - received_by 使用 JWT identity（operator_id），不由前端传入
        - 不触发状态变更（§e.4 / Q-011 决策 A）
        """
        if not fixture_id:
            raise ValidationError('fixture_id 为必填项')
        if not actual_arrival_date_str:
            raise ValidationError('actual_arrival_date 为必填项')
        if received_qty is None:
            raise ValidationError('received_qty 为必填项')
        try:
            received_qty = int(received_qty)
        except (ValueError, TypeError):
            raise ValidationError('received_qty 须为整数')
        if received_qty < 1:
            raise ValidationError('received_qty 须 ≥ 1')

        try:
            parsed = datetime.fromisoformat(str(actual_arrival_date_str))
            actual_arrival_date = parsed.date() if isinstance(parsed, datetime) else parsed
        except (ValueError, TypeError):
            raise ValidationError('actual_arrival_date 格式非法，请使用 ISO 8601 日期（如 2026-05-17）')

        fixture = db.session.get(Fixture, fixture_id)
        if not fixture:
            raise NotFoundError('治具不存在')

        if purchase_order_id:
            po = db.session.get(PurchaseOrder, purchase_order_id)
            if not po:
                raise NotFoundError('采购订单不存在')

        receipt = GoodsReceipt(
            fixture_id=fixture_id,
            purchase_order_id=purchase_order_id or None,
            actual_arrival_date=actual_arrival_date,
            received_qty=received_qty,
            remark=remark or None,
            received_by=operator_id,
        )
        db.session.add(receipt)
        db.session.commit()
        # 状态流转（pending_iqc，trigger=normal）由前端另发 PATCH /status（Q-011 决策 A）
        return receipt

    @staticmethod
    def list_goods_receipts(fixture_id):
        """查询治具到货签收单列表，fixture_id 必填，按 created_at DESC。"""
        if not fixture_id:
            raise ValidationError('fixture_id 为必填项')
        fixture = db.session.get(Fixture, fixture_id)
        if not fixture:
            raise NotFoundError('治具不存在')

        from sqlalchemy import select, desc
        stmt = (
            select(GoodsReceipt)
            .where(GoodsReceipt.fixture_id == fixture_id)
            .order_by(desc(GoodsReceipt.created_at))
        )
        return db.session.execute(stmt).scalars().all()
