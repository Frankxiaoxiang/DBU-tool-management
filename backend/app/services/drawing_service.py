"""
DrawingService — 图纸/DFM 记录 Service

业务规则：
- business_record：只增不改不删，无 version 字段，无乐观锁
- 文件走 utils/upload.py:save_upload()，相对路径正斜杠存入 file_path（§e.2）
- 本模块不调 state_machine.transition()，不改 fixture.current_status（设计阶段无状态流转）
- drawing_type 枚举校验并存库（design_drawing / dfm_report）
"""
from datetime import datetime

from extensions import db
from app.models.drawing import Drawing
from app.models.fixture import Fixture
from app.exceptions import ConflictError, NotFoundError, ValidationError
from app.utils.upload import save_upload


ALLOWED_DRAWING_TYPES = {'design_drawing', 'dfm_report'}


class DrawingService:

    @staticmethod
    def create_drawing(fixture_id, version_code, drawing_type,
                       file_storage, acceptance_standard, bom_info,
                       is_copied, source_drawing_id, operator_id):
        if not fixture_id:
            raise ValidationError('fixture_id 为必填项')
        if not version_code:
            raise ValidationError('version_code 为必填项')
        if not drawing_type:
            raise ValidationError('drawing_type 为必填项')
        if drawing_type not in ALLOWED_DRAWING_TYPES:
            raise ValidationError(
                f'drawing_type 枚举值非法，允许值：{", ".join(sorted(ALLOWED_DRAWING_TYPES))}'
            )
        if file_storage is None or file_storage.filename == '':
            raise ValidationError('file 为必填项')

        fixture = db.session.get(Fixture, fixture_id)
        if not fixture:
            raise NotFoundError('治具不存在')

        if is_copied and source_drawing_id:
            source = db.session.get(Drawing, source_drawing_id)
            if not source:
                raise NotFoundError('来源图纸不存在')
        else:
            source_drawing_id = None

        file_path = save_upload(file_storage, 'drawings')

        drawing = Drawing(
            fixture_id=fixture_id,
            version_code=version_code,
            drawing_type=drawing_type,
            file_path=file_path,
            acceptance_standard=acceptance_standard,
            bom_info=bom_info,
            is_copied=bool(is_copied),
            source_drawing_id=source_drawing_id,
            uploaded_by=operator_id,
            confirmed_by=None,
            confirmed_at=None,
        )
        db.session.add(drawing)
        db.session.commit()
        return drawing

    @staticmethod
    def list_drawings(fixture_id):
        if not fixture_id:
            raise ValidationError('fixture_id 为必填项')

        fixture = db.session.get(Fixture, fixture_id)
        if not fixture:
            raise NotFoundError('治具不存在')

        from sqlalchemy import select, desc
        stmt = (
            select(Drawing)
            .where(Drawing.fixture_id == fixture_id)
            .order_by(desc(Drawing.created_at))
        )
        return db.session.execute(stmt).scalars().all()

    @staticmethod
    def confirm_drawing(drawing_id, operator_id):
        drawing = db.session.get(Drawing, drawing_id)
        if not drawing:
            raise NotFoundError('图纸记录不存在')

        if drawing.confirmed_by is not None:
            raise ConflictError('图纸已被确认')

        drawing.confirmed_by = operator_id
        drawing.confirmed_at = datetime.now()
        db.session.commit()
        return drawing
