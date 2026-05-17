"""
PurchaseRequisitionService — 采购申请单 Service

业务规则：
- business_record：只增不改不删，无 version 字段，无乐观锁
- requisition_no 由本 Service 生成，格式：PR-YYYYMMDD-XXXX（4位当日序号，从数据库查当日最大值递增）
- 本模块不调 state_machine.transition()，不改 fixture.current_status
"""
from datetime import datetime, date

from extensions import db
from app.models.purchase_requisition import PurchaseRequisition
from app.models.fixture import Fixture
from app.models.drawing import Drawing
from app.exceptions import ConflictError, NotFoundError, ValidationError


class PurchaseRequisitionService:

    @staticmethod
    def _generate_requisition_no():
        today_str = date.today().strftime('%Y%m%d')
        prefix = f'PR-{today_str}-'

        from sqlalchemy import select
        stmt = (
            select(PurchaseRequisition.requisition_no)
            .where(PurchaseRequisition.requisition_no.like(f'{prefix}%'))
            .order_by(PurchaseRequisition.requisition_no.desc())
            .limit(1)
        )
        last = db.session.execute(stmt).scalar_one_or_none()
        if last:
            last_seq = int(last.split('-')[-1])
            new_seq = last_seq + 1
        else:
            new_seq = 1
        return f'{prefix}{new_seq:04d}'

    @staticmethod
    def create_purchase_requisition(fixture_id, drawing_id, quantity,
                                    spec_note, required_date, operator_id):
        if not fixture_id:
            raise ValidationError('fixture_id 为必填项')
        if quantity is None:
            raise ValidationError('quantity 为必填项')
        if not isinstance(quantity, int) or quantity < 1:
            raise ValidationError('quantity 须 ≥ 1')

        fixture = db.session.get(Fixture, fixture_id)
        if not fixture:
            raise NotFoundError('治具不存在')

        if drawing_id:
            drawing = db.session.get(Drawing, drawing_id)
            if not drawing:
                raise NotFoundError('图纸不存在')

        parsed_required_date = None
        if required_date:
            try:
                parsed_required_date = date.fromisoformat(required_date)
            except ValueError:
                raise ValidationError('required_date 格式非法，请使用 ISO 8601 日期（如 2026-06-15）')

        requisition_no = PurchaseRequisitionService._generate_requisition_no()

        pr = PurchaseRequisition(
            fixture_id=fixture_id,
            requisition_no=requisition_no,
            drawing_id=drawing_id,
            quantity=quantity,
            spec_note=spec_note,
            required_date=parsed_required_date,
            confirm_status='pending',
            created_by=operator_id,
            confirmed_by=None,
            confirmed_at=None,
        )
        db.session.add(pr)
        db.session.commit()
        return pr

    @staticmethod
    def list_purchase_requisitions(fixture_id):
        if not fixture_id:
            raise ValidationError('fixture_id 为必填项')

        fixture = db.session.get(Fixture, fixture_id)
        if not fixture:
            raise NotFoundError('治具不存在')

        from sqlalchemy import select, desc
        stmt = (
            select(PurchaseRequisition)
            .where(PurchaseRequisition.fixture_id == fixture_id)
            .order_by(desc(PurchaseRequisition.created_at))
        )
        return db.session.execute(stmt).scalars().all()

    @staticmethod
    def confirm_purchase_requisition(pr_id, operator_id):
        pr = db.session.get(PurchaseRequisition, pr_id)
        if not pr:
            raise NotFoundError('采购申请单不存在')

        if pr.confirm_status == 'confirmed':
            raise ConflictError('申请单已被确认')

        pr.confirm_status = 'confirmed'
        pr.confirmed_by = operator_id
        pr.confirmed_at = datetime.now()
        db.session.commit()
        return pr
