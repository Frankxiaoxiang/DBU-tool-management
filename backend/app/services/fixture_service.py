import re

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from extensions import db
from app.models.batch import Batch
from app.models.fixture import Fixture
from app.models.fixture_status_history import FixtureStatusHistory
from app.models.project import Project
from app.exceptions import ConflictError, ForbiddenError, NotFoundError, ValidationError
from app.services.code_generator import generate_fixture_code
from app.services.state_machine import (
    TRANSITIONS, StateMachineError,
    force_transition, reject, transition,
)
from app.utils.enums import FixtureStatus as S

# PATCH /:id/status 精细 trigger × role 校验（Blueprint 层粗拦，Service 层精细）
TRIGGER_ROLE_MAP = {
    'iqc_pass':              ['super_admin', 'iqc'],
    'concession_approved':   ['super_admin', 'iqc'],
    'emergency_auth':        ['super_admin', 'iqc'],
    'return_repair':         ['super_admin', 'iqc'],
    'normal':                ['super_admin', 'me'],
    'acceptance_pass':       ['super_admin', 'me'],
    'rework':                ['super_admin', 'me'],
    'acceptance_fail_scrap': ['super_admin', 'me'],
    'checkout':              ['super_admin', 'production_lead', 'warehouse'],
    'return':                ['super_admin', 'production_lead', 'warehouse'],
    'maintenance_due':       ['super_admin', 'production_lead', 'warehouse'],
    'repair_request':        ['super_admin', 'production_lead', 'warehouse'],
    'scrap':                 ['super_admin', 'pm'],
    'seal':                  ['super_admin', 'warehouse'],
    'release_seal':          ['super_admin'],
}

REJECT_TRIGGERS = {'return_repair'}

# 从 fixture_code 中解析套号，例如 "EGL-FB-YN#3-A1" → 3
_SET_NO_RE = re.compile(r'#(\d+)-')

# force_transition 的 to_status 合法值集合
_VALID_STATUSES = {v for k, v in vars(S).items() if not k.startswith('_')}


# ---------------------------------------------------------------------------
# 内部工具
# ---------------------------------------------------------------------------

def _serialize_item(fixture):
    return {
        'id':                   fixture.id,
        'fixture_code':         fixture.fixture_code,
        'batch_id':             fixture.batch_id,
        'project_id':           fixture.project_id,
        'fixture_type_code':    fixture.fixture_type_code,
        'set_no':               fixture.set_no,
        'current_version_code': fixture.current_version_code,
        'current_status':       fixture.current_status,
        'parent_fixture_id':    fixture.parent_fixture_id,
        'supplier_id':          fixture.supplier_id,
        'lead_time_days':       fixture.lead_time_days,
        'planned_arrival_date': (
            fixture.planned_arrival_date.isoformat()
            if fixture.planned_arrival_date else None
        ),
        'is_sealed':            fixture.is_sealed,
        'sealed_at':            fixture.sealed_at.isoformat() if fixture.sealed_at else None,
        'sealed_by':            fixture.sealed_by,
        'status':               fixture.status,
        'created_by':           fixture.created_by,
        'created_at':           fixture.created_at.isoformat() if fixture.created_at else None,
        'updated_at':           fixture.updated_at.isoformat() if fixture.updated_at else None,
        'version':              fixture.version,
    }


def _get_or_404(fixture_id):
    fixture = db.session.get(Fixture, fixture_id)
    if not fixture:
        raise NotFoundError('治具不存在')
    return fixture


# ---------------------------------------------------------------------------
# 公开 Service 函数
# ---------------------------------------------------------------------------

