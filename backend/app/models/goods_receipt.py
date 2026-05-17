"""
GoodsReceipt — 到货签收记录（业务单据 business_record）

字段裁决（Frank 2026-05-17）：
- actual_arrival_date 用 DATE（非 DATETIME）
- received_qty 保留（API spec 未列但业务需要）
- purchase_order_id 可选 FK（关联来源 PO）
- remark 可选
- 无 receipt_photo_path（API spec 未要求照片）
"""
from extensions import db


class GoodsReceipt(db.Model):
    __tablename__ = 'goods_receipts'
    __table_args__ = (
        db.Index('idx_goods_receipts_fixture', 'fixture_id'),
        {
            'mysql_charset': 'utf8mb4',
            'mysql_collate': 'utf8mb4_unicode_ci',
        },
    )

    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    fixture_id = db.Column(
        db.BigInteger,
        db.ForeignKey('fixtures.id', ondelete='RESTRICT'),
        nullable=False,
        comment='关联治具 ID',
    )
    purchase_order_id = db.Column(
        db.BigInteger,
        db.ForeignKey('purchase_orders.id', ondelete='RESTRICT'),
        nullable=True,
        comment='关联 PO ID（可选）',
    )
    actual_arrival_date = db.Column(
        db.Date,
        nullable=False,
        comment='实际到货日期',
    )
    received_qty = db.Column(
        db.Integer,
        nullable=False,
        comment='签收数量',
    )
    received_by = db.Column(
        db.BigInteger,
        db.ForeignKey('users.id', ondelete='RESTRICT'),
        nullable=False,
        comment='签收人 user_id',
    )
    remark = db.Column(
        db.Text,
        nullable=True,
        comment='备注',
    )
    created_at = db.Column(
        db.DateTime,
        nullable=False,
        server_default=db.func.now(),
        comment='创建时间',
    )

    fixture = db.relationship('Fixture', foreign_keys=[fixture_id], backref='goods_receipts', lazy='select')
    purchase_order = db.relationship('PurchaseOrder', foreign_keys=[purchase_order_id], lazy='select')
    receiver = db.relationship('User', foreign_keys=[received_by], lazy='select')

    def to_dict(self):
        return {
            'id': self.id,
            'fixture_id': self.fixture_id,
            'purchase_order_id': self.purchase_order_id,
            'actual_arrival_date': self.actual_arrival_date.isoformat() if self.actual_arrival_date else None,
            'received_qty': self.received_qty,
            'received_by': self.received_by,
            'remark': self.remark,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
