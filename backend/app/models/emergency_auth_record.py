"""
EmergencyAuthRecord — 紧急上机授权单（业务单据 business_record）

字段以 API spec §3 为准（Frank 2026-05-17 确认）：
- authorized_by_pm / authorized_by_iqc（非 pm_id / iqc_id）
- authorization_date DATETIME NOT NULL（必填）
- risk_description TEXT NOT NULL（非 risk_note）
- iqc_report_id FK（关联触发本授权的 IQC 报告）
"""
from extensions import db


class EmergencyAuthRecord(db.Model):
    __tablename__ = 'emergency_auth_records'
    __table_args__ = (
        db.Index('idx_emergency_auth_fixture', 'fixture_id'),
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
    iqc_report_id = db.Column(
        db.BigInteger,
        db.ForeignKey('iqc_reports.id', ondelete='RESTRICT'),
        nullable=False,
        comment='触发本授权的 IQC 报告 ID',
    )
    authorized_by_pm = db.Column(
        db.BigInteger,
        db.ForeignKey('users.id', ondelete='RESTRICT'),
        nullable=False,
        comment='PM 授权人 user_id',
    )
    authorized_by_iqc = db.Column(
        db.BigInteger,
        db.ForeignKey('users.id', ondelete='RESTRICT'),
        nullable=False,
        comment='IQC 授权人 user_id',
    )
    authorization_date = db.Column(
        db.DateTime,
        nullable=False,
        comment='授权日期时间',
    )
    risk_description = db.Column(
        db.Text,
        nullable=False,
        comment='风险说明，不得为空',
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

    fixture = db.relationship('Fixture', foreign_keys=[fixture_id], backref='emergency_auth_records', lazy='select')
    iqc_report = db.relationship('IqcReport', foreign_keys=[iqc_report_id], lazy='select')
    pm_authorizer = db.relationship('User', foreign_keys=[authorized_by_pm], lazy='select')
    iqc_authorizer = db.relationship('User', foreign_keys=[authorized_by_iqc], lazy='select')

    def to_dict(self):
        return {
            'id': self.id,
            'fixture_id': self.fixture_id,
            'iqc_report_id': self.iqc_report_id,
            'authorized_by_pm': self.authorized_by_pm,
            'authorized_by_iqc': self.authorized_by_iqc,
            'authorization_date': self.authorization_date.isoformat() if self.authorization_date else None,
            'risk_description': self.risk_description,
            'remark': self.remark,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
