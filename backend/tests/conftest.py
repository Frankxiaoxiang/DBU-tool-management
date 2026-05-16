from pathlib import Path
import pytest
from dotenv import load_dotenv
from sqlalchemy.orm import sessionmaker, scoped_session
from flask_jwt_extended import create_access_token
from werkzeug.security import generate_password_hash

# 必须在 create_app 之前：TestingConfig 类体在 import 时求值 os.environ.get('TEST_DATABASE_URL')
load_dotenv(Path(__file__).resolve().parent.parent.parent / '.env.testing', override=True)

from app import create_app        # noqa: E402
from extensions import db, scheduler         # noqa: E402
from app.models.user import User  # noqa: E402
from app.models.role import Role  # noqa: E402
from app.models.project import Project  # noqa: E402
from app.models.batch import Batch  # noqa: E402
from app.models.fixture_template import FixtureTemplate  # noqa: E402
from app.models.fixture_template_snapshot import FixtureTemplateSnapshot  # noqa: E402
from app.models.fixture import Fixture  # noqa: E402


# ---------------------------------------------------------------------------
# 会话级 fixture：建表一次，会话结束后 drop
# ---------------------------------------------------------------------------

@pytest.fixture(scope='session')
def app():
    application = create_app('testing')
    with application.app_context():
        db.create_all()
    yield application
    try:
        scheduler.shutdown(wait=False)
    except Exception:
        pass
    with application.app_context():
        db.drop_all()


# ---------------------------------------------------------------------------
# 函数级事务隔离：connection-level transaction + nested savepoint
# Service 内的 db.session.commit() 只释放 savepoint，外层 transaction 在用例结束后 rollback
# ---------------------------------------------------------------------------

@pytest.fixture(scope='function')
def db_session(app):
    with app.app_context():
        connection = db.engine.connect()
        transaction = connection.begin()
        _original_session = db.session
        db.session = scoped_session(
            sessionmaker(
                bind=connection,
                join_transaction_mode='create_savepoint',
            )
        )
        try:
            yield db.session
        finally:
            db.session.remove()
            db.session = _original_session
            transaction.rollback()
            connection.close()


@pytest.fixture(scope='function')
def client(app, db_session):
    return app.test_client()


# ---------------------------------------------------------------------------
# 种子数据 fixtures（每个用例独立，事务 rollback 后自动还原）
# ---------------------------------------------------------------------------

@pytest.fixture
def seeded_pm_user(db_session):
    role = Role(code='pm', name='项目经理')
    db_session.add(role)
    db_session.flush()
    user = User(
        username='pm_test',
        password_hash=generate_password_hash('Test1234!'),
        full_name='测试PM',
        email='pm@test.com',
        is_active=True,
    )
    user.roles.append(role)
    db_session.add(user)
    db_session.flush()
    return user


@pytest.fixture
def seeded_iqc_user(db_session):
    role = Role(code='iqc', name='IQC检验员')
    db_session.add(role)
    db_session.flush()
    user = User(
        username='iqc_test',
        password_hash=generate_password_hash('Test1234!'),
        full_name='测试IQC',
        email='iqc@test.com',
        is_active=True,
    )
    user.roles.append(role)
    db_session.add(user)
    db_session.flush()
    return user


@pytest.fixture
def seeded_super_admin_user(db_session):
    role = Role(code='super_admin', name='超级管理员')
    db_session.add(role)
    db_session.flush()
    user = User(
        username='super_test',
        password_hash=generate_password_hash('Test1234!'),
        full_name='超级管理员',
        email='super@test.com',
        is_active=True,
    )
    user.roles.append(role)
    db_session.add(user)
    db_session.flush()
    return user


@pytest.fixture
def seeded_project(db_session, seeded_pm_user):
    project = Project(
        project_code='SEED',
        project_name='种子项目',
        product_type='SUS_VC',
        project_owner_id=seeded_pm_user.id,
        status='active',
        created_by=seeded_pm_user.id,
        version=0,
    )
    db_session.add(project)
    db_session.flush()
    return project


