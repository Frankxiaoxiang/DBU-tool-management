"""
test_state_machine.py — 状态机三函数单元测试
被测模块：app/services/state_machine.py + app/services/audit_service.py
Phase 2 Step 2-6-1
"""
import inspect
import pytest
from sqlalchemy import select

from app.services.state_machine import (
    transition, reject, force_transition,
    StateMachineError,
)
from app.utils.enums import FixtureStatus as S
from app.models.fixture_status_history import FixtureStatusHistory
from app.models.audit_log import AuditLog


# ── 1. transition() ──────────────────────────────────────────────────────────

def test_transition_pending_iqc_to_iqc_inspecting_ok(db_session, make_fixture):
    """合法流转：PENDING_IQC → IQC_INSPECTING，current_status 变更且 FixtureStatusHistory 写入一条"""
    fix = make_fixture(current_status=S.PENDING_IQC)
    operator_id = fix.created_by

    transition(fix, S.IQC_INSPECTING, 'normal', operator_id)
    db_session.flush()

    assert fix.current_status == S.IQC_INSPECTING

    stmt = select(FixtureStatusHistory).where(FixtureStatusHistory.fixture_id == fix.id)
    histories = db_session.execute(stmt).scalars().all()
    assert len(histories) == 1
    h = histories[0]
    assert h.from_status == S.PENDING_IQC
    assert h.to_status == S.IQC_INSPECTING
    assert h.trigger_type == 'normal'
    assert h.operator_id == operator_id


def test_transition_illegal_jump_raises_state_machine_error(db_session, make_fixture):
    """非法跨状态跳转（PENDING_IQC → IN_STOCK）抛 StateMachineError"""
    fix = make_fixture(current_status=S.PENDING_IQC)

    with pytest.raises(StateMachineError):
        transition(fix, S.IN_STOCK, 'normal', fix.created_by)


def test_transition_wrong_trigger_raises_state_machine_error(db_session, make_fixture):
    """合法 from→to 但触发器不匹配（PENDING_IQC → IQC_INSPECTING，trigger='wrong_trigger'）抛 StateMachineError"""
    fix = make_fixture(current_status=S.PENDING_IQC)

    with pytest.raises(StateMachineError):
        transition(fix, S.IQC_INSPECTING, 'wrong_trigger', fix.created_by)


def test_transition_scrapped_terminal_state_raises_error(db_session, make_fixture):
    """终态 SCRAPPED 无出口，任意跳转抛 StateMachineError"""
    fix = make_fixture(current_status=S.SCRAPPED)

    with pytest.raises(StateMachineError):
        transition(fix, S.IN_STOCK, 'normal', fix.created_by)


# ── 2. reject() ──────────────────────────────────────────────────────────────

def test_reject_iqc_inspecting_returns_to_pending_iqc(db_session, make_fixture):
    """IQC_INSPECTING 驳回回退至 PENDING_IQC，trigger='return_repair'，reason 含 [审批驳回] 前缀"""
    fix = make_fixture(current_status=S.IQC_INSPECTING)
    operator_id = fix.created_by

    reject(fix, operator_id, '不合格')
    db_session.flush()

    assert fix.current_status == S.PENDING_IQC

    stmt = select(FixtureStatusHistory).where(FixtureStatusHistory.fixture_id == fix.id)
    histories = db_session.execute(stmt).scalars().all()
    assert len(histories) == 1
    h = histories[0]
    assert h.trigger_type == 'return_repair'
    assert '[审批驳回]' in h.reason


def test_reject_acceptance_testing_returns_to_installing(db_session, make_fixture):
    """ACCEPTANCE_TESTING 驳回回退至 INSTALLING，trigger='rework'"""
    fix = make_fixture(current_status=S.ACCEPTANCE_TESTING)
    operator_id = fix.created_by

    reject(fix, operator_id, '试产不合格')
    db_session.flush()

    assert fix.current_status == S.INSTALLING

    stmt = select(FixtureStatusHistory).where(FixtureStatusHistory.fixture_id == fix.id)
    histories = db_session.execute(stmt).scalars().all()
    assert len(histories) == 1
    assert histories[0].trigger_type == 'rework'


def test_reject_unsupported_state_raises_error(db_session, make_fixture):
    """IN_STOCK 不在 REJECT_CONFIG 中，reject() 抛 StateMachineError"""
    fix = make_fixture(current_status=S.IN_STOCK)

    with pytest.raises(StateMachineError):
        reject(fix, fix.created_by, '错误驳回')


# ── 3. force_transition() ────────────────────────────────────────────────────

def test_force_transition_empty_reason_raises_value_error(db_session, make_fixture):
    """force_transition() 传空字符串 reason 抛 ValueError"""
    fix = make_fixture(current_status=S.IN_STOCK)

    with pytest.raises(ValueError):
        force_transition(fix, S.SEALED, fix.created_by, reason='')


def test_force_transition_none_reason_raises_value_error(db_session, make_fixture):
    """force_transition() 传 None reason 抛 ValueError"""
    fix = make_fixture(current_status=S.IN_STOCK)

    with pytest.raises(ValueError):
        force_transition(fix, S.SEALED, fix.created_by, reason=None)


def test_force_transition_writes_audit_log(db_session, make_fixture):
    """force_transition() 写入 AuditLog(action='force_status')，含正确字段"""
    fix = make_fixture(current_status=S.SCRAPPED)
    operator_id = fix.created_by

    force_transition(fix, S.IN_STOCK, operator_id, reason='测试强制跳转')
    db_session.flush()

    assert fix.current_status == S.IN_STOCK

    stmt = select(AuditLog).where(
        AuditLog.action == 'force_status',
        AuditLog.target_id == fix.id,
    )
    logs = db_session.execute(stmt).scalars().all()
    assert len(logs) == 1
    log = logs[0]
    assert log.target_table == 'fixtures'
    assert log.operator_id == operator_id
    assert '测试强制跳转' in (log.detail or '')


def test_force_transition_writes_forced_trigger_in_history(db_session, make_fixture):
    """force_transition() 在 FixtureStatusHistory 中记录 trigger_type='forced'"""
    fix = make_fixture(current_status=S.SCRAPPED)

    force_transition(fix, S.IN_STOCK, fix.created_by, reason='强制回仓')
    db_session.flush()

    stmt = select(FixtureStatusHistory).where(FixtureStatusHistory.fixture_id == fix.id)
    histories = db_session.execute(stmt).scalars().all()
    assert len(histories) == 1
    assert histories[0].trigger_type == 'forced'


# ── 4. 后门防护 ───────────────────────────────────────────────────────────────

def test_no_back_door_in_transition():
    """transition() 签名不得含 force / bypass 参数，防止 V1.2 后门设计重现（CLAUDE.md §h / §e.4）"""
    sig = inspect.signature(transition)
    assert 'force' not in sig.parameters, \
        f"transition() 含 force 参数，违反 V1.4 铁律！签名：{sig}"
    assert 'bypass' not in sig.parameters, \
        f"transition() 含 bypass 参数，违反 V1.4 铁律！签名：{sig}"
