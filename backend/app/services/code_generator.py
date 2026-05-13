import re

from app.exceptions import ConflictError, ValidationError

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
    if Project.query.filter_by(project_code=project_code).first():
        raise ConflictError('project_code 已存在')

    return project_code
