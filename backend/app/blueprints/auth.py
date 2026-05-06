import logging
from flask import Blueprint, request
from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    jwt_required,
    get_jwt_identity,
    get_jwt,
)
from app.exceptions import ValidationError, NotFoundError
from app.utils.response import success_response
from app.models import User
from app.services.auth_service import get_user_by_username, verify_password

logger = logging.getLogger(__name__)

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/login', methods=['POST'])
def login():
    body = request.get_json(silent=True) or {}
    username = (body.get('username') or '').strip()
    password = body.get('password') or ''
    if not username or not password:
        raise ValidationError('username 和 password 为必填项')

    user = get_user_by_username(username)
    if not user or not verify_password(user, password):
        raise ValidationError('用户名或密码错误')

    role_codes = [r.code for r in user.roles]
    claims = {'role_codes': role_codes}
    access_token = create_access_token(identity=str(user.id), additional_claims=claims)
    refresh_token = create_refresh_token(identity=str(user.id), additional_claims=claims)

    return success_response({
        'access_token': access_token,
        'refresh_token': refresh_token,
        'user': {
            'id': user.id,
            'username': user.username,
            'full_name': user.full_name,
            'role_code': role_codes[0] if role_codes else None,
        },
    })


@auth_bp.route('/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh():
    user_id = int(get_jwt_identity())  # Rule 4
    claims = get_jwt()
    role_codes = claims.get('role_codes', [])
    access_token = create_access_token(
        identity=str(user_id),
        additional_claims={'role_codes': role_codes},
    )
    return success_response({'access_token': access_token})


@auth_bp.route('/logout', methods=['POST'])
@jwt_required()
def logout():
    user_id = int(get_jwt_identity())  # Rule 4
    logger.info('User %s logged out', user_id)
    return success_response(message='已登出')


@auth_bp.route('/me', methods=['GET'])
@jwt_required()
def me():
    user_id = int(get_jwt_identity())  # Rule 4
    user = User.query.get(user_id)
    if not user or not user.is_active:
        raise NotFoundError('用户不存在或已停用')
    role_codes = [r.code for r in user.roles]
    return success_response({
        'id': user.id,
        'username': user.username,
        'full_name': user.full_name,
        'email': user.email,
        'role_code': role_codes[0] if role_codes else None,
    })
