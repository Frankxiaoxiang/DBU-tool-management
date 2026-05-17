import os
import logging
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask
from sqlalchemy.orm.exc import StaleDataError

# ★ 关键顺序：先加载 .env 填充 os.environ，再 import config
#   config.py 的 Config 类体在 import 时执行 os.environ.get()；
#   若 load_dotenv 放在 create_app() 内部，类体早已求值完毕，DATABASE_URL 永远 None
_pre_env = os.environ.get('FLASK_ENV', 'development')
load_dotenv(Path(__file__).resolve().parent.parent / f'.env.{_pre_env}')

from config import CONFIG_MAP  # noqa: E402 — must be after load_dotenv
from extensions import db, migrate, jwt, scheduler  # noqa: E402


def create_app(config_name=None):
    env = config_name or os.environ.get('FLASK_ENV', 'development')

    app = Flask(__name__)

    # ① 加载 Config 类
    config_class = CONFIG_MAP.get(env, CONFIG_MAP['development'])
    app.config.from_object(config_class)

    # ② 日志：TimedRotatingFileHandler 按天切割，保留 30 天
    log_dir = Path(os.environ.get('LOG_DIR', './logs'))
    if not log_dir.is_absolute():
        log_dir = Path(app.root_path).parent / log_dir
    log_dir.mkdir(parents=True, exist_ok=True)

    file_handler = TimedRotatingFileHandler(
        filename=str(log_dir / 'app.log'),
        when='midnight',
        backupCount=30,
        encoding='utf-8',
    )
    file_handler.setFormatter(logging.Formatter(
        '[%(asctime)s] %(levelname)s in %(module)s: %(message)s'
    ))
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.setLevel(logging.INFO)

    # ③ 初始化扩展（顺序不可变）
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    scheduler.init_app(app)

    # ④ 注册 Models（必须在 db.init_app 之后，确保 Alembic 能扫到 metadata）
    from app import models  # noqa: F401

    # ⑤ 注册 Blueprint（prefix 只在此处加，Blueprint 定义处不带）
    from app.blueprints.auth import auth_bp
    app.register_blueprint(auth_bp, url_prefix='/api/auth')

    from app.blueprints.projects import projects_bp
    app.register_blueprint(projects_bp, url_prefix='/api/projects')

    from app.blueprints.batches import batch_bp
    app.register_blueprint(batch_bp, url_prefix='/api/batches')

    from app.blueprints.fixtures import fixtures_bp
    app.register_blueprint(fixtures_bp, url_prefix='/api/fixtures')

    from app.blueprints.files import files_bp
    app.register_blueprint(files_bp, url_prefix='/api/files')

    from app.blueprints.drawings import drawings_bp
    app.register_blueprint(drawings_bp, url_prefix='/api/drawings')

    from app.blueprints.purchase_requisitions import purchase_requisitions_bp
    app.register_blueprint(purchase_requisitions_bp, url_prefix='/api/purchase-requisitions')

    # ⑥ 全局 errorhandler
    _register_error_handlers(app)

    # ⑦ APScheduler：debug 模式下只在 Werkzeug reloader 子进程里启动，避免双启
    if not app.debug or os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
        scheduler.start()

    # ⑧ CLI 命令
    from scripts.seed_data import seed_command
    app.cli.add_command(seed_command)

    app.logger.info('App created, env=%s', env)
    return app


def _register_error_handlers(app):
    from app.exceptions import ConflictError, ForbiddenError, ValidationError, NotFoundError
    from app.utils.response import error_response

    @app.errorhandler(StaleDataError)
    def handle_stale_data(err):
        return error_response('数据已被其他请求修改，请刷新后重试', 409)

    @app.errorhandler(ConflictError)
    def handle_conflict(err):
        kwargs = {'data': err.data} if getattr(err, 'data', None) else {}
        return error_response(err.message, 409, **kwargs)

    @app.errorhandler(ValidationError)
    def handle_validation(err):
        return error_response(err.message, 400, field=err.field)

    @app.errorhandler(ForbiddenError)
    def handle_forbidden(err):
        return error_response(err.message, 403)

    @app.errorhandler(NotFoundError)
    def handle_not_found(err):
        return error_response(err.message, 404)

    # JWT 错误回调（统一返回 JSON，避免 HTML 默认响应）
    @jwt.invalid_token_loader
    def invalid_token_callback(reason):
        return error_response('无效的 Token', 401)

    @jwt.expired_token_loader
    def expired_token_callback(jwt_header, jwt_data):
        return error_response('Token 已过期，请重新登录', 401)

    @jwt.unauthorized_loader
    def missing_token_callback(reason):
        return error_response('缺少认证 Token', 401)

    @jwt.revoked_token_loader
    def revoked_token_callback(jwt_header, jwt_data):
        return error_response('Token 已失效', 401)
