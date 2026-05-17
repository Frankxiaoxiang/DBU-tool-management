"""
PurchaseOrderItem — 采购订单明细（业务单据 business_record）

设计原则：
- 业务单据：只增不改不删，无 version，无 status，无 updated_at（§e.3/§e.12）
- 一行 item 对应一个 fixture_id（一 PO 可含多个治具明细，2026-05-17 架构决策）
- unit_price 为成本字段，Decimal 序列化时转 str 保留精度
"""
from extensions import db


class PurchaseOrderItem(db.Model):
    __tablename__ = 'purchase_order_items'
    __table_args__ = (
        db.Index('idx_poi_po', 'purchase_order_id'),
        db.Index('idx_poi_fixture', 'fixture_id'),
        {
            'mysql_charset': 'utf8mb4',
            'mysql_collate': 'utf8mb4_unicode_ci',
        }
    )

    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    purchase_order_id = db.Column(
        db.BigInteger,
        db.ForeignKey('purchase_orders.id', ondelete='CASCADE'),
        nullable=False, comment='所属 PO'
    )
    fixture_id = db.Column(
        db.BigInteger,
        db.ForeignKey('fixtures.id', ondelete='RESTRICT'),
        nullable=False, comment='关联治具（一 item 一治具）'
    )
    unit_price = db.Column(
        db.Numeric(12, 2), nullable=True,
        comment='单价（元）；成本字段，查看权限控制留 Service'
    )
    item_lead_time_days = db.Column(db.Integer, nullable=True, comment='本明细项交期（天数，选填）')
    created_at = db.Column(
        db.DateTime, nullable=False, default=db.func.now(), comment='创建时间'
    )

    purchase_order = db.relationship(
        'PurchaseOrder', foreign_keys=[purchase_order_id],
        back_populates='items', lazy='select'
    )
    fixture = db.relationship('Fixture', foreign_keys=[fixture_id], lazy='select')

    def to_dict(self):
        return {
            'id': self.id,
            'purchase_order_id': self.purchase_order_id,
            'fixture_id': self.fixture_id,
            'unit_price': str(self.unit_price) if self.unit_price is not None else None,
            'item_lead_time_days': self.item_lead_time_days,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
