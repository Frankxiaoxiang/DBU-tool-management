from sqlalchemy import func

from extensions import db
from app.models.batch import Batch
from app.models.project import Project
from app.models.fixture_template_snapshot import FixtureTemplateSnapshot
from app.exceptions import ConflictError, NotFoundError, ValidationError

VALID_BATCH_TYPES = ('manual_init', 'mass_prod', 'addon_quantity', 'addon_optimize')
VALID_FLOW_PATHS = ('full', 'simplified')

BATCH_TYPE_SHORT = {
    'manual_init':    'M0',
    'mass_prod':      'MP',
    'addon_quantity': 'AQ',
    'addon_optimize': 'AO',
}


# ---------------------------------------------------------------------------
# 内部序列化
# ---------------------------------------------------------------------------

def _serialize_item(batch):
    return {
        'id':            batch.id,
        'project_id':    batch.project_id,
        'batch_no':      batch.batch_no,
        'batch_type':    batch.batch_type,
        'flow_path':     batch.flow_path,
        'status':        batch.status,
        'expected_date': batch.expected_date.isoformat() if batch.expected_date else None,
        'remark':        batch.remark,
        'created_by':    batch.created_by,
        'created_at':    batch.created_at.isoformat() if batch.created_at else None,
        'updated_at':    batch.updated_at.isoformat() if batch.updated_at else None,
        'version':       batch.version,
    }


def _serialize_detail(batch):
    return {
        'id':               batch.id,
        'project_id':       batch.project_id,
        'project_code':     batch.project.project_code if batch.project else None,
        'batch_no':         batch.batch_no,
        'batch_type':       batch.batch_type,
        'parent_batch_id':  batch.parent_batch_id,
        'flow_path':        batch.flow_path,
        'status':           batch.status,
        'expected_date':    batch.expected_date.isoformat() if batch.expected_date else None,
        'remark':           batch.remark,
        'cancelled_reason': batch.cancelled_reason,
        'cancelled_at':     batch.cancelled_at.isoformat() if batch.cancelled_at else None,
        'cancelled_by':     batch.cancelled_by,
        'created_by':       batch.created_by,
        'created_at':       batch.created_at.isoformat() if batch.created_at else None,
        'updated_at':       batch.updated_at.isoformat() if batch.updated_at else None,
        'version':          batch.version,
        'fixture_count':    0,  # Phase 1 占位，实现待 Phase 2
    }


# ---------------------------------------------------------------------------
# 内部工具
# ---------------------------------------------------------------------------

def _get_or_404(batch_id):
    batch = db.session.get(Batch, batch_id)
    if not batch:
        raise NotFoundError('批次不存在')
    return batch


def _safe_transition(batch, new_status, operator_id):
    """
    Phase 1 批次级状态变更的唯一入口。
    当前实现：直接更新 batch.status 字段（无状态机校验）。

    # TODO(Phase 4): 审批流接入后，此函数将与 services/state_machine.py
    # 的全局状态机集成，届时需在此处调用 state_machine.transition()，
    # 并走 TRANSITIONS 合法路径校验。禁止在 Phase 1 阶段绕过本函数直接赋值。
    """
    # Phase 1 暂时直接赋值，Phase 4 重构此处
    batch.status = new_status


def _generate_batch_no(project_id, batch_type, project_code):
    """格式：{project_code}-{batch_type_short}-{seq}，seq 基于历史总数（含 cancelled）递增，不回收。"""
    short = BATCH_TYPE_SHORT[batch_type]
    count = db.session.execute(
        db.select(func.count()).select_from(Batch).where(
            Batch.project_id == project_id,
            Batch.batch_type == batch_type,
        )
    ).scalar()
    seq = (count or 0) + 1
    return f"{project_code}-{short}-{seq}"


# ---------------------------------------------------------------------------
# 公开 Service 函数
# ---------------------------------------------------------------------------

def list_batches_with_filter(filters, page, page_size):
    query = Batch.query

    if filters.get('project_id'):
        query = query.filter(Batch.project_id == filters['project_id'])
    if filters.get('batch_type'):
        query = query.filter(Batch.batch_type == filters['batch_type'])
    if filters.get('status'):
        query = query.filter(Batch.status == filters['status'])

    pagination = query.order_by(Batch.created_at.desc()).paginate(
        page=page, per_page=page_size, error_out=False
    )

    return {
        'items':    [_serialize_item(b) for b in pagination.items],
        'total':    pagination.total,
        'page':     page,
        'per_page': page_size,
    }


def get_batch_by_id(batch_id):
    batch = _get_or_404(batch_id)
    return _serialize_detail(batch)


