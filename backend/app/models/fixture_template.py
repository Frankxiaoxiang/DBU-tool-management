from extensions import db


class FixtureTemplate(db.Model):
    __tablename__ = 'fixture_templates'
    __table_args__ = {
        'mysql_charset': 'utf8mb4',
        'mysql_collate': 'utf8mb4_unicode_ci',
    }

    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    code = db.Column(db.String(20), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    process_step = db.Column(db.String(50), nullable=False)
    mode_label = db.Column(db.String(20))
    equipment_label = db.Column(db.String(50))
    applicable_products = db.Column(db.String(10), nullable=False)
    default_lt_days = db.Column(db.Integer)
    is_attachment = db.Column(db.Boolean, nullable=False, default=False)
    remark = db.Column(db.String(200))
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, default=db.func.now())
    updated_at = db.Column(db.DateTime, default=db.func.now(), onupdate=db.func.now())
    version = db.Column(db.Integer, nullable=False, default=1)
