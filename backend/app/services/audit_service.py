# ★ audit_service.py — 审计日志写入服务
# ★ 查询端点属 Phase 6，本步只写入
# ★ log_force_action() 由 force_transition() 调用，写一条 AuditLog

import json

from extensions import db
from app.models.audit_log import AuditLog


def log_force_action(fixture, from_status: str, to_status: str,
                     operator_id: int, reason: str) -> None:
    """
    记录超管强制状态跳转审计日志。
    由 state_machine.force_transition() 调用，写入 audit_logs 表。

    Args:
        fixture: Fixture 实例（取 fixture.id 用于 target_id）
        from_status: 跳转前状态
        to_status: 跳转后状态
        operator_id: 操作人 ID
        reason: 强制跳转原因（非空，由 force_transition 已校验）
    """
    detail = json.dumps({
        'from_status': from_status,
        'to_status': to_status,
        'reason': reason,
    }, ensure_ascii=False)

    log = AuditLog(
        action='force_status',
        target_table='fixtures',
        target_id=fixture.id,
        detail=detail,
        operator_id=operator_id,
    )
    db.session.add(log)
    # 不在此处 commit，由调用方（force_transition → Blueprint）统一 commit