def list_fixtures(filters, page, per_page):
    stmt = select(Fixture)

    if filters.get('project_id'):
        stmt = stmt.where(Fixture.project_id == filters['project_id'])
    if filters.get('batch_id'):
        stmt = stmt.where(Fixture.batch_id == filters['batch_id'])
    if filters.get('current_status'):
        stmt = stmt.where(Fixture.current_status == filters['current_status'])
    if filters.get('fixture_code'):
        stmt = stmt.where(Fixture.fixture_code.like(f"%{filters['fixture_code']}%"))

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = db.session.execute(count_stmt).scalar()

    items_stmt = (
        stmt.order_by(Fixture.created_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
    )
    fixtures = db.session.execute(items_stmt).scalars().all()

    return {
        'items':    [_serialize_item(f) for f in fixtures],
        'total':    total,
        'page':     page,
        'per_page': per_page,
    }


def get_fixture_by_id(fixture_id):
    return _serialize_item(_get_or_404(fixture_id))


def create_fixture(payload, operator_id):
    if not payload.get('batch_id'):
        raise ValidationError('batch_id 为必填项', field='batch_id')
    if not payload.get('fixture_type_code'):
        raise ValidationError('fixture_type_code 为必填项', field='fixture_type_code')

    batch_id = int(payload['batch_id'])
    fixture_type_code = payload['fixture_type_code']

    batch = db.session.get(Batch, batch_id)
    if not batch:
        raise NotFoundError('批次不存在')
    if batch.status == 'cancelled':
        raise ValidationError('批次已作废，不可新建治具')

    project = db.session.get(Project, batch.project_id)
    if not project:
        raise NotFoundError('项目不存在')

    # generate_fixture_code 内部校验项目状态并自动计算套号
    fixture_code = generate_fixture_code(project.project_code, fixture_type_code)

    # 从 fixture_code 中解析套号（例如 "EGL-FB-YN#3-A1" → set_no=3）
    m = _SET_NO_RE.search(fixture_code)
    set_no = int(m.group(1)) if m else 1

    fixture = Fixture(
        fixture_code=fixture_code,
        batch_id=batch_id,
        project_id=batch.project_id,
        fixture_type_code=fixture_type_code,
        set_no=set_no,
        current_version_code='A1',
        status='active',
        created_by=operator_id,
    )
    if 'supplier_id' in payload:
        fixture.supplier_id = payload['supplier_id']
    if 'lead_time_days' in payload:
        fixture.lead_time_days = payload['lead_time_days']
    if 'planned_arrival_date' in payload:
        fixture.planned_arrival_date = payload['planned_arrival_date']

    try:
        db.session.add(fixture)
        db.session.commit()
        db.session.refresh(fixture)
    except IntegrityError:
        db.session.rollback()
        raise ConflictError('fixture_code 生成冲突，请重试')

    return _serialize_item(fixture)


def update_fixture(fixture_id, payload, operator_id):
    fixture = _get_or_404(fixture_id)

    if fixture.status == 'cancelled':
        raise ValidationError('已作废的治具不可编辑')

    request_version = payload['version']  # Blueprint 已前置校验 'version' in payload
    assert request_version is not None, 'version is required'
    if fixture.version != request_version:
        raise ConflictError(
            '数据已被其他请求修改，请刷新后重试',
            data={'server_version': fixture.version, 'your_version': request_version},
        )

    if 'supplier_id' in payload:
        fixture.supplier_id = payload['supplier_id']
    if 'lead_time_days' in payload:
        fixture.lead_time_days = payload['lead_time_days']
    if 'planned_arrival_date' in payload:
        fixture.planned_arrival_date = payload['planned_arrival_date']

    fixture.version += 1
    db.session.commit()
    db.session.refresh(fixture)
    return _serialize_item(fixture)


def change_fixture_status(fixture_id, trigger, operator_id, operator_role_codes, reason=None):
    fixture = _get_or_404(fixture_id)

    if trigger not in TRIGGER_ROLE_MAP:
        raise ValidationError(f'无效的 trigger 值: {trigger}', field='trigger')

    if not set(operator_role_codes) & set(TRIGGER_ROLE_MAP[trigger]):
        raise ForbiddenError('无权执行该操作')

    try:
        if trigger in REJECT_TRIGGERS:
            reject(fixture, operator_id, reason or '')
        else:
            from_status = fixture.current_status
            allowed = TRANSITIONS.get(from_status, {})
            # 按当前状态反查 trigger 对应的 to_status
            to_status = next(
                (ts for ts, tr in allowed.items() if tr == trigger), None
            )
            if to_status is None:
                raise ValidationError(
                    f'当前状态 {from_status} 下 trigger={trigger} 无合法目标状态',
                    field='trigger',
                )
            transition(fixture, to_status, trigger, operator_id, reason=reason)
    except StateMachineError as e:
        raise ValidationError(str(e), field='trigger')

    db.session.commit()
    db.session.refresh(fixture)
    return _serialize_item(fixture)


def version_bump(fixture_id: int, request_version: int, operator_id: int) -> dict:
    """
    图纸版本升级：A1→A2→A3→B1→B2→B3→C1...
    只改 current_version_code 字段，不新建 fixture（CLAUDE.md §e.7）。
    成功后写一条 FixtureStatusHistory（auxiliary event，不走 state_machine.transition()）。
    """
    assert request_version is not None  # 乐观锁守卫（§e.5）

    fixture = db.session.get(Fixture, fixture_id)  # 新 API（09_dev_rules.md 后端 #11）
    if fixture is None:
        raise NotFoundError(f'治具 {fixture_id} 不存在')

    # 乐观锁手动校验（§e.5 / 后端 #7）
    if fixture.version != request_version:
        raise ConflictError(
            '数据已被其他请求修改，请刷新后重试',
            data={'server_version': fixture.version, 'your_version': request_version},
        )

    old_ver = fixture.current_version_code
    new_ver = _next_version_code(old_ver)

    fixture.current_version_code = new_ver
    fixture.version += 1

    # auxiliary event: bypasses state_machine.transition() by design
    # (from_status == to_status == current_status; version diff recorded in reason)
    history = FixtureStatusHistory(
        fixture_id=fixture.id,
        from_status=fixture.current_status,
        to_status=fixture.current_status,
        trigger_type='version_bump',
        reason=f'图纸版本升级: {old_ver} → {new_ver}',
        operator_id=operator_id,
    )
    db.session.add(history)
    db.session.commit()
    db.session.refresh(fixture)
    return _serialize_item(fixture)


def _next_version_code(current: str) -> str:
    """
    版本推进规则（《编码规则 V1.0》§4.2）：
    格式 [A-Z][1-3]；数字 < 3 → 数字+1；数字 == 3 → 字母进位，数字重置为 1。
    Z3 视为上限，抛 ValidationError。
    """
    if not current or len(current) < 2:
        raise ValidationError(f'无效的版本号格式: {current!r}')

    letter = current[0].upper()
    try:
        num = int(current[1])
    except ValueError:
        raise ValidationError(f'无效的版本号格式: {current!r}')

    if letter == 'Z' and num == 3:
        raise ValidationError('版本号已达上限（Z3），无法继续升级')

    if num < 3:
        return f'{letter}{num + 1}'
    else:  # num == 3，字母进位，数字重置为 1
        return f'{chr(ord(letter) + 1)}1'


def copy_to_batch(source_fixture_id: int, target_batch_id: int, operator_id: int) -> dict:
    """
    加开-复制图纸：以源治具为模板生成新 fixture。
    - parent_fixture_id 指向源治具（仅用于溯源，§e.7）
    - current_version_code 继承源治具当前版本（§e.7 / 《编码规则 V1.0》§4.3）
    - fixture_code / set_no 由 generate_fixture_code() 在目标项目+型号下递增生成（Service 层不拼接编码字符串）
    - 新 fixture 初始 current_status = 'pending_iqc'（新建赋值，不走 transition()）
    - 本函数不修改源治具，源治具 version 不自增
    """
    # ── 1. 查源治具 ───────────────────────────────────────────────────────────
    source = db.session.get(Fixture, source_fixture_id)
    if source is None:
        raise NotFoundError(f'源治具 {source_fixture_id} 不存在')
    if source.status == 'cancelled':
        raise ValidationError('源治具已作废，不可复制')

    # ── 2. 查目标批次 ─────────────────────────────────────────────────────────
    target_batch = db.session.get(Batch, target_batch_id)
    if target_batch is None:
        raise NotFoundError(f'目标批次 {target_batch_id} 不存在')
    if target_batch.status == 'cancelled':
        raise ValidationError('目标批次已作废，不可复制治具到此批次')

    # ── 3. 跨项目校验 ─────────────────────────────────────────────────────────
    if target_batch.project_id != source.project_id:
        raise ValidationError('目标批次与源治具不属于同一个项目，禁止跨项目复制')

    # ── 4. 取目标项目代号，生成新编码（套号在目标项目+型号下递增） ──────────
    project = db.session.get(Project, target_batch.project_id)
    if project is None:
        raise NotFoundError('项目不存在')

    # version_code 传入源治具当前版本，新编码嵌入继承版本（§e.7 / 《编码规则 V1.0》§4.3）
    new_fixture_code = generate_fixture_code(
        project.project_code,
        source.fixture_type_code,
        version_code=source.current_version_code,
    )
    m = _SET_NO_RE.search(new_fixture_code)
    new_set_no = int(m.group(1)) if m else 1

    # ── 5. 创建新 fixture ─────────────────────────────────────────────────────
    new_fixture = Fixture(
        fixture_code         =new_fixture_code,
        batch_id             =target_batch_id,
        project_id           =target_batch.project_id,
        fixture_type_code    =source.fixture_type_code,
        set_no               =new_set_no,
        current_version_code =source.current_version_code,  # 继承源治具当前版本（§e.7）
        current_status       ='pending_iqc',                 # 新建赋值，不走 transition()（§e.4）
        parent_fixture_id    =source.id,                     # 溯源（§e.7，仅用于此场景）
        status               ='active',
        created_by           =operator_id,
    )
    try:
        db.session.add(new_fixture)
        db.session.commit()
        db.session.refresh(new_fixture)
    except IntegrityError:
        db.session.rollback()
        raise ConflictError('fixture_code 生成冲突，请重试')

    return _serialize_item(new_fixture)


def force_fixture_status(fixture_id, to_status, reason, operator_id):
    fixture = _get_or_404(fixture_id)

    if not reason or not reason.strip():
        raise ValidationError('reason 不得为空', field='reason')

    if to_status not in _VALID_STATUSES:
        raise ValidationError(f'to_status 无效', field='to_status')

    try:
        force_transition(fixture, to_status, operator_id, reason)
    except ValueError as e:
        raise ValidationError(str(e), field='reason')

    db.session.commit()
    db.session.refresh(fixture)
    return _serialize_item(fixture)
