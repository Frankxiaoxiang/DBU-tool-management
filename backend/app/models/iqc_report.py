"""
IqcReport — IQC 检验报告（业务单据 business_record）

字段以 API spec §3 为准：
- result 枚举：pass / fail / concession
- inspector_id（非 inspected_by）
- inspection_date DATETIME（必填）
- file_path 存上传文件的相对路径（正斜杠，§e.2）
- defect_description（可选，result=fail 时建议填写）
"""
from extensions import db


class IqcReport(db.Model):
    __tablename__ = 'iqc_reports'
    __table_args__ = (
        db.Index('idx_iqc_reports_fixture', 'fixture_id'),
        db.Index('idx_iqc_reports_result', 'result'),
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
    result = db.Column(
        db.String(16),
        nullable=False,
        comment='检验结果：pass / fail / concession',
    )
    inspector_id = db.Column(
        db.BigInteger,
        db.ForeignKey('users.id', ondelete='RESTRICT'),
        nullable=False,
        comment='检验员 user_id',
    )
    inspection_date = db.Column(
        db.DateTime,
        nullable=False,
        comment='检验日期时间',
    )
    defect_description = db.Column(
        db.Text,
        nullable=True,
        comment='缺陷描述（result=fail 时建议填写）',
    )
    file_path = db.Column(
        db.String(512),
        nullable=True,
        comment='检验报告附件相对路径（正斜杠，由 utils/upload.py:save_upload 返回）',
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

    fixture = db.relationship('Fixture', foreign_keys=[fixture_id], backref='iqc_reports', lazy='select')
    inspector = db.relationship('User', foreign_keys=[inspector_id], lazy='select')

    def to_dict(self):
        return {
            'id': self.id,
            'fixture_id': self.fixture_id,
            'result': self.result,
            'inspector_id': self.inspector_id,
            'inspection_date': self.inspection_date.isoformat() if self.inspection_date else None,
            'defect_description': self.defect_description,
            'file_path': self.file_path,
            'remark': self.remark,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
