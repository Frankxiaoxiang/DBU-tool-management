from werkzeug.security import generate_password_hash, check_password_hash
from app.models import User


def get_user_by_username(username):
    return User.query.filter_by(username=username, is_active=True).first()


def verify_password(user, password):
    return check_password_hash(user.password_hash, password)


def make_password_hash(password):
    return generate_password_hash(password)
