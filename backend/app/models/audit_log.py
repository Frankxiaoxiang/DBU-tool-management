# ★ business_record 表 — 只增不改不删，审计日志不可篡改
# ★ 无 status / version / updated_at 字段
# ★ 写入方：services/audit_service.py 的 log_force_action()（由 force_transition() 调用）
# ★ 查询端点属 Phase 6，本步只建表，不建 Blueprint
# ★ 严禁 __mapper_args__ = {'version_id_col': ...}

from extensions import db


class AuditLog(db.Model):
    __tablename__ = 'audit_logs'
    __table_args__ = (
        db.Index('idx_action',   'action'),
        db.Index('idx_operator', 'operator_id'),
        db.Index('idx_created',  'created_at'),
        {'mysql_charset': 'utf8mb4', 'mysql_collate': 'utf8mb4_unicode_ci'},
    )

    id           = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    action       = db.Column(db.String(64), nullable=False)
    target_table = db.Column(db.String(64), nullable=True)
    target_id    = db.Column(db.BigInteger, nullable=True)
    detail       = db.Column(db.Text, nullable=True)
    operator_id  = db.Column(db.BigInteger, db.ForeignKey('users.id'), nullable=False)
    created_at   = db.Column(db.DateTime, nullable=False, server_default=db.func.now())
