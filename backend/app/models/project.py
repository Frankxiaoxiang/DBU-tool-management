# backend/app/models/project.py
# 对应架构文档：Doc/03_architecture_v1.4.md §2.3 项目与批次模型
# 表归类：core（作废走 status='cancelled'，禁止 HTTP DELETE）
# 乐观锁：手动 Service 层校验（见 CLAUDE.md §e.5），严禁 __mapper_args__ version_id_col

from extensions import db


class Project(db.Model):
    __tablename__ = 'projects'
    __table_args__ = (
        db.Index('idx_owner', 'project_owner_id'),
        db.Index('idx_product_type', 'product_type'),
        db.Index('idx_status', 'status'),
        {'mysql_charset': 'utf8mb4', 'mysql_collate': 'utf8mb4_unicode_ci'},
    )

    id               = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    project_code     = db.Column(db.String(10), unique=True, nullable=False)
    project_name     = db.Column(db.String(100), nullable=False)
    product_type     = db.Column(db.Enum('SUS_VC', 'CU_VC', 'HP'), nullable=False)
    project_owner_id = db.Column(db.BigInteger, db.ForeignKey('users.id'), nullable=False)
    status           = db.Column(db.String(16), nullable=False, default='active')
    cancelled_reason = db.Column(db.Text, nullable=True)
    cancelled_at     = db.Column(db.DateTime, nullable=True)
    cancelled_by     = db.Column(db.BigInteger, db.ForeignKey('users.id'), nullable=True)
    created_by       = db.Column(db.BigInteger, db.ForeignKey('users.id'), nullable=False)
    created_at       = db.Column(db.DateTime, nullable=False, default=db.func.now())
    updated_at       = db.Column(db.DateTime, nullable=False, default=db.func.now(),
                                 onupdate=db.func.now())
    version          = db.Column(db.Integer, nullable=False, default=0)
