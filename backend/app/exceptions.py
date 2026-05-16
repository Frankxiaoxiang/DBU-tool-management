class ConflictError(Exception):
    def __init__(self, message='数据冲突或版本已过期', data=None):
        self.message = message
        self.data = data
        super().__init__(message)


class ForbiddenError(Exception):
    def __init__(self, message='权限不足'):
        self.message = message
        super().__init__(message)


class ValidationError(Exception):
    def __init__(self, message, field=None):
        self.message = message
        self.field = field
        super().__init__(message)


class NotFoundError(Exception):
    def __init__(self, message='资源不存在'):
        self.message = message
        super().__init__(message)
