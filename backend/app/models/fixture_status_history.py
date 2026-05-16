# ★ business_record 表 — 只增不改不删
# ★ 无 status / version / updated_at 字段
# ★ 写入方：services/state_machine.py 的 transition() / reject() / force_transition()
#           以及 version_bump() / seal_batch() 的辅助事件直接 INSERT
# ★ 严禁 __mapper_args__ = {'version_id_col': ...}

from extensions import db


class FixtureStatusHistory(db.Model):
    __tablename__ = 'fixture_status_history'
    __table_args__ = (
        db.Index('idx_fixture', 'fixture_id'),
        db.Index('idx_created', 'created_at'),
        {'mysql_charset': 'utf8mb4', 'mysql_collate': 'utf8mb4_unicode_ci'},
    )

    id            = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    fixture_id    = db.Column(db.BigInteger, db.ForeignKey('fixtures.id'), nullable=False)
    from_status   = db.Column(db.String(32), nullable=True)
    to_status     = db.Column(db.String(32), nullable=False)
    trigger_type  = db.Column(db.String(32), nullable=False)
    reason        = db.Column(db.String(512), nullable=True)
    related_table = db.Column(db.String(64), nullable=True)
    related_id    = db.Column(db.BigInteger, nullable=True)
    operator_id   = db.Column(db.BigInteger, db.ForeignKey('users.id'), nullable=False)
    created_at    = db.Column(db.DateTime, nullable=False, server_default=db.func.now())
