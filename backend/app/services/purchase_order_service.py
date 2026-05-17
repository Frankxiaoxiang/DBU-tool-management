"""
PurchaseOrderService — 采购订单 Service

铁律：
- purchase_orders 是核心表：有 status/version，禁 DELETE，作废走 cancel()
- 乐观锁手动校验（§e.5）：version 不匹配 → ConflictError，更新后 version += 1
- 字段更新用 'key' in body 模式（§d Rule 5），禁 body.get()
- Q-012 决策 A：仅存 order_date，计划日期推算留 Phase 5（TODO 钩子）
- Decimal 字段（total_amount/unit_price）序列化时转 str
- 已知 Model-Spec Gap：
  - PO 头无 fixture_id 字段（fixture 关联在 items 层）
  - PO 头无 planned_delivery_date 字段（Q-012 关闭）
  - purchase_order_items 无 item_name/quantity/unit/remark/line_total 字段
"""
from datetime import date, datetime

from extensions import db
from app.models.purchase_order import PurchaseOrder
from app.models.purchase_order_item import PurchaseOrderItem
from app.exceptions import ValidationError, NotFoundError, ConflictError


class PurchaseOrderService:

    # ─── po_no 生成 ──────────────────────────────────────────────
    @staticmethod
    def _generate_po_no():
        """
        生成 PO 单号，格式：PO-YYYYMMDD-XXXX（4 位当日序号）。
        通过当日最大序号 +1 实现递增（MVP，非严格并发安全）。
        """
        today_str = date.today().strftime('%Y%m%d')
        prefix = f'PO-{today_str}-'
        from sqlalchemy import select
        stmt = (
            select(PurchaseOrder.po_no)
            .where(PurchaseOrder.po_no.like(f'{prefix}%'))
            .order_by(PurchaseOrder.po_no.desc())
            .limit(1)
        )
        last = db.session.execute(stmt).scalar_one_or_none()
        if last:
            new_seq = int(last.split('-')[-1]) + 1
        else:
            new_seq = 1
        return f'{prefix}{new_seq:04d}'

    # ─── 新建 PO 头 ───────────────────────────────────────────────
    @staticmethod
    def create_purchase_order(supplier_id, order_date_str, contract_no,
                              total_lead_time_days, total_amount, remark,
                              operator_id):
        """
        新建 PO 头。
        - fixture_id 在 Spec 中为必填，但 Model 无此列（Gap 已知）；
          fixture 绑定请在 PO 创建后单独调用 add_item()
        - planned_delivery_date 静默忽略（Q-012 决策 A）
        - TODO Phase 5: 计划日期级联推算（Q-012 决策 A：本步不实现）
        """
        if not supplier_id:
            raise ValidationError('supplier_id 为必填项')
        if not order_date_str:
            raise ValidationError('order_date 为必填项')

        from app.models.supplier import Supplier
        supplier = db.session.get(Supplier, supplier_id)
        if not supplier:
            raise NotFoundError('供应商不存在')

        try:
            order_date = date.fromisoformat(order_date_str)
        except (ValueError, TypeError):
            raise ValidationError('order_date 格式非法，请使用 ISO 8601 日期（如 2026-05-17）')

        po_no = PurchaseOrderService._generate_po_no()

        po = PurchaseOrder(
            po_no=po_no,
            supplier_id=supplier_id,
            contract_no=contract_no or None,
            order_date=order_date,
            total_lead_time_days=total_lead_time_days or None,
            total_amount=total_amount or None,
            remark=remark or None,
            status='open',
            created_by=operator_id,
            version=0,
        )
        db.session.add(po)
        db.session.commit()
        return po

    # ─── 添加明细项 ───────────────────────────────────────────────
    @staticmethod
    def add_item(po_id, fixture_id, unit_price, item_lead_time_days, operator_id):
        """
        在 PO 下添加明细项（business_record，只增不改不删）。

        已知 Model-Spec Gap：
        - Spec 要求 item_name / quantity / unit / remark / line_total，
          但 purchase_order_items 表无这 5 个字段；
          本函数只处理 Model 实际有的字段（fixture_id / unit_price / item_lead_time_days）。
        - 响应不含 item_name / quantity / unit / line_total。
        """
        po = db.session.get(PurchaseOrder, po_id)
        if not po:
            raise NotFoundError('采购订单不存在')
        if po.status == 'cancelled':
            raise ValidationError('已作废的采购订单不能添加明细项')

        if not fixture_id:
            raise ValidationError('fixture_id 为必填项')
        from app.models.fixture import Fixture
        fixture = db.session.get(Fixture, fixture_id)
        if not fixture:
            raise NotFoundError('治具不存在')

        item = PurchaseOrderItem(
            purchase_order_id=po_id,
            fixture_id=fixture_id,
            unit_price=unit_price or None,
            item_lead_time_days=item_lead_time_days or None,
        )
        db.session.add(item)
        db.session.commit()
        return item

    # ─── PO 详情 ──────────────────────────────────────────────────
    @staticmethod
    def get_purchase_order(po_id):
        """PO 详情，含 items 列表。NotFoundError 兜底。"""
        po = db.session.get(PurchaseOrder, po_id)
        if not po:
            raise NotFoundError('采购订单不存在')
        return po

    # ─── PO 列表 ──────────────────────────────────────────────────
    @staticmethod
    def list_purchase_orders(supplier_id=None, status=None,
                             order_date_start=None, order_date_end=None,
                             page=1, page_size=20):
        """PO 列表，支持 supplier_id / status / order_date 范围过滤 + 分页。"""
        from sqlalchemy import select, func, desc
        stmt = select(PurchaseOrder).order_by(desc(PurchaseOrder.created_at))

        if supplier_id:
            stmt = stmt.where(PurchaseOrder.supplier_id == supplier_id)
        if status:
            stmt = stmt.where(PurchaseOrder.status == status)
        if order_date_start:
            try:
                stmt = stmt.where(
                    PurchaseOrder.order_date >= date.fromisoformat(order_date_start)
                )
            except ValueError:
                raise ValidationError('order_date_start 格式非法')
        if order_date_end:
            try:
                stmt = stmt.where(
                    PurchaseOrder.order_date <= date.fromisoformat(order_date_end)
                )
            except ValueError:
                raise ValidationError('order_date_end 格式非法')

        page = max(1, int(page))
        page_size = min(100, max(1, int(page_size)))
        offset = (page - 1) * page_size

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = db.session.execute(count_stmt).scalar_one()

        rows = db.session.execute(stmt.offset(offset).limit(page_size)).scalars().all()
        return rows, total, page, page_size

    # ─── 编辑 PO 头（乐观锁） ────────────────────────────────────
    @staticmethod
    def update_purchase_order(po_id, body, operator_id):
        """
        编辑 PO 头，含乐观锁手动校验（§e.5）。
        字段更新用 'key' in body 模式（§d Rule 5），禁 body.get()。
        """
        if 'version' not in body:
            raise ValidationError('version 为必填项')

        po = db.session.get(PurchaseOrder, po_id)
        if not po:
            raise NotFoundError('采购订单不存在')
        if po.status == 'cancelled':
            raise ValidationError('已作废的采购订单不能编辑')

        if po.version != body['version']:
            raise ConflictError('数据已被他人修改，请刷新后重试')

        if 'supplier_id' in body:
            from app.models.supplier import Supplier
            supplier = db.session.get(Supplier, body['supplier_id'])
            if not supplier:
                raise NotFoundError('供应商不存在')
            po.supplier_id = body['supplier_id']

        if 'contract_no' in body:
            po.contract_no = body['contract_no']

        if 'order_date' in body:
            try:
                po.order_date = date.fromisoformat(body['order_date'])
            except (ValueError, TypeError):
                raise ValidationError('order_date 格式非法')

        if 'total_lead_time_days' in body:
            po.total_lead_time_days = body['total_lead_time_days']

        if 'total_amount' in body:
            po.total_amount = body['total_amount']

        if 'remark' in body:
            po.remark = body['remark']

        # planned_delivery_date 静默忽略（Q-012 决策 A，Model 无此字段）
        # TODO Phase 5: 计划日期级联推算（Q-012 决策 A：本步不实现）

        po.version += 1
        db.session.commit()
        return po

    # ─── 作废 PO ─────────────────────────────────────────────────
    @staticmethod
    def cancel_purchase_order(po_id, body, operator_id):
        """
        作废 PO，写 status='cancelled'（核心表禁 DELETE，§e.3）。
        含乐观锁校验，含幂等保护（已作废 → 409）。
        """
        if 'version' not in body:
            raise ValidationError('version 为必填项')

        po = db.session.get(PurchaseOrder, po_id)
        if not po:
            raise NotFoundError('采购订单不存在')

        if po.status == 'cancelled':
            raise ConflictError('采购订单已被作废')

        if po.version != body['version']:
            raise ConflictError('数据已被他人修改，请刷新后重试')

        cancel_reason = body.get('cancel_reason') or ''
        if not cancel_reason.strip():
            raise ValidationError('cancel_reason 为必填项')

        po.status = 'cancelled'
        po.cancel_reason = cancel_reason
        po.cancelled_at = datetime.now()
        po.cancelled_by = operator_id
        po.version += 1
        db.session.commit()
        return po
