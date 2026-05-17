"""
PurchaseRequisition — 采购申请单（业务单据 business_record）

设计原则：
- 只增不改不删：无 version 字段，无 updated_at，无 current_status
- confirm_status 仅记录 PM 确认动作结果（pending/confirmed），不是 12 状态机字段
- supplier_id 留在 PO 层，本表仅记录需求侧信息
- requisition_no 由 purchase_requisition_service 生成，Model 只定义 UNIQUE 约束
"""
from extensions import db


class PurchaseRequisition(db.Model):
    __tablename__ = 'purchase_requisitions'
    __table_args__ = (
        db.Index('idx_pr_fixture', 'fixture_id'),
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
    # 编号由 purchase_requisition_service 生成（格式 PR-YYYYMMDD-NNNN）
    requisition_no = db.Column(
        db.String(32),
        nullable=False,
        unique=True,
        comment='采购申请单号，由 purchase_requisition_service 生成',
    )
    drawing_id = db.Column(
        db.BigInteger,
        db.ForeignKey('drawings.id', ondelete='SET NULL'),
        nullable=True,
        comment='关联图纸 ID（选填）',
    )
    quantity = db.Column(
        db.Integer,
        nullable=False,
        comment='申请数量，须 ≥ 1',
    )
    spec_note = db.Column(
        db.Text,
        nullable=True,
        comment='规格说明 / 技术要求',
    )
    required_date = db.Column(
        db.Date,
        nullable=True,
        comment='要求到货日期',
    )
    # 仅记录 PM 确认动作结果，不是 12 状态机字段；枚举：pending / confirmed
    confirm_status = db.Column(
        db.String(16),
        nullable=False,
        default='pending',
        comment='PM 确认状态：pending（待确认）/ confirmed（已确认）',
    )
    created_by = db.Column(
        db.BigInteger,
        db.ForeignKey('users.id', ondelete='RESTRICT'),
        nullable=False,
        comment='申请发起人 user_id',
    )
    confirmed_by = db.Column(
        db.BigInteger,
        db.ForeignKey('users.id', ondelete='RESTRICT'),
        nullable=True,
        comment='PM 确认人 user_id',
    )
    confirmed_at = db.Column(
        db.DateTime,
        nullable=True,
        comment='PM 确认时间',
    )
    created_at = db.Column(
        db.DateTime,
        nullable=False,
        server_default=db.func.now(),
        comment='创建时间',
    )

    fixture = db.relationship(
        'Fixture', foreign_keys=[fixture_id], backref='purchase_requisitions', lazy='select'
    )
    drawing = db.relationship('Drawing', foreign_keys=[drawing_id], lazy='select')
    creator = db.relationship('User', foreign_keys=[created_by], lazy='select')
    confirmer = db.relationship('User', foreign_keys=[confirmed_by], lazy='select')

    def to_dict(self):
        return {
            'id': self.id,
            'fixture_id': self.fixture_id,
            'requisition_no': self.requisition_no,
            'drawing_id': self.drawing_id,
            'quantity': self.quantity,
            'spec_note': self.spec_note,
            'required_date': self.required_date.isoformat() if self.required_date else None,
            'confirm_status': self.confirm_status,
            'created_by': self.created_by,
            'confirmed_by': self.confirmed_by,
            'confirmed_at': self.confirmed_at.isoformat() if self.confirmed_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
