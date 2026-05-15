# backend/app/models/fixture.py
# 对应架构文档：Doc/03_architecture_v1.4.md §2.3 fixtures — 治具主表
# ★ core 表 — 严禁 DELETE 路由；作废走 status='cancelled'
# ★ current_status（12状态机）与 status（行政作废）正交，不可混用（Frank 2026-05-15 裁决）
# ★ 乐观锁：仅 Service 层手动校验 version，严禁 __mapper_args__ = {'version_id_col': version}
# ★ fixture_code 由 services/code_generator.py 生成，前端禁止拼接

from extensions import db


class Fixture(db.Model):
    __tablename__ = 'fixtures'
    __table_args__ = (
        db.Index('idx_batch',   'batch_id'),
        db.Index('idx_project', 'project_id'),
        db.Index('idx_status',  'current_status'),
        db.Index('idx_type',    'fixture_type_code'),
        db.Index('idx_parent',  'parent_fixture_id'),
        {
            'mysql_charset': 'utf8mb4',
            'mysql_collate': 'utf8mb4_unicode_ci',
        }
    )

    id                   = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    fixture_code         = db.Column(db.String(32), unique=True, nullable=False)
    batch_id             = db.Column(db.BigInteger, db.ForeignKey('batches.id'), nullable=False)
    project_id           = db.Column(db.BigInteger, db.ForeignKey('projects.id'), nullable=False)
    fixture_type_code    = db.Column(db.String(16), nullable=False)
    set_no               = db.Column(db.Integer, nullable=False)
    current_version_code = db.Column(db.String(8), nullable=False, default='A1')
    current_status       = db.Column(db.String(16), nullable=False, default='pending_iqc')
    parent_fixture_id    = db.Column(db.BigInteger, db.ForeignKey('fixtures.id'), nullable=True)
    supplier_id          = db.Column(db.BigInteger, db.ForeignKey('suppliers.id'), nullable=True)
    lead_time_days       = db.Column(db.Integer, nullable=True)
    planned_arrival_date = db.Column(db.Date, nullable=True)
    is_sealed            = db.Column(db.Boolean, nullable=False, default=False, server_default='0')
    sealed_at            = db.Column(db.DateTime, nullable=True)
    sealed_by            = db.Column(db.BigInteger, db.ForeignKey('users.id'), nullable=True)
    status               = db.Column(db.String(16), nullable=False, default='active')
    version              = db.Column(db.Integer, nullable=False, default=0)
    created_by           = db.Column(db.BigInteger, db.ForeignKey('users.id'), nullable=False)
    created_at           = db.Column(db.DateTime, nullable=False, default=db.func.now())
    updated_at           = db.Column(db.DateTime, nullable=False, default=db.func.now(),
                                     onupdate=db.func.now())
    # ⚠️ 严禁加 __mapper_args__ = {'version_id_col': version}（CLAUDE.md §e.5）
