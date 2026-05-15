import re

from sqlalchemy import func, select

from extensions import db
from app.exceptions import ConflictError, NotFoundError, ValidationError

_PROJECT_CODE_RE = re.compile(r'^[A-Z]{2,6}$')


def generate_project_code(project_code: str) -> str:
    """校验人工输入的项目代号（Phase 1）。Phase 2+ 将在本文件追加治具编码自动生成函数。

    规则：
      - 格式：^[A-Z]{2,6}$（2-6 位全大写字母）
      - 唯一性：全局唯一，重复则抛 ConflictError

    Returns: 校验通过的 project_code（原值返回）
    Raises:
      ValidationError — 格式不合规
      ConflictError   — 编码已存在
    """
    if not _PROJECT_CODE_RE.match(project_code or ''):
        raise ValidationError(
            'project_code 格式不合规（须匹配 ^[A-Z]{2,6}$）',
            field='project_code',
        )

    from app.models.project import Project  # 函数内 import，避免循环依赖
    stmt = select(Project).where(Project.project_code == project_code)
    if db.session.execute(stmt).scalar_one_or_none() is not None:
        raise ConflictError('project_code 已存在')

    return project_code


def generate_fixture_code(project_code: str, fixture_type_code: str, version_code: str = 'A1') -> str:
    """生成治具编码，格式：[项目代号]-[治具型号代号]#[套号]-[版本号]
    示例：EGL-FB-YN#1-A1

    Args:
        project_code: 项目代号，如 'EGL'
        fixture_type_code: 治具型号代号，如 'FB-YN'
        version_code: 图纸版本号，默认 'A1'；加开-复制场景由调用方传入源治具当前版本

    Returns:
        str: 完整治具编码

    Raises:
        NotFoundError: 项目不存在
        ValidationError: 项目已作废

    Note:
        套号从 1 起连续递增，按同项目 + 同治具型号统计现有记录数 + 1。
        并发安全由 fixture_code UNIQUE 约束兜底，调用方需处理 IntegrityError。
    """
    from app.models.project import Project  # 函数内 import，避免循环依赖
    from app.models.fixture import Fixture

    # 查出项目
    project_stmt = select(Project).where(Project.project_code == project_code)
    project = db.session.execute(project_stmt).scalar_one_or_none()
    if project is None:
        raise NotFoundError(f"项目 {project_code} 不存在")
    if project.status == 'cancelled':
        raise ValidationError(f"项目 {project_code} 已作废，不可新建治具")

    # 统计同项目 + 同型号已有记录数，计算套号
    count_stmt = select(func.count()).select_from(Fixture).where(
        Fixture.project_id == project.id,
        Fixture.fixture_type_code == fixture_type_code,
    )
    existing_count = db.session.execute(count_stmt).scalar()

    # 并发安全说明：
    # 套号基于 COUNT 查询生成，存在极低概率的并发竞争（两请求同时查到相同 existing_count）。
    # 兜底依赖 fixtures.fixture_code 的 UNIQUE 约束：
    # 调用方（fixture_service.create_fixture）在 db.session.commit() 时若捕获 IntegrityError，
    # 应重新调用本函数一次（重新计算套号）或抛 ConflictError(409) 提示前端刷新重试。
    set_no = existing_count + 1
    return f"{project_code}-{fixture_type_code}#{set_no}-{version_code}"
