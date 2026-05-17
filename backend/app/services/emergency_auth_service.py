"""
EmergencyAuthService — 紧急上机授权单 Service

业务规则：
- business_record：只增不改不删，无 version，无乐观锁
- 无文件字段（JSON body）
- 不调 state_machine.transition()，不改 fixture.current_status（§e.4）

审批-gated 流转（CLAUDE.md §e.6）：
- 授权单创建后，emergency_auth 双签审批流 → TODO Phase 4
- 本步只落库单据数据，不触发审批流
"""
from datetime import datetime

from extensions import db
from app.models.emergency_auth_record import EmergencyAuthRecord
from app.models.fixture import Fixture
from app.models.iqc_report import IqcReport
from app.exceptions import ValidationError, NotFoundError


class EmergencyAuthService:

    @staticmethod
    def create_emergency_auth(fixture_id, iqc_report_id, risk_description,
                               authorized_by_pm, authorized_by_iqc,
                               authorization_date_str, remark):
        """
        新建紧急上机授权单。
        - 双签：authorized_by_pm + authorized_by_iqc 均必填
        - risk_description 不得为空（spec §3）
        - 不触发 emergency_auth 审批流（§e.6 / TODO Phase 4）
        """
        required = {
            'fixture_id': fixture_id,
            'iqc_report_id': iqc_report_id,
            'risk_description': risk_description,
            'authorized_by_pm': authorized_by_pm,
            'authorized_by_iqc': authorized_by_iqc,
            'authorization_date': authorization_date_str,
        }
        for field, val in required.items():
            if val is None or val == '':
                raise ValidationError(f'{field} 为必填项')

        if not str(risk_description).strip():
            raise ValidationError('risk_description 不得为空')

        try:
            authorization_date = datetime.fromisoformat(str(authorization_date_str))
        except (ValueError, TypeError):
            raise ValidationError('authorization_date 格式非法，请使用 ISO 8601 日期时间')

        fixture = db.session.get(Fixture, fixture_id)
        if not fixture:
            raise NotFoundError('治具不存在')

        iqc_report = db.session.get(IqcReport, iqc_report_id)
        if not iqc_report:
            raise NotFoundError('IQC 报告不存在')

        record = EmergencyAuthRecord(
            fixture_id=fixture_id,
            iqc_report_id=iqc_report_id,
            risk_description=str(risk_description).strip(),
            authorized_by_pm=int(authorized_by_pm),
            authorized_by_iqc=int(authorized_by_iqc),
            authorization_date=authorization_date,
            remark=remark or None,
        )
        db.session.add(record)
        db.session.commit()

        # ── 审批-gated 流转钩子（§e.6）──────────────────────────────
        # emergency_auth 双签审批流由 Phase 4 审批引擎接管，当前不实现
        # TODO Phase 4: 授权单创建后触发 emergency_auth 审批流
        # ────────────────────────────────────────────────────────────

        return record

    @staticmethod
    def list_emergency_auth_records(fixture_id):
        """查询治具紧急上机授权单列表，fixture_id 必填，按 created_at DESC。"""
        if not fixture_id:
            raise ValidationError('fixture_id 为必填项')
        fixture = db.session.get(Fixture, fixture_id)
        if not fixture:
            raise NotFoundError('治具不存在')

        from sqlalchemy import select, desc
        stmt = (
            select(EmergencyAuthRecord)
            .where(EmergencyAuthRecord.fixture_id == fixture_id)
            .order_by(desc(EmergencyAuthRecord.created_at))
        )
        return db.session.execute(stmt).scalars().all()