def create_batch(payload, operator_id):
    # --- 必填字段校验 ---
    if not payload.get('project_id'):
        raise ValidationError('project_id 为必填项', field='project_id')
    if not payload.get('batch_type'):
        raise ValidationError('batch_type 为必填项', field='batch_type')
    if payload['batch_type'] not in VALID_BATCH_TYPES:
        raise ValidationError('batch_type 非法值', field='batch_type')

    project_id = payload['project_id']
    batch_type = payload['batch_type']

    # --- 项目存在性与状态校验 ---
    project = db.session.get(Project, project_id)
    if not project:
        raise NotFoundError('project_id 对应项目不存在')
    if project.status == 'cancelled':
        raise ValidationError('项目已处于 cancelled 状态，不可新建批次')

    # --- 规则 6：项目快照前置验证 ---
    snapshot = FixtureTemplateSnapshot.query.filter_by(project_id=project_id).first()
    if not snapshot:
        raise ValidationError('项目模板快照尚未锁定，无法创建批次')

    # --- 批次类型业务规则 ---
    if batch_type == 'manual_init':
        # 规则 1
        if payload.get('parent_batch_id') is not None:
            raise ValidationError('manual_init 批次不允许有父批次', field='parent_batch_id')
        existing = Batch.query.filter(
            Batch.project_id == project_id,
            Batch.batch_type == 'manual_init',
            Batch.status != 'cancelled',
        ).first()
        if existing:
            raise ValidationError('该项目已存在手动初版批次')
        flow_path = 'full'
        parent_batch_id = None

    elif batch_type == 'mass_prod':
        # 规则 2
        if payload.get('parent_batch_id') is not None:
            raise ValidationError('mass_prod 批次不允许有父批次', field='parent_batch_id')
        existing = Batch.query.filter(
            Batch.project_id == project_id,
            Batch.batch_type == 'mass_prod',
            Batch.status != 'cancelled',
        ).first()
        if existing:
            raise ValidationError('该项目已存在量产批次')
        flow_path = 'full'
        parent_batch_id = None

    else:
        # 规则 3：addon_quantity / addon_optimize
        parent_batch_id = payload.get('parent_batch_id')
        if parent_batch_id is None:
            raise ValidationError('addon 类型批次必须指定父批次', field='parent_batch_id')
        parent = db.session.get(Batch, parent_batch_id)
        if not parent or parent.project_id != project_id:
            raise ValidationError('父批次不属于当前项目', field='parent_batch_id')
        flow_path = payload.get('flow_path', 'full')
        if flow_path not in VALID_FLOW_PATHS:
            raise ValidationError('flow_path 仅允许 full 或 simplified', field='flow_path')

    # --- 规则 4：batch_no 自动生成（绝对不从请求体读取）---
    batch_no = _generate_batch_no(project_id, batch_type, project.project_code)

    batch = Batch(
        project_id=project_id,
        batch_no=batch_no,
        batch_type=batch_type,
        parent_batch_id=parent_batch_id,
        flow_path=flow_path,
        status='draft',
        expected_date=payload.get('expected_date'),
        remark=payload.get('remark'),
        created_by=operator_id,
        version=0,
    )
    db.session.add(batch)
    db.session.commit()
    db.session.refresh(batch)

    result = _serialize_detail(batch)
    if batch_type == 'mass_prod':
        result['urgency_flag'] = True
    return result


def update_batch(batch_id, payload, operator_id):
    batch = _get_or_404(batch_id)

    if batch.status == 'cancelled':
        raise ValidationError('已 cancelled 的批次不可编辑')
    if batch.status == 'sealed':
        raise ValidationError('已封存的批次不可编辑')

    request_version = payload['version']  # Blueprint 已前置校验 'version' in body
    assert request_version is not None, 'version is required'
    if batch.version != request_version:
        raise ConflictError('数据已被其他请求修改，请刷新后重试')

    if 'expected_date' in payload:
        batch.expected_date = payload['expected_date']
    if 'remark' in payload:
        batch.remark = payload['remark']
    if 'flow_path' in payload:
        if payload['flow_path'] not in VALID_FLOW_PATHS:
            raise ValidationError('flow_path 仅允许 full 或 simplified', field='flow_path')
        batch.flow_path = payload['flow_path']

    batch.version += 1
    db.session.commit()
    db.session.refresh(batch)
    return _serialize_detail(batch)


def cancel_batch(batch_id, reason, operator_id, request_version):
    batch = _get_or_404(batch_id)

    if batch.status == 'cancelled':
        raise ValidationError('批次已处于 cancelled 状态')

    assert request_version is not None, 'version is required'
    if batch.version != request_version:
        raise ConflictError('数据已被其他请求修改，请刷新后重试')

    _safe_transition(batch, 'cancelled', operator_id)
    batch.cancelled_reason = reason
    batch.cancelled_at = func.now()
    batch.cancelled_by = operator_id
    batch.version += 1
    db.session.commit()
    db.session.refresh(batch)

    return {
        'id':               batch.id,
        'status':           batch.status,
        'cancelled_reason': batch.cancelled_reason,
        'cancelled_at':     batch.cancelled_at.isoformat() if batch.cancelled_at else None,
        'cancelled_by':     batch.cancelled_by,
        'version':          batch.version,
    }