@pytest.fixture
def seeded_templates(db_session):
    """工厂 fixture：向 fixture_templates 插入测试模板，返回列表。
    计数器保证同一测试内多次调用时 code 唯一。
    is_active=True 为默认，测试内如需 False 可直接修改后 flush。
    """
    _counter = [0]

    def _factory(product_type='SUS_VC', count=5):
        templates = []
        for _ in range(count):
            t = FixtureTemplate(
                code=f'TST-{_counter[0]:04d}',
                name=f'测试模板 {_counter[0]:04d}',
                process_step='测试工序',
                applicable_products=product_type,
                default_lt_days=30,
                is_attachment=False,
                is_active=True,
            )
            db_session.add(t)
            templates.append(t)
            _counter[0] += 1
        db_session.flush()
        return templates

    return _factory


@pytest.fixture
def seeded_project_with_snapshot(db_session, seeded_pm_user, seeded_templates):
    """激活态项目，附带 1 条 FixtureTemplateSnapshot 记录（供批次创建的快照前置校验使用）。"""
    project = Project(
        project_code='SNAP',
        project_name='有快照项目',
        product_type='SUS_VC',
        project_owner_id=seeded_pm_user.id,
        status='active',
        created_by=seeded_pm_user.id,
        version=0,
    )
    db_session.add(project)
    db_session.flush()
    templates = seeded_templates(product_type='SUS_VC', count=1)
    template = templates[0]
    snapshot = FixtureTemplateSnapshot(
        project_id=project.id,
        source_template_id=template.id,
        fixture_type_code=template.code,
        product_type=template.applicable_products,
        synced_by=seeded_pm_user.id,
    )
    db_session.add(snapshot)
    db_session.flush()
    return project


@pytest.fixture
def seeded_manual_batch(db_session, seeded_project_with_snapshot, seeded_pm_user):
    """seeded_project_with_snapshot 下的 manual_init 批次（status='draft'，直接插 Model 跳过 service）。"""
    batch = Batch(
        project_id=seeded_project_with_snapshot.id,
        batch_no=f'{seeded_project_with_snapshot.project_code}-M0-1',
        batch_type='manual_init',
        flow_path='full',
        status='draft',
        created_by=seeded_pm_user.id,
        version=0,
    )
    db_session.add(batch)
    db_session.flush()
    return batch


@pytest.fixture
def make_fixture(db_session, seeded_pm_user, seeded_manual_batch):
    """
    治具测试数据工厂。
    current_status 直接构造时传入（合法的测试数据初始化，非业务流转）。
    """
    created = []

    def _factory(current_status='pending_iqc', **kwargs):
        f = Fixture(
            fixture_code=f"TEST-FB-YN#1-A1-{len(created)}",
            batch_id=seeded_manual_batch.id,
            project_id=seeded_manual_batch.project_id,
            fixture_type_code='FB-YN',
            set_no=len(created) + 1,
            current_version_code='A1',
            current_status=current_status,
            status='active',
            version=0,
            created_by=seeded_pm_user.id,
            **kwargs
        )
        db_session.add(f)
        db_session.flush()
        created.append(f)
        return f

    return _factory


@pytest.fixture
def seeded_warehouse_user(db_session):
    role = Role(code='warehouse', name='仓库管理员')
    db_session.add(role)
    db_session.flush()
    user = User(
        username='warehouse_test',
        password_hash=generate_password_hash('Test1234!'),
        full_name='测试仓库',
        email='warehouse@test.com',
        is_active=True,
    )
    user.roles.append(role)
    db_session.add(user)
    db_session.flush()
    return user


@pytest.fixture
def seeded_design_engineer_user(db_session):
    role = Role(code='design_engineer', name='设计工程师')
    db_session.add(role)
    db_session.flush()
    user = User(
        username='de_test',
        password_hash=generate_password_hash('Test1234!'),
        full_name='测试设计师',
        email='de@test.com',
        is_active=True,
    )
    user.roles.append(role)
    db_session.add(user)
    db_session.flush()
    return user


