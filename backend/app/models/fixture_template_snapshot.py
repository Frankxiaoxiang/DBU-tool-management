from extensions import db

# 对应架构文档：Doc/03_architecture_v1.4.md §2.4 项目模板快照
# 表归类：business_record（只增不改不删）
# 无 version 字段（无并发写）；无 status / is_active（快照无生命周期）
# 唯一约束 uk_project_type(project_id, fixture_type_code) — 同项目同类型仅一份快照
# fixture_type_code ← fixture_templates.code（sync service 负责映射，见 Step 1-2-2）
# product_type      ← fixture_templates.applicable_products（同上）


class FixtureTemplateSnapshot(db.Model):
    __tablename__ = 'fixture_template_snapshots'
    __table_args__ = (
        db.UniqueConstraint('project_id', 'fixture_type_code', name='uk_project_type'),
        db.Index('idx_project', 'project_id'),
        db.Index('idx_source_template', 'source_template_id'),
        {'mysql_charset': 'utf8mb4', 'mysql_collate': 'utf8mb4_unicode_ci'},
    )

    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    project_id = db.Column(db.BigInteger, db.ForeignKey('projects.id'), nullable=False)
    source_template_id = db.Column(db.BigInteger, db.ForeignKey('fixture_templates.id'), nullable=False)
    fixture_type_code = db.Column(db.String(32), nullable=False)
    product_type = db.Column(db.String(16), nullable=False)
    default_lt_days = db.Column(db.Integer, nullable=True)
    default_iqc_interval_days = db.Column(db.Integer, nullable=True)
    default_install_interval_days = db.Column(db.Integer, nullable=True)
    default_acceptance_interval_days = db.Column(db.Integer, nullable=True)
    default_handover_interval_days = db.Column(db.Integer, nullable=True)
    default_maintenance_threshold = db.Column(db.Integer, nullable=True)
    synced_at = db.Column(db.DateTime, nullable=False, server_default=db.func.now())
    synced_by = db.Column(db.BigInteger, db.ForeignKey('users.id'), nullable=False)
