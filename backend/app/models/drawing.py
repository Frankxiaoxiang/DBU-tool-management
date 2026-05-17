"""
Drawing — 图纸 / DFM 报告记录（业务单据 business_record）

设计原则：
- 每次上传建一条记录，drawing_type 区分 design_drawing / dfm_report
- 只增不改不删：无 version 字段，无 updated_at，无 current_status
- file_path 存 save_upload() 返回的相对路径（正斜杠，§e.2）
- source_drawing_id 自引用 FK，use_alter=True 避免循环依赖
"""
from extensions import db


class Drawing(db.Model):
    __tablename__ = 'drawings'
    __table_args__ = (
        db.Index('idx_drawings_fixture', 'fixture_id'),
        db.Index('idx_drawings_version', 'version_code'),
        db.Index('idx_drawings_type', 'drawing_type'),
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
    version_code = db.Column(
        db.String(8),
        nullable=False,
        comment='图纸版本号，对应 fixture.current_version_code（如 A1、A2）',
    )
    drawing_type = db.Column(
        db.String(16),
        nullable=False,
        comment='图纸类型：design_drawing（设计图纸）/ dfm_report（DFM 报告）',
    )
    file_path = db.Column(
        db.String(512),
        nullable=False,
        comment='文件相对路径（正斜杠，由 utils/upload.py:save_upload 返回）',
    )
    acceptance_standard = db.Column(
        db.Text,
        nullable=True,
        comment='关键尺寸 / 验收标准文字描述（主要用于 design_drawing）',
    )
    bom_info = db.Column(
        db.Text,
        nullable=True,
        comment='BOM 信息（主要用于 design_drawing）',
    )
    is_copied = db.Column(
        db.Boolean,
        nullable=False,
        default=False,
        comment='是否复制既有图纸（简化流程标记）',
    )
    # Self-referential FK: use_alter=True lets Alembic add constraint after table creation
    source_drawing_id = db.Column(
        db.BigInteger,
        db.ForeignKey('drawings.id', use_alter=True, name='fk_drawings_source', ondelete='SET NULL'),
        nullable=True,
        comment='复制来源图纸 ID（is_copied=True 时填写）',
    )
    uploaded_by = db.Column(
        db.BigInteger,
        db.ForeignKey('users.id', ondelete='RESTRICT'),
        nullable=False,
        comment='上传者 user_id',
    )
    confirmed_by = db.Column(
        db.BigInteger,
        db.ForeignKey('users.id', ondelete='RESTRICT'),
        nullable=True,
        comment='PM 确认人 user_id',
    )
    confirmed_at = db.Column(
        db.DateTime,
        nullable=True,
        comment='PM 确认时间',
    )
    created_at = db.Column(
        db.DateTime,
        nullable=False,
        server_default=db.func.now(),
        comment='创建时间',
    )

    fixture = db.relationship('Fixture', foreign_keys=[fixture_id], backref='drawings', lazy='select')
    uploader = db.relationship('User', foreign_keys=[uploaded_by], lazy='select')
    confirmer = db.relationship('User', foreign_keys=[confirmed_by], lazy='select')
    source_drawing = db.relationship(
        'Drawing', remote_side=[id], foreign_keys=[source_drawing_id], lazy='select'
    )

    def to_dict(self):
        return {
            'id': self.id,
            'fixture_id': self.fixture_id,
            'version_code': self.version_code,
            'drawing_type': self.drawing_type,
            'file_path': self.file_path,
            'acceptance_standard': self.acceptance_standard,
            'bom_info': self.bom_info,
            'is_copied': self.is_copied,
            'source_drawing_id': self.source_drawing_id,
            'uploaded_by': self.uploaded_by,
            'confirmed_by': self.confirmed_by,
            'confirmed_at': self.confirmed_at.isoformat() if self.confirmed_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