@pytest.fixture
def auth_headers(seeded_pm_user, seeded_iqc_user, seeded_super_admin_user,
                 seeded_warehouse_user, seeded_design_engineer_user):
    """各角色 JWT headers；additional_claims 必须含 role_codes，与 require_role 装饰器对齐。"""
    return {
        'pm': {
            'Authorization': 'Bearer ' + create_access_token(
                identity=str(seeded_pm_user.id),
                additional_claims={'role_codes': ['pm']},
            ),
        },
        'iqc': {
            'Authorization': 'Bearer ' + create_access_token(
                identity=str(seeded_iqc_user.id),
                additional_claims={'role_codes': ['iqc']},
            ),
        },
        'super_admin': {
            'Authorization': 'Bearer ' + create_access_token(
                identity=str(seeded_super_admin_user.id),
                additional_claims={'role_codes': ['super_admin']},
            ),
        },
        'warehouse': {
            'Authorization': 'Bearer ' + create_access_token(
                identity=str(seeded_warehouse_user.id),
                additional_claims={'role_codes': ['warehouse']},
            ),
        },
        'design_engineer': {
            'Authorization': 'Bearer ' + create_access_token(
                identity=str(seeded_design_engineer_user.id),
                additional_claims={'role_codes': ['design_engineer']},
            ),
        },
    }


# ---------------------------------------------------------------------------
# Phase 2 Step 2-6-2 — fixture service 测试所需种子数据
# ---------------------------------------------------------------------------

@pytest.fixture
def seeded_batch(seeded_manual_batch):
    """seeded_manual_batch 的别名（manual_init, status=draft）。"""
    return seeded_manual_batch


@pytest.fixture
def seeded_fixture(db_session, seeded_batch, seeded_pm_user):
    """seeded_batch 下的治具（version_code=A1, status=pending_iqc）。"""
    f = Fixture(
        fixture_code='SNAP-FB-YN#1-A1',
        batch_id=seeded_batch.id,
        project_id=seeded_batch.project_id,
        fixture_type_code='FB-YN',
        set_no=1,
        current_version_code='A1',
        current_status='pending_iqc',
        status='active',
        version=0,
        created_by=seeded_pm_user.id,
    )
    db_session.add(f)
    db_session.flush()
    return f


@pytest.fixture
def seeded_fixture_a3(db_session, seeded_batch, seeded_pm_user):
    """seeded_batch 下的治具（version_code=A3，供 A3→B1 版本升级用例使用）。"""
    f = Fixture(
        fixture_code='SNAP-FB-YN#2-A3',
        batch_id=seeded_batch.id,
        project_id=seeded_batch.project_id,
        fixture_type_code='FB-YN',
        set_no=2,
        current_version_code='A3',
        current_status='pending_iqc',
        status='active',
        version=0,
        created_by=seeded_pm_user.id,
    )
    db_session.add(f)
    db_session.flush()
    return f


@pytest.fixture
def seeded_mass_prod_batch(db_session, seeded_project_with_snapshot, seeded_pm_user):
    """同项目 mass_prod 批次（status=in_progress），供 seal_batch 前置校验使用。"""
    batch = Batch(
        project_id=seeded_project_with_snapshot.id,
        batch_no=f'{seeded_project_with_snapshot.project_code}-MP-1',
        batch_type='mass_prod',
        flow_path='full',
        status='in_progress',
        created_by=seeded_pm_user.id,
        version=0,
    )
    db_session.add(batch)
    db_session.flush()
    return batch


@pytest.fixture
def seeded_target_batch(db_session, seeded_project_with_snapshot, seeded_pm_user):
    """同项目第二个 manual_init 批次，供 copy_to_batch 目标批次使用。"""
    batch = Batch(
        project_id=seeded_project_with_snapshot.id,
        batch_no=f'{seeded_project_with_snapshot.project_code}-M0-2',
        batch_type='manual_init',
        flow_path='full',
        status='draft',
        created_by=seeded_pm_user.id,
        version=0,
    )
    db_session.add(batch)
    db_session.flush()
    return batch


@pytest.fixture
def seeded_cross_project_batch(db_session, seeded_pm_user):
    """跨项目批次（不同 project），用于 copy_to_batch 跨项目 400 用例。"""
    other_project = Project(
        project_code='XPRJ',
        project_name='跨项目测试',
        product_type='SUS_VC',
        project_owner_id=seeded_pm_user.id,
        status='active',
        created_by=seeded_pm_user.id,
        version=0,
    )
    db_session.add(other_project)
    db_session.flush()
    batch = Batch(
        project_id=other_project.id,
        batch_no='XPRJ-M0-1',
        batch_type='manual_init',
        flow_path='full',
        status='draft',
        created_by=seeded_pm_user.id,
        version=0,
    )
    db_session.add(batch)
    db_session.flush()
    return batch
