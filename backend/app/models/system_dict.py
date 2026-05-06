from extensions import db


class SystemDict(db.Model):
    __tablename__ = 'system_dicts'
    __table_args__ = (
        db.UniqueConstraint('dict_type', 'dict_key', name='uk_dict'),
        {
            'mysql_charset': 'utf8mb4',
            'mysql_collate': 'utf8mb4_unicode_ci',
        },
    )

    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    dict_type = db.Column(db.String(32), nullable=False)
    dict_key = db.Column(db.String(64), nullable=False)
    dict_value = db.Column(db.String(255), nullable=False)
    sort_order = db.Column(db.Integer, default=0)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    version = db.Column(db.Integer, nullable=False, default=1)
    created_at = db.Column(db.DateTime, default=db.func.now())
    updated_at = db.Column(db.DateTime, default=db.func.now(), onupdate=db.func.now())
