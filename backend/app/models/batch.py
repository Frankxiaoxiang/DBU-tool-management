# backend/app/models/batch.py
# 对应架构文档：Doc/03_architecture_v1.4.md §2.3 项目与批次模型
# 表归类：core（作废走 status='cancelled'，禁止 HTTP DELETE）
# 乐观锁：手动 Service 层校验（见 CLAUDE.md §e.5），严禁 __mapper_args__ version_id_col

from extensions import db


class Batch(db.Model):
    __tablename__ = 'batches'
    __table_args__ = (
        db.UniqueConstraint('project_id', 'batch_no', name='uk_project_batch'),
        db.Index('idx_batch_parent', 'parent_batch_id'),
        db.Index('idx_batch_status', 'status'),
        {
            'mysql_charset': 'utf8mb4',
            'mysql_collate': 'utf8mb4_unicode_ci',
        }
    )

    id               = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    project_id       = db.Column(db.BigInteger, db.ForeignKey('projects.id'), nullable=False)
    batch_no         = db.Column(db.String(20), nullable=False)
    batch_type       = db.Column(db.String(20), nullable=False)
    # parent_batch_id：自引用外键，仅 addon 批次类型填值
    parent_batch_id  = db.Column(db.BigInteger, db.ForeignKey('batches.id'), nullable=True)
    flow_path        = db.Column(db.String(16), nullable=False, default='full')
    status           = db.Column(db.String(16), nullable=False, default='draft')
    expected_date    = db.Column(db.Date, nullable=True)
    remark           = db.Column(db.Text, nullable=True)
    cancelled_reason = db.Column(db.Text, nullable=True)
    cancelled_at     = db.Column(db.DateTime, nullable=True)
    cancelled_by     = db.Column(db.BigInteger, db.ForeignKey('users.id'), nullable=True)
    created_by       = db.Column(db.BigInteger, db.ForeignKey('users.id'), nullable=False)
    created_at       = db.Column(db.DateTime, nullable=False, default=db.func.now())
    updated_at       = db.Column(db.DateTime, nullable=False, default=db.func.now(),
                                 onupdate=db.func.now())
    version          = db.Column(db.Integer, nullable=False, default=0)
    # ⚠️ 严禁加 __mapper_args__ = {'version_id_col': version}（CLAUDE.md §e.5）

    project      = db.relationship('Project', foreign_keys=[project_id], backref='batches')
    parent_batch = db.relationship('Batch', remote_side=[id], foreign_keys=[parent_batch_id])
    creator      = db.relationship('User', foreign_keys=[created_by])
    canceller    = db.relationship('User', foreign_keys=[cancelled_by])
