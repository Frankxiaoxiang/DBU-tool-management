from sqlalchemy import func, or_

from extensions import db
from app.models.project import Project
from app.models.user import User
from app.exceptions import ConflictError, NotFoundError, ValidationError
from app.services.code_generator import generate_project_code

VALID_PRODUCT_TYPES = ('SUS_VC', 'CU_VC', 'HP')


# ---------------------------------------------------------------------------
# 内部序列化
# ---------------------------------------------------------------------------

def _serialize_item(project, owner_name):
    return {
        'id': project.id,
        'project_code': project.project_code,
        'project_name': project.project_name,
        'product_type': project.product_type,
        'project_owner_id': project.project_owner_id,
        'owner_name': owner_name,
        'status': project.status,
        'created_at': project.created_at.isoformat() if project.created_at else None,
        'updated_at': project.updated_at.isoformat() if project.updated_at else None,
        'version': project.version,
    }


def _serialize_detail(project, owner_name):
    return {
        'id': project.id,
        'project_code': project.project_code,
        'project_name': project.project_name,
        'product_type': project.product_type,
        'project_owner_id': project.project_owner_id,
        'owner_name': owner_name,
        'status': project.status,
        'cancelled_reason': project.cancelled_reason,
        'cancelled_at': project.cancelled_at.isoformat() if project.cancelled_at else None,
        'cancelled_by': project.cancelled_by,
        'created_by': project.created_by,
        'created_at': project.created_at.isoformat() if project.created_at else None,
        'updated_at': project.updated_at.isoformat() if project.updated_at else None,
        'version': project.version,
        'batches': [],  # Phase 1 占位，实现待 Step 1-3
    }


# ---------------------------------------------------------------------------
# 内部工具
# ---------------------------------------------------------------------------

def _get_or_404(project_id):
    project = Project.query.get(project_id)
    if not project:
        raise NotFoundError('项目不存在')
    return project


def _validate_owner(owner_id, field='project_owner_id'):
    owner = User.query.get(owner_id)
    if not owner or not owner.is_active:
        raise ValidationError('对应用户不存在或已停用', field=field)
    return owner


# ---------------------------------------------------------------------------
# 公开 Service 函数
# ---------------------------------------------------------------------------

def list_projects(filters, page, per_page):
    query = Project.query

    if filters.get('product_type'):
        query = query.filter(Project.product_type == filters['product_type'])
    if filters.get('status'):
        query = query.filter(Project.status == filters['status'])
    if filters.get('owner_id'):
        query = query.filter(Project.project_owner_id == filters['owner_id'])
    if filters.get('keyword'):
        kw = f"%{filters['keyword']}%"
        query = query.filter(or_(
            Project.project_code.like(kw),
            Project.project_name.like(kw),
        ))

    pagination = query.order_by(Project.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )

    items = pagination.items
    owner_ids = {p.project_owner_id for p in items}
    owners = (
        {u.id: u.full_name for u in User.query.filter(User.id.in_(owner_ids)).all()}
        if owner_ids else {}
    )

    return {
        'items': [_serialize_item(p, owners.get(p.project_owner_id)) for p in items],
        'total': pagination.total,
        'page': page,
        'per_page': per_page,
    }


def get_project_by_id(project_id):
    project = _get_or_404(project_id)
    owner = User.query.get(project.project_owner_id)
    return _serialize_detail(project, owner.full_name if owner else None)


def create_project(payload, operator_id):
    for field in ('project_code', 'project_name', 'product_type', 'project_owner_id'):
        if not payload.get(field):
            raise ValidationError(f'{field} 为必填项', field=field)

    generate_project_code(payload['project_code'])  # 格式 + 唯一性校验

    if payload['product_type'] not in VALID_PRODUCT_TYPES:
        raise ValidationError('product_type 非法值', field='product_type')

    owner = _validate_owner(payload['project_owner_id'])

    project = Project(
        project_code=payload['project_code'],
        project_name=payload['project_name'].strip(),
        product_type=payload['product_type'],
        project_owner_id=payload['project_owner_id'],
        status='active',
        created_by=operator_id,
        version=0,
    )
    db.session.add(project)
    db.session.commit()
    db.session.refresh(project)
    return _serialize_detail(project, owner.full_name)


def update_project(project_id, payload, operator_id):
    project = _get_or_404(project_id)
    request_version = payload['version']  # Blueprint 已前置校验 'version' in body
    assert request_version is not None, 'version is required'
    if project.version != request_version:
        raise ConflictError('数据已被其他请求修改，请刷新后重试')

    if 'project_name' in payload:
        if not str(payload['project_name']).strip():
            raise ValidationError('project_name 不得为空字符串', field='project_name')
        project.project_name = payload['project_name'].strip()

    if 'product_type' in payload:
        if payload['product_type'] not in VALID_PRODUCT_TYPES:
            raise ValidationError('product_type 非法值', field='product_type')
        project.product_type = payload['product_type']

    if 'project_owner_id' in payload:
        _validate_owner(payload['project_owner_id'])
        project.project_owner_id = payload['project_owner_id']

    project.version += 1
    db.session.commit()
    db.session.refresh(project)

    owner = User.query.get(project.project_owner_id)
    return _serialize_detail(project, owner.full_name if owner else None)


def cancel_project(project_id, reason, operator_id, request_version):
    project = _get_or_404(project_id)
    if project.status == 'cancelled':
        raise ValidationError('项目已处于作废状态')
    assert request_version is not None, 'version is required'
    if project.version != request_version:
        raise ConflictError('数据已被其他请求修改，请刷新后重试')

    project.status = 'cancelled'
    project.cancelled_reason = reason
    project.cancelled_at = func.now()
    project.cancelled_by = operator_id
    project.version += 1
    db.session.commit()
    db.session.refresh(project)  # 取回 func.now() 的服务端实际值

    return {
        'id': project.id,
        'status': project.status,
        'cancelled_reason': project.cancelled_reason,
        'cancelled_at': project.cancelled_at.isoformat() if project.cancelled_at else None,
        'cancelled_by': project.cancelled_by,
        'version': project.version,
    }


def transfer_project_owner(project_id, new_owner_id, operator_id, request_version):
    project = _get_or_404(project_id)
    assert request_version is not None, 'version is required'
    if project.version != request_version:
        raise ConflictError('数据已被其他请求修改，请刷新后重试')

    owner = _validate_owner(new_owner_id, field='new_owner_id')
    project.project_owner_id = new_owner_id
    project.version += 1
    db.session.commit()

    return {
        'id': project.id,
        'project_owner_id': project.project_owner_id,
        'owner_name': owner.full_name,
        'version': project.version,
    }
