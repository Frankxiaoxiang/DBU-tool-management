# ★ state_machine.py — 治具状态机核心
# ★ transition()：正常流转，严格走 TRANSITIONS，签名严禁出现 force/bypass 参数
# ★ reject()：审批驳回，走 REJECT_CONFIG
# ★ force_transition()：唯一允许绕过 TRANSITIONS 的入口，必填 reason，写 audit_logs
# ★ 除本文件内部外，任何代码严禁 fixture.current_status = ...（CLAUDE.md §e.4）

from extensions import db
from app.models.fixture_status_history import FixtureStatusHistory
from app.services.audit_service import log_force_action
from app.utils.enums import FixtureStatus as S


# {from_status: {to_status: trigger}}
# 注：同一 from→to 对只能有一个 trigger；通过 (from, to) 反查 trigger 自然支持驳回路径复用
TRANSITIONS = {
    S.PENDING_IQC: {
        S.IQC_INSPECTING:    'normal',
        S.EMERGENCY_PENDING: 'emergency_auth',
    },
    S.IQC_INSPECTING: {
        S.INSTALLING:          'iqc_pass',
        S.CONCESSION_ACCEPTED: 'concession_approved',
        S.PENDING_IQC:         'return_repair',     # 复用：既用于退厂返修，也用于审批驳回
    },
    S.EMERGENCY_PENDING:    {S.INSTALLING: 'normal'},
    S.CONCESSION_ACCEPTED:  {S.INSTALLING: 'normal'},
    S.INSTALLING:           {S.ACCEPTANCE_TESTING: 'normal'},
    S.ACCEPTANCE_TESTING: {
        S.IN_STOCK:    'acceptance_pass',
        S.INSTALLING:  'rework',                   # ★ V1.4 改名，与 'normal' 区分
        S.SCRAPPED:    'acceptance_fail_scrap',    # 试产不合格可直接报废
    },
    S.IN_STOCK: {
        S.IN_USE:    'checkout',
        S.SEALED:    'seal',
        S.SCRAPPED:  'scrap',
    },
    S.IN_USE: {
        S.IN_STOCK:     'return',
        S.MAINTAINING:  'maintenance_due',
        S.REPAIRING:    'repair_request',
    },
    S.MAINTAINING: {S.IN_STOCK: 'normal'},
    S.REPAIRING:   {S.IN_STOCK: 'normal'},
    S.SEALED:      {S.IN_STOCK: 'release_seal'},
    S.SCRAPPED:    {},                             # 终态
}

# 驳回时使用的 (trigger, to_status) 配置 — 复用 TRANSITIONS 中已定义的合法路径
REJECT_CONFIG = {
    S.IQC_INSPECTING:     ('return_repair', S.PENDING_IQC),
    S.ACCEPTANCE_TESTING: ('rework',         S.INSTALLING),
}


class StateMachineError(Exception):
    pass


def transition(fixture, to_status, trigger, operator_id,
               reason=None, related=None):
    """
    正常状态流转 — 严格走 TRANSITIONS，不可绕过。
    任何尝试通过本函数做"非法"跳转都会抛 StateMachineError。
    """
    from_status = fixture.current_status
    allowed = TRANSITIONS.get(from_status, {})
    if to_status not in allowed:
        raise StateMachineError(f"非法状态转换：{from_status} -> {to_status}")
    if allowed[to_status] != trigger:
        raise StateMachineError(
            f"触发器不匹配：期望 {allowed[to_status]}，实际 {trigger}"
        )

    history = FixtureStatusHistory(
        fixture_id=fixture.id,
        from_status=from_status,
        to_status=to_status,
        trigger_type=trigger,
        reason=reason,
        related_table=related[0] if related else None,
        related_id=related[1] if related else None,
        operator_id=operator_id,
    )
    db.session.add(history)
    fixture.current_status = to_status
    return fixture


def reject(fixture, operator_id, reason):
    """
    审批驳回 → 走 TRANSITIONS 内已配置的回退路径。
    严格校验，不再使用 force=True 绕过（★ V1.4 修订）。
    """
    config = REJECT_CONFIG.get(fixture.current_status)
    if not config:
        raise StateMachineError(
            f"{fixture.current_status} 不支持驳回回退"
        )
    trigger, to_status = config
    return transition(
        fixture, to_status, trigger, operator_id,
        reason=f"[审批驳回] {reason}"
    )


def force_transition(fixture, to_status, operator_id, reason):
    """
    超管强制跳转 — 唯一允许绕过 TRANSITIONS 校验的入口。
    必须满足：
    1. 操作者是超管（由调用方权限校验保证，本函数不重复校验）
    2. 必须填写原因（非空）
    3. 自动写审计日志
    """
    if not reason or not reason.strip():
        raise ValueError("强制跳转必须填写原因")

    from_status = fixture.current_status
    history = FixtureStatusHistory(
        fixture_id=fixture.id,
        from_status=from_status,
        to_status=to_status,
        trigger_type='forced',                # 历史记录中明确标记
        reason=reason,
        operator_id=operator_id,
    )
    db.session.add(history)
    log_force_action(fixture, from_status, to_status, operator_id, reason)
    fixture.current_status = to_status
    return fixture
