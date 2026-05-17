"""
PurchaseOrder — 采购订单头（核心表 core）

设计原则：
- 核心表：有 status / version，作废走 status='cancelled'，禁 HTTP DELETE（§e.3/§e.12）
- version 字段由 Service 层手动校验（§e.5），严禁 __mapper_args__ ORM 自动版
- fixture_id 在 items 明细表（一 PO 多治具，2026-05-17 架构决策）
- total_amount / unit_price 为成本字段，查看权限控制留 Service/Blueprint 层
- Q-012 Frank 决策 A：无 planned_delivery_date 字段
"""
from extensions import db


class PurchaseOrder(db.Model):
    __tablename__ = 'purchase_orders'
    __table_args__ = (
        db.Index('idx_po_supplier', 'supplier_id'),
        db.Index('idx_po_status', 'status'),
        db.Index('idx_po_order_date', 'order_date'),
        {
            'mysql_charset': 'utf8mb4',
            'mysql_collate': 'utf8mb4_unicode_ci',
        }
    )

    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    po_no = db.Column(
        db.String(32), nullable=False, unique=True,
        comment='PO 单号，由 purchase_order_service 生成'
    )
    supplier_id = db.Column(
        db.BigInteger, db.ForeignKey('suppliers.id', ondelete='RESTRICT'),
        nullable=False, comment='供应商'
    )
    contract_no = db.Column(db.String(64), nullable=True, comment='合同号（选填）')
    order_date = db.Column(
        db.Date, nullable=False,
        comment='采购下单日期（Q-012：Phase 3 仅存下单日，计划日期推算留 Phase 5）'
    )
    total_lead_time_days = db.Column(db.Integer, nullable=True, comment='总交期（天数，选填）')
    total_amount = db.Column(
        db.Numeric(12, 2), nullable=True,
        comment='合同总金额（元）；成本字段，查看权限控制留 Service'
    )
    remark = db.Column(db.Text, nullable=True, comment='备注')
    status = db.Column(
        db.String(16), nullable=False, default='open',
        comment='状态：open（进行中）/ closed（已结案）/ cancelled（已作废）'
    )
    cancel_reason = db.Column(db.String(256), nullable=True, comment='作废原因')
    cancelled_at = db.Column(db.DateTime, nullable=True, comment='作废时间')
    cancelled_by = db.Column(
        db.BigInteger, db.ForeignKey('users.id', ondelete='RESTRICT'),
        nullable=True, comment='作废操作人 user_id'
    )
    created_by = db.Column(
        db.BigInteger, db.ForeignKey('users.id', ondelete='RESTRICT'),
        nullable=False, comment='创建人 user_id'
    )
    created_at = db.Column(
        db.DateTime, nullable=False, default=db.func.now(), comment='创建时间'
    )
    updated_at = db.Column(
        db.DateTime, nullable=False,
        default=db.func.now(), onupdate=db.func.now(),
        comment='最后更新时间'
    )
    version = db.Column(
        db.Integer, nullable=False, default=0,
        comment='乐观锁版本号（手动校验，严禁 __mapper_args__ version_id_col）'
    )

    supplier = db.relationship('Supplier', foreign_keys=[supplier_id], lazy='select')
    creator = db.relationship('User', foreign_keys=[created_by], lazy='select')
    canceller = db.relationship('User', foreign_keys=[cancelled_by], lazy='select')
    items = db.relationship(
        'PurchaseOrderItem', back_populates='purchase_order',
        lazy='select', cascade='all, delete-orphan'
    )

    def to_dict(self, include_items=False):
        data = {
            'id': self.id,
            'po_no': self.po_no,
            'supplier_id': self.supplier_id,
            'contract_no': self.contract_no,
            'order_date': self.order_date.isoformat() if self.order_date else None,
            'total_lead_time_days': self.total_lead_time_days,
            'total_amount': str(self.total_amount) if self.total_amount is not None else None,
            'remark': self.remark,
            'status': self.status,
            'cancel_reason': self.cancel_reason,
            'cancelled_at': self.cancelled_at.isoformat() if self.cancelled_at else None,
            'cancelled_by': self.cancelled_by,
            'created_by': self.created_by,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'version': self.version,
        }
        if include_items:
            data['items'] = [item.to_dict() for item in self.items]
        return data
