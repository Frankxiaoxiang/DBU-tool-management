from functools import wraps
from flask_jwt_extended import verify_jwt_in_request, get_jwt, get_jwt_identity
from app.exceptions import ForbiddenError


def require_role(*allowed_roles):
    """
    用法：@require_role('super_admin', 'pm')  — 任一角色命中即放行。
    角色列表从 JWT additional_claims['role_codes'] 读取，避免每次请求查 DB。
    """
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            verify_jwt_in_request()
            user_id = int(get_jwt_identity())  # Rule 4: 必须强转 int
            claims = get_jwt()
            user_role_codes = set(claims.get('role_codes', []))
            if not user_role_codes & set(allowed_roles):
                raise ForbiddenError()
            return fn(*args, **kwargs)
        return wrapper
    return decorator
