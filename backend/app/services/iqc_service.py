"""
IqcService — IQC 检验报告 Service

业务规则：
- business_record：只增不改不删，无 version，无乐观锁
- IQC 报告文件走 save_upload()，相对路径存入 file_path（§e.2）
- 本模块不调 state_machine.transition()，不改 fixture.current_status（§e.4）
- 状态流转全部由前端在 POST 成功后另发 PATCH /status（Q-011 决策 A）

审批-gated 流转（CLAUDE.md §e.6）：
- result='fail'       → 三方审批流（return_repair / concession_approved）→ TODO Phase 4
- result='concession' → 让步审批流 → TODO Phase 4
- 以上审批流在本步仅落库单据，不触发，Service 中注明钩子
"""
from datetime import datetime

from extensions import db
from app.models.iqc_report import IqcReport
from app.models.fixture import Fixture
from app.exceptions import ValidationError, NotFoundError
from app.utils.upload import save_upload


ALLOWED_RESULTS = {'pass', 'fail', 'concession'}


class IqcService:

    @staticmethod
    def create_iqc_report(fixture_id, result, inspection_date_str,
                           inspector_id, defect_description, remark, file_storage):
        """
        新建 IQC 检验报告。
        - result 枚举：pass / fail / concession
        - 文件可选（检验报告 / 照片），存入 file_path
        - 不触发任何状态变更（§e.4 / Q-011 决策 A）

        状态流转钩子（前端负责，本步不实现）：
          result='pass'       → 前端发 PATCH /status trigger=iqc_pass（无审批）
          result='fail'       → 前端走三方审批流（return_repair）→ TODO Phase 4 [HOOK]
          result='concession' → 前端走让步审批流（concession_approved）→ TODO Phase 4 [HOOK]
        """
        if not fixture_id:
            raise ValidationError('fixture_id 为必填项')
        if not result:
            raise ValidationError('result 为必填项')
        if result not in ALLOWED_RESULTS:
            raise ValidationError(
                f'result 枚举值非法，允许值：{", ".join(sorted(ALLOWED_RESULTS))}'
            )
        if not inspection_date_str:
            raise ValidationError('inspection_date 为必填项')
        if not inspector_id:
            raise ValidationError('inspector_id 为必填项')

        try:
            inspection_date = datetime.fromisoformat(str(inspection_date_str))
        except (ValueError, TypeError):
            raise ValidationError('inspection_date 格式非法，请使用 ISO 8601 日期时间')

        fixture = db.session.get(Fixture, fixture_id)
        if not fixture:
            raise NotFoundError('治具不存在')

        file_path = None
        if file_storage and file_storage.filename:
            file_path = save_upload(file_storage, 'iqc')

        report = IqcReport(
            fixture_id=fixture_id,
            result=result,
            inspection_date=inspection_date,
            inspector_id=int(inspector_id),
            defect_description=defect_description or None,
            file_path=file_path,
            remark=remark or None,
        )
        db.session.add(report)
        db.session.commit()

        # ── 审批-gated 流转钩子（§e.6）────────────────────────────
        # result='fail' / 'concession' 时，三方/让步审批流由 Phase 4 审批引擎接管
        # 当前不实现，前端接收 201 响应后根据 result 自行决策后续 PATCH /status 调用
        # TODO Phase 4: 当 result in ('fail', 'concession') 时触发审批流引擎
        # ──────────────────────────────────────────────────────────

        return report

    @staticmethod
    def list_iqc_reports(fixture_id):
        """查询治具 IQC 报告列表，fixture_id 必填，按 created_at DESC。"""
        if not fixture_id:
            raise ValidationError('fixture_id 为必填项')
        fixture = db.session.get(Fixture, fixture_id)
        if not fixture:
            raise NotFoundError('治具不存在')

        from sqlalchemy import select, desc
        stmt = (
            select(IqcReport)
            .where(IqcReport.fixture_id == fixture_id)
            .order_by(desc(IqcReport.created_at))
        )
        return db.session.execute(stmt).scalars().all()
