# DBU 模治具管理系统 — 系统架构设计方案 V1.4

> 配套文档:《DBU模治具全流程管控文件 V2.1》、《DBU模治具编码规则 V1.0》、《CLAUDE_reference_for_opus.md》
>
> 设计原则:**清晰分层 · 模块独立 · 可维护性优先 · 复杂度可控 · 兼容 Claude Code CLI 协作开发**
>
> **本版核心变更:基于第三轮(最终)审阅 8 处底层与机制修正。** 涉及乐观锁机制重新校准、状态机 reject 漏洞修复、告警事务隔离、连接池假死防护、生产日志切割、Waitress 调优、前端时区强校验、开发铁律文档化。详见末尾「修订记录」。
>
> **本版作为开发启动前的最终架构基线。**

---

## 一、整体架构设计

### 1.1 架构模式选择

| 维度 | 选择 | 理由 |
|------|------|------|
| 后端形态 | 单体 Flask(Modular Monolith) | 50 人内部使用、局域网部署,微服务过度设计 |
| 前端形态 | Vue 3 SPA + Element Plus | 与现有 vc-cost-system 一致 |
| 通信协议 | RESTful JSON over HTTP | 与现有规范一致 |
| 部署形态 | 混合部署(开发 Docker MySQL + 生产 Windows Server 原生) | 匹配开发者已有部署经验 |
| 生产 WSGI | **Waitress (threads=32, max_request_body_size=500MB)** | **★ V1.4 调优** |
| 认证 | JWT(Flask-JWT-Extended) | 与现有规范一致 |
| 异步任务 | Flask-APScheduler 内嵌 | 单进程 Waitress 无并发陷阱 |
| **并发控制** | **仅手动乐观锁 + 全局 StaleDataError 兜底** | **★ V1.4 修订:剥离 ORM 自动版** |

### 1.2 前后端职责划分

```
┌──────────────────────────┐         ┌─────────────────────────────┐
│       前端 (Vue 3)        │         │      后端 (Flask)            │
├──────────────────────────┤         ├─────────────────────────────┤
│ · 页面渲染、表单校验       │         │ · 业务逻辑(services/)        │
│ · 路由守卫、按钮级权限     │ ──API─▶ │ · 状态机校验(无 force 后门)  │
│ · 数据可视化(甘特图/导出) │ ◀─JSON─ │ · 审批流流转                 │
│ · 文件上传(multipart)     │         │ · 编码自动生成               │
│ · ★ 时间用 dayjs.tz(str)  │         │ · 权限校验(最终防线)         │
│   而非 dayjs(str)         │         │ · 文件落盘 / 大报表流式生成   │
│                          │         │ · 计划日期推算               │
│                          │         │ · 邮件告警(事务隔离)         │
└──────────────────────────┘         └─────────────────────────────┘
```

**铁律:前端权限只用于"隐藏不该看到的按钮和菜单",后端必须独立做权限校验。**

### 1.3 混合部署方案

#### 部署形态总览

```
┌─────────────────────────────────────────┐    ┌──────────────────────────────────────┐
│ 本地开发机 (ThinkPad, Windows 11)        │    │ 公司服务器 (Windows Server)           │
├─────────────────────────────────────────┤    ├──────────────────────────────────────┤
│ ① Vue Dev Server (pnpm dev:5173)        │    │ ① Vue 静态文件 (dist/)               │
│ ② Flask Dev (python run.py:5000)        │    │ ② Flask + Waitress (NSSM 服务)       │
│ ③ MySQL (Docker, +08:00 时区)           │    │ ③ MySQL (Windows 原生)               │
│ ④ APScheduler 内嵌                      │    │ ④ APScheduler 内嵌                   │
└─────────────────────────────────────────┘    └──────────────────────────────────────┘
```

#### 开发环境

```bash
# Docker MySQL
docker run -d --name dbu-mysql-dev \
  -e MYSQL_ROOT_PASSWORD=devpassword \
  -e MYSQL_DATABASE=dbu_fixture \
  -p 3306:3306 \
  -v dbu_mysql_data:/var/lib/mysql \
  mysql:8.4 \
  --character-set-server=utf8mb4 \
  --collation-server=utf8mb4_unicode_ci \
  --default-time-zone='+08:00'

# Flask
cd backend && python -m venv venv && .\venv\Scripts\activate
pip install -r requirements.txt
python run.py

# Vue
cd frontend && pnpm install && pnpm dev
```

`vite.config.js` API 代理:

```javascript
export default defineConfig({
  server: {
    port: 5173,
    proxy: {
      '/api':     { target: 'http://localhost:5000', changeOrigin: true },
      '/uploads': { target: 'http://localhost:5000', changeOrigin: true },
    }
  }
})
```

#### 生产环境(Windows Server)

| 组件 | 安装方式 | 路径 / 端口 |
|------|----------|------------|
| Python 3.12 | 官方 Installer | `C:\Python312\` |
| MySQL 8.4 | MySQL Installer | `localhost:3306` |
| Flask 应用 | Git clone → venv → pip install | `C:\dbu\backend\` |
| Waitress | pip 安装 | `0.0.0.0:5000` |
| Vue 静态文件 | `pnpm build` 后拷贝 | `C:\dbu\frontend\dist\` |
| 附件目录 | 手动创建 | `D:\dbu\uploads\` |
| 日志目录 | 手动创建 | `D:\dbu\logs\` |
| 备份目录 | 手动创建 | `D:\dbu\backup\` |

**[V1.4 修订] Waitress 启动配置:**

```python
# backend/serve.py
from waitress import serve
from app import create_app
import os

os.environ.setdefault('FLASK_ENV', 'production')
app = create_app()

if __name__ == '__main__':
    serve(
        app,
        host='0.0.0.0',
        port=5000,
        threads=32,                              # ★ V1.4 由 8 提至 32(I/O 密集型友好)
        max_request_body_size=536870912,         # ★ V1.4 防御底线:500MB
        channel_timeout=120,                     # 慢客户端超时
        cleanup_interval=30,                     # 通道清理间隔
    )
```

**Vue 静态文件 serve(MVP 方案):** Flask 通过 `static_folder` 直接 serve(详见 V1.3 第 1.3 节,本版未修改)。

**NSSM 注册为 Windows 服务:**

```powershell
nssm install DBU-Fixture-Backend "C:\Python312\python.exe" "C:\dbu\backend\serve.py"
nssm set DBU-Fixture-Backend AppDirectory "C:\dbu\backend"
# ★ V1.4:NSSM 仅做兜底输出捕获,不再依赖其作为主日志方案
nssm set DBU-Fixture-Backend AppStdout "D:\dbu\logs\nssm_stdout.log"
nssm set DBU-Fixture-Backend AppStderr "D:\dbu\logs\nssm_stderr.log"
nssm set DBU-Fixture-Backend AppRotateFiles 1
nssm set DBU-Fixture-Backend AppRotateBytes 10485760    # 10MB 切割
nssm start DBU-Fixture-Backend
```

#### 配置管理(python-dotenv)

```python
# backend/app/config.py
import os
from pathlib import Path
from dotenv import load_dotenv
from datetime import timedelta

env = os.environ.get('FLASK_ENV', 'development')
env_file = Path(__file__).parent.parent / f'.env.{env}'
load_dotenv(env_file)

class Config:
    SQLALCHEMY_DATABASE_URI = os.environ['DATABASE_URL']

    # ★ V1.4 关键修订:连接池防假死
    SQLALCHEMY_ENGINE_OPTIONS = {
        "connect_args": {"init_command": "SET time_zone='+08:00'"},
        "pool_pre_ping": True,                # 用前测活
        "pool_recycle": 3600,                 # ★ V1.4 新增:每小时主动回收,防 wait_timeout 断开
        "pool_size": 10,
        "max_overflow": 20,
    }

    JWT_SECRET_KEY = os.environ['JWT_SECRET']
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=8)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=7)

    UPLOAD_BASE = os.environ.get('UPLOAD_BASE', './uploads')
    UPLOAD_MAX_SIZE = 0                       # 业务无限制
    UPLOAD_ALLOWED_EXT = {'jpg','jpeg','png','pdf','heic','mp4','mov'}

    LOG_DIR = os.environ.get('LOG_DIR', './logs')
    LOG_BACKUP_COUNT = 30                     # ★ V1.4 新增:日志保留 30 天

    MAIL_SERVER = os.environ['SMTP_HOST']
    MAIL_PORT = int(os.environ.get('SMTP_PORT', 25))

    SCHEDULER_TIMEZONE = 'Asia/Shanghai'
```

#### 时区处理

- **生产**:Windows Server → MySQL Windows 自动继承,无需特殊配置
- **开发**:Docker MySQL 启动时 `--default-time-zone='+08:00'` + 连接串 `init_command` 双保险
- **APScheduler**:实例化时显式 `timezone='Asia/Shanghai'`(唯一需注意)
- **前端**:见 4.5 节,`dayjs.tz(str)` 强制规范

### 1.4 备份与还原策略

(同 V1.3,Windows 任务计划程序 + mysqldump.exe + robocopy,详见 docs/06)

### 1.5 [V1.4 新增] 日志切割策略

**问题:** Windows 不支持对被占用文件无缝切割,NSSM 的 AppStdout 重定向会让单体日志膨胀到几十 GB。

**方案:** Flask 在 `create_app()` 中配置原生 `TimedRotatingFileHandler`,按天切割保留 30 天:

```python
# app/__init__.py 中的 configure_logging()
import logging
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path

def configure_logging(app):
    log_dir = Path(app.config['LOG_DIR'])
    log_dir.mkdir(parents=True, exist_ok=True)

    handler = TimedRotatingFileHandler(
        filename=log_dir / 'app.log',
        when='midnight',
        interval=1,
        backupCount=app.config['LOG_BACKUP_COUNT'],   # 30 天
        encoding='utf-8',
        utc=False,                                    # 用本地时间命名 app.log.2026-04-26
    )
    handler.setFormatter(logging.Formatter(
        '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
    ))
    handler.setLevel(logging.INFO)

    app.logger.addHandler(handler)
    app.logger.setLevel(logging.INFO)

    # SQLAlchemy 日志单独控制(默认 WARN 即可,DEBUG 时再开)
    logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)

    # APScheduler 日志
    logging.getLogger('apscheduler').setLevel(logging.INFO)
```

**结果:** `D:\dbu\logs\` 下每天产生 `app.log` + 历史文件 `app.log.2026-04-25` 等,超过 30 天自动删除。NSSM 的 stdout/stderr 仅作为兜底(配合 NSSM 自身的 AppRotateBytes 10MB 切割)。

---

## 二、数据库设计方案(基于 MySQL 8.4)

> 本章节相对 V1.3 的实质变更:**Model 定义中删除所有 `__mapper_args__ = {'version_id_col': version}`**(详见 2.9)。其他 DDL 完全一致。

### 2.1 核心数据表清单(共 27 张)

(同 V1.3,完整列表参考 V1.3 文档 2.1 节)

#### 核心约束:禁止物理删除(保留)

- `projects` / `batches` / `fixtures` / `purchase_orders` 等核心表禁止 HTTP DELETE
- 作废走 `status='cancelled'` 或状态机 SCRAPPED
- 配置型(users/suppliers/templates) 走 `is_active=FALSE`
- 真·删除仅 `scripts/reset_db.py` 提供

### 2.2 核心 ER 关系图

(同 V1.3)

### 2.3 三层数据结构核心字段 [V1.4 修订:删除 __mapper_args__]

#### `projects` — 项目主表

```sql
CREATE TABLE projects (
  id              BIGINT PRIMARY KEY AUTO_INCREMENT,
  project_code    VARCHAR(10) UNIQUE NOT NULL,
  project_name    VARCHAR(100) NOT NULL,
  product_type    ENUM('SUS_VC','CU_VC','HP') NOT NULL,
  project_owner_id BIGINT NOT NULL,
  status          VARCHAR(16) NOT NULL DEFAULT 'active',  -- 按全系统约定改用 VARCHAR(16)，不使用 ENUM，Service 层校验合法值
  cancelled_reason TEXT NULL,
  cancelled_at    DATETIME NULL,
  cancelled_by    BIGINT NULL,
  created_by      BIGINT NOT NULL,
  created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  version         INT DEFAULT 0,
  INDEX idx_owner (project_owner_id),
  INDEX idx_product_type (product_type),
  INDEX idx_status (status),
  CONSTRAINT fk_proj_owner FOREIGN KEY (project_owner_id) REFERENCES users(id)
)
ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

```python
# app/models/project.py — V1.4 关键修订
class Project(db.Model):
    __tablename__ = 'projects'
    __table_args__ = {'mysql_charset':'utf8mb4', 'mysql_collate':'utf8mb4_unicode_ci'}

    id = db.Column(db.BigInteger, primary_key=True)
    project_code = db.Column(db.String(10), unique=True, nullable=False)
    # ... 其他字段
    version = db.Column(db.Integer, nullable=False, default=0)

    # ★ V1.4 删除以下配置:
    # __mapper_args__ = {'version_id_col': version}     ← 不再使用 ORM 自动版
    # 改用 Service 层手动校验,见 2.9 节
```

#### `batches` 和 `fixtures`

#### fixtures — 治具主表

```sql
CREATE TABLE fixtures (
  id                    BIGINT PRIMARY KEY AUTO_INCREMENT,
  fixture_code          VARCHAR(32) UNIQUE NOT NULL,            -- 系统按编码规则生成，禁止前端拼接（§e.7）
  batch_id              BIGINT NOT NULL,
  project_id            BIGINT NOT NULL,                        -- 冗余字段，便于按项目过滤；与 batch.project_id 一致性由 Service 层保证
  fixture_type_code     VARCHAR(16) NOT NULL,                   -- 治具型号代号，如 FB-YN
  set_no                INT NOT NULL,                           -- 套号 #N 的 N，从 1 起连续递增（《编码规则 V1.0》§2.2）
  current_version_code  VARCHAR(8) NOT NULL DEFAULT 'A1',       -- 图纸版本 A1/A2/A3/B1…；不用 ENUM，Service 层校验
  current_status        VARCHAR(32) NOT NULL DEFAULT 'pending_iqc',  -- 12 状态机工艺流程；最长值 concession_accepted(19字符)，不用 ENUM（§e.4）
  parent_fixture_id     BIGINT NULL,                            -- 自引用；仅"加开-复制图纸"溯源（§e.7）
  supplier_id           BIGINT NULL,                            -- 采购前未定故可空
  lead_time_days        INT NULL,
  planned_arrival_date  DATE NULL,
  is_sealed             BOOLEAN NOT NULL DEFAULT FALSE,         -- 封存标志（§3.3.x）
  sealed_at             DATETIME NULL,
  sealed_by             BIGINT NULL,
  status                VARCHAR(16) NOT NULL DEFAULT 'active',  -- 行政作废（active/cancelled）；与 current_status 正交（Frank 2026-05-15 裁决）
  version               INT NOT NULL DEFAULT 0,                -- 手动乐观锁，不用 ORM 自动版（§e.5）
  created_by            BIGINT NOT NULL,
  created_at            DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at            DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX idx_batch   (batch_id),
  INDEX idx_project (project_id),
  INDEX idx_status  (current_status),
  INDEX idx_type    (fixture_type_code),
  INDEX idx_parent  (parent_fixture_id),
  CONSTRAINT fk_fix_batch     FOREIGN KEY (batch_id)           REFERENCES batches(id),
  CONSTRAINT fk_fix_project   FOREIGN KEY (project_id)         REFERENCES projects(id),
  CONSTRAINT fk_fix_parent    FOREIGN KEY (parent_fixture_id)  REFERENCES fixtures(id),
  CONSTRAINT fk_fix_supplier  FOREIGN KEY (supplier_id)        REFERENCES suppliers(id),
  CONSTRAINT fk_fix_sealed_by FOREIGN KEY (sealed_by)          REFERENCES users(id),
  CONSTRAINT fk_fix_created   FOREIGN KEY (created_by)         REFERENCES users(id)
)
ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

```python
# app/models/fixture.py
from extensions import db  # ★ 不得写 from app.extensions import db（§h 高频笔误）

class Fixture(db.Model):
    __tablename__ = 'fixtures'
    __table_args__ = {'mysql_charset': 'utf8mb4', 'mysql_collate': 'utf8mb4_unicode_ci'}

    id                   = db.Column(db.BigInteger, primary_key=True)
    fixture_code         = db.Column(db.String(32), unique=True, nullable=False)
    batch_id             = db.Column(db.BigInteger, db.ForeignKey('batches.id'), nullable=False)
    project_id           = db.Column(db.BigInteger, db.ForeignKey('projects.id'), nullable=False)
    fixture_type_code    = db.Column(db.String(16), nullable=False)
    set_no               = db.Column(db.Integer, nullable=False)
    current_version_code = db.Column(db.String(8), nullable=False, default='A1')
    current_status       = db.Column(db.String(32), nullable=False, default='pending_iqc')
    parent_fixture_id    = db.Column(db.BigInteger, db.ForeignKey('fixtures.id'), nullable=True)
    supplier_id          = db.Column(db.BigInteger, db.ForeignKey('suppliers.id'), nullable=True)
    lead_time_days       = db.Column(db.Integer, nullable=True)
    planned_arrival_date = db.Column(db.Date, nullable=True)
    is_sealed            = db.Column(db.Boolean, nullable=False, default=False)
    sealed_at            = db.Column(db.DateTime, nullable=True)
    sealed_by            = db.Column(db.BigInteger, db.ForeignKey('users.id'), nullable=True)
    status               = db.Column(db.String(16), nullable=False, default='active')
    version              = db.Column(db.Integer, nullable=False, default=0)
    created_by           = db.Column(db.BigInteger, db.ForeignKey('users.id'), nullable=False)
    created_at           = db.Column(db.DateTime, server_default=db.func.now())
    updated_at           = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now())

    # ★ 不加 __mapper_args__ = {'version_id_col': version}（§e.5 / CLAUDE.md §h）
```

`fixtures.parent_fixture_id` 仅用于"加开-复制图纸"场景;加开-加量复制时 `current_version_code` 继承源治具(业务规则)。

> **§2.3 修订记录**：V1.4 补写自 Phase 2 Step 2-0-1，Frank 2026-05-15 三项裁决落定（保留 `fixtures.status` 正交字段、不新建 `fixture_version_history` 表、`batch-seal` 纳入 Phase 2）。

### 2.4 — 2.8

(同 V1.3,无变更)

- 2.4 快照机制(复制型 + 追加同步)
- 2.5 状态机历史表
- 2.6 审批流数据模型
- 2.7 甘特图字段与计划日期推算
- 2.8 审计日志表

### 2.9 乐观锁 [V1.4 重大修订:仅手动校验]

#### 决策:删除 ORM 自动版,只保留手动校验

**原因(V1.4 纠偏):**

V1.1/V1.2 提出"双层乐观锁"是错误设计。SQLAlchemy 的 `version_id_col` 机制会在 UPDATE 时**自动递增 version 并加入 WHERE 子句**。如果 Service 层又手动 `version += 1`,SQLAlchemy 会生成 `SET version=N+2 WHERE version=N+1` 这种永远不匹配的 SQL,导致所有更新都报 StaleDataError。

**V1.4 最终方案:**

```python
# app/models/fixture.py
class Fixture(db.Model):
    __tablename__ = 'fixtures'
    # ...
    version = db.Column(db.Integer, nullable=False, default=0)

    # ★ 不要使用以下配置(V1.4 删除):
    # __mapper_args__ = {'version_id_col': version}
```

```python
# Service 层手动校验(主防线)
class FixtureService:
    @staticmethod
    def update(fixture_id, data, request_version, operator_id):
        fixture = Fixture.query.get_or_404(fixture_id)

        # ★ 唯一防线:Service 层比对 version
        if fixture.version != request_version:
            raise ConflictError(
                "Modified by another user. Please refresh.",
                code=409,
                server_version=fixture.version,
                your_version=request_version,
            )

        # 更新业务字段
        for key in ['planned_arrival_date', 'supplier_id', ...]:
            if key in data:
                setattr(fixture, key, data[key])

        # 手动递增 version
        fixture.version += 1
        db.session.commit()
        return fixture
```

```python
# 全局兜底(极端情况下仍可能由 SQLAlchemy 内部抛出)
from sqlalchemy.orm.exc import StaleDataError

@app.errorhandler(StaleDataError)
def handle_stale(e):
    app.logger.warning(f"StaleDataError caught at request level: {e}")
    return error_response("Conflict: please refresh", 409)

# ConflictError 自定义异常
@app.errorhandler(ConflictError)
def handle_conflict(e):
    return jsonify({
        'code': 409,
        'message': str(e),
        'data': {
            'server_version': e.server_version,
            'your_version': e.your_version,
        }
    }), 409
```

**为什么不用 ORM 自动版的好处也没了?**

- ORM 自动版的"防漏"价值在 V1.4 通过**单元测试 + Code Review + CLAUDE.md 铁律**保障
- 关键写入路径(fixture/project/batch)的 Service 层必须有 `assert request_version is not None` 守卫,在测试中验证

**API 约定:** 所有 PUT/PATCH 请求体必须包含 `version` 字段,前端从最近一次 GET 返回值带回。详见 docs/04_api_spec.md。

### 2.10 告警状态去重表

(同 V1.3)

### 2.11 采购订单一对多设计

(同 V1.3)

---

## 三、后端模块划分

### 3.1 目录结构

(同 V1.3,新增 docs/09_dev_rules.md)

```
backend/
├── docs/
│   ├── ...(同 V1.3)
│   └── 09_dev_rules.md             # ★ V1.4 新增:开发铁律
├── ...
```

### 3.2 核心 API 端点

(同 V1.3,无变更)

### 3.3 状态机核心逻辑 [V1.4 重构:消除 force=True 后门]

#### 三个职责清晰的函数

V1.4 将 V1.3 的 `transition(force=...)` 拆为三个独立函数,语义边界清晰:

| 函数 | 职责 | 校验 |
|------|------|------|
| `transition()` | 正常状态流转 | 严格走 TRANSITIONS,不可绕过 |
| `reject()` | 审批驳回回退 | 走 TRANSITIONS 内已配置的回退路径,严格校验 |
| `force_transition()` | 超管强制跳转 | **唯一**允许绕过 TRANSITIONS 的入口,必须填原因 + 写审计日志 |

#### 完整代码

```python
# app/utils/enums.py
class FixtureStatus:
    PENDING_IQC          = 'pending_iqc'
    IQC_INSPECTING       = 'iqc_inspecting'
    EMERGENCY_PENDING    = 'emergency_pending'
    CONCESSION_ACCEPTED  = 'concession_accepted'
    INSTALLING           = 'installing'
    ACCEPTANCE_TESTING   = 'acceptance_testing'
    IN_STOCK             = 'in_stock'
    IN_USE               = 'in_use'
    MAINTAINING          = 'maintaining'
    REPAIRING            = 'repairing'
    SEALED               = 'sealed'
    SCRAPPED             = 'scrapped'
```

```python
# app/services/state_machine.py
from app.utils.enums import FixtureStatus as S
from app.models import FixtureStatusHistory, db
from app.services.audit_service import log_force_action

# {from_status: {to_status: trigger}}
# 注意:同一 from→to 对只能有一个 trigger;不同 trigger 可以指向相同 to_status
# 通过(from, to)对反查 trigger 的方式自然支持驳回路径复用
TRANSITIONS = {
    S.PENDING_IQC: {
        S.IQC_INSPECTING:    'normal',
        S.EMERGENCY_PENDING: 'emergency_auth',
    },
    S.IQC_INSPECTING: {
        S.INSTALLING:          'iqc_pass',
        S.CONCESSION_ACCEPTED: 'concession_approved',
        S.PENDING_IQC:         'return_repair',     # 复用:既用于退厂返修,也用于审批驳回
    },
    S.EMERGENCY_PENDING:    { S.INSTALLING: 'normal' },
    S.CONCESSION_ACCEPTED:  { S.INSTALLING: 'normal' },
    S.INSTALLING:           { S.ACCEPTANCE_TESTING: 'normal' },
    S.ACCEPTANCE_TESTING: {
        S.IN_STOCK:    'acceptance_pass',
        S.INSTALLING:  'rework',                    # ★ V1.4 改名,与 'normal' 区分
        S.SCRAPPED:    'acceptance_fail_scrap',     # 业务确认:试产不合格可直接报废
    },
    S.IN_STOCK: {
        S.IN_USE:    'checkout',
        S.SEALED:    'seal',
        S.SCRAPPED:  'scrap',
    },
    S.IN_USE: {
        S.IN_STOCK:     'return',
        S.MAINTAINING:  'maintenance_due',
        S.REPAIRING:    'repair_request',
    },
    S.MAINTAINING: { S.IN_STOCK: 'normal' },
    S.REPAIRING:   { S.IN_STOCK: 'normal' },
    S.SEALED:      { S.IN_STOCK: 'release_seal' },
    S.SCRAPPED:    {},                              # 终态
}

# 驳回时使用的 (trigger, to_status) 配置 — 复用 TRANSITIONS 中已定义的合法路径
REJECT_CONFIG = {
    S.IQC_INSPECTING:     ('return_repair', S.PENDING_IQC),
    S.ACCEPTANCE_TESTING: ('rework',         S.INSTALLING),
}


class StateMachineError(Exception):
    pass


def transition(fixture, to_status, trigger, operator_id,
               reason=None, related=None):
    """
    正常状态流转 — 严格走 TRANSITIONS,不可绕过。
    任何尝试通过本函数做"非法"跳转都会抛 StateMachineError。
    """
    from_status = fixture.current_status
    allowed = TRANSITIONS.get(from_status, {})
    if to_status not in allowed:
        raise StateMachineError(f"非法状态转换:{from_status} -> {to_status}")
    if allowed[to_status] != trigger:
        raise StateMachineError(
            f"触发器不匹配:期望 {allowed[to_status]},实际 {trigger}"
        )

    history = FixtureStatusHistory(
        fixture_id=fixture.id,
        from_status=from_status,
        to_status=to_status,
        trigger_type=trigger,
        reason=reason,
        related_table=related[0] if related else None,
        related_id=related[1] if related else None,
        operator_id=operator_id,
    )
    db.session.add(history)
    fixture.current_status = to_status
    return fixture


def reject(fixture, operator_id, reason):
    """
    审批驳回 → 走 TRANSITIONS 内已配置的回退路径
    严格校验,不再使用 force=True 绕过(★ V1.4 修订)
    """
    config = REJECT_CONFIG.get(fixture.current_status)
    if not config:
        raise StateMachineError(
            f"{fixture.current_status} 不支持驳回回退"
        )
    trigger, to_status = config
    return transition(
        fixture, to_status, trigger, operator_id,
        reason=f"[审批驳回] {reason}"
    )


def force_transition(fixture, to_status, operator_id, reason):
    """
    超管强制跳转 — 唯一允许绕过 TRANSITIONS 校验的入口。
    必须满足:
    1. 操作者是超管(由调用方权限校验保证,本函数不重复校验)
    2. 必须填写原因(非空)
    3. 自动写审计日志
    """
    if not reason or not reason.strip():
        raise ValueError("强制跳转必须填写原因")

    from_status = fixture.current_status
    history = FixtureStatusHistory(
        fixture_id=fixture.id,
        from_status=from_status,
        to_status=to_status,
        trigger_type='forced',                # 历史记录中明确标记
        reason=reason,
        operator_id=operator_id,
    )
    db.session.add(history)
    log_force_action(fixture, from_status, to_status, operator_id, reason)
    fixture.current_status = to_status
    return fixture
```

#### Blueprint 中的调用方式

```python
# app/blueprints/fixtures.py

@bp.route('/fixtures/<int:fid>/status', methods=['PATCH'])
@jwt_required()
def change_status(fid):
    fixture = Fixture.query.get_or_404(fid)
    body = request.get_json()

    # 乐观锁手动校验
    if fixture.version != body.get('version'):
        raise ConflictError(...)

    # 走严格状态机
    transition(
        fixture,
        to_status=body['to_status'],
        trigger=body['trigger'],
        operator_id=current_user_id(),
        reason=body.get('reason'),
    )
    fixture.version += 1
    db.session.commit()
    return success_response(fixture.to_dict())


@bp.route('/fixtures/<int:fid>/force-status', methods=['POST'])
@jwt_required()
@require_role('super_admin')                  # 仅超管
def force_change_status(fid):
    fixture = Fixture.query.get_or_404(fid)
    body = request.get_json()

    if fixture.version != body.get('version'):
        raise ConflictError(...)

    force_transition(
        fixture,
        to_status=body['to_status'],
        operator_id=current_user_id(),
        reason=body['reason'],                # 不可为空
    )
    fixture.version += 1
    db.session.commit()
    return success_response(fixture.to_dict())
```

#### 单元测试覆盖矩阵(必做)

```python
# tests/test_state_machine.py
def test_legal_transition_pending_to_inspecting():
    fixture = make_fixture(status=S.PENDING_IQC)
    transition(fixture, S.IQC_INSPECTING, 'normal', operator_id=1)
    assert fixture.current_status == S.IQC_INSPECTING

def test_illegal_transition_raises():
    fixture = make_fixture(status=S.PENDING_IQC)
    with pytest.raises(StateMachineError):
        transition(fixture, S.IN_USE, 'whatever', operator_id=1)

def test_reject_iqc_inspecting():
    fixture = make_fixture(status=S.IQC_INSPECTING)
    reject(fixture, operator_id=1, reason='设计审批未通过')
    assert fixture.current_status == S.PENDING_IQC
    history = fixture.status_history[-1]
    assert history.trigger_type == 'return_repair'
    assert '审批驳回' in history.reason

def test_reject_unsupported_state_raises():
    fixture = make_fixture(status=S.IN_STOCK)         # IN_STOCK 不在 REJECT_CONFIG
    with pytest.raises(StateMachineError):
        reject(fixture, operator_id=1, reason='x')

def test_force_transition_requires_reason():
    fixture = make_fixture(status=S.IN_STOCK)
    with pytest.raises(ValueError):
        force_transition(fixture, S.SCRAPPED, operator_id=1, reason='')

def test_force_transition_writes_audit_log():
    fixture = make_fixture(status=S.IN_STOCK)
    force_transition(fixture, S.IN_USE, operator_id=1, reason='测试')
    assert AuditLog.query.filter_by(action='force_status').count() == 1

def test_no_back_door_in_transition():
    """确保 transition() 不接受任何 force/bypass 参数"""
    sig = inspect.signature(transition)
    assert 'force' not in sig.parameters
```

#### 3.3.x 手动版封存联动设计（Phase 2 + Phase 4 分期实现）

> **设计里程碑**：
> - 接口骨架（可选）：Phase 1 Step 1-4-2（Frank 决策后）
> - 封存核心逻辑（fixtures 批量写入）：**Phase 2**（fixtures 表建立后）
> - 解封审批流接入：**Phase 4**（审批流引擎就绪后）

##### 业务规则

**触发条件（seal）：**
1. `batch.batch_type` **必须为** `manual_init`（其他类型不允许触发封存）
2. 同一 `project_id` 下**必须存在**至少一个 `mass_prod` 批次，且其状态 ∈ `{in_progress, completed}`（量产已投产才允许封存手动版）
3. 操作角色：`super_admin` 或 `warehouse`（仓库管理员执行封存动作）

**执行内容（seal，Phase 2 实现）：**
```python
# TODO(Phase 2): 批量封存同批次下所有 fixtures
# for fixture in batch.fixtures:
#     fixture.is_sealed = True
#     fixture.sealed_at = datetime.utcnow()
#     fixture.sealed_by = operator_id
#     db.session.add(FixtureStatusHistory(
#         fixture_id=fixture.id,
#         from_status=fixture.current_status,
#         to_status='sealed',
#         trigger_type='batch_seal',
#         operator_id=operator_id
#     ))
```

**解封流程（unseal）：**
- **Phase 1**：仅 `super_admin` 可直接解封（无审批），写审计日志
- **Phase 4**：接入双人会签审批流（PM + 生产主管 `production_lead`），复用 §3.4 的 `sequential` 模式引擎；`approval_id` 关联审批单

##### 状态字段设计说明

封存状态当前**仅由 `fixtures.is_sealed` 字段反映**，不在 `batches.status` 上新增独立状态值。
原因：`batches.status` 描述批次生命周期（draft → in_progress → completed → cancelled），封存是治具层面的物理状态，两个维度正交，合并会导致状态机路径爆炸。

> 🟡 **待确认（Q-003）**：是否需要在 `batches` 表上新增 `sealed_fixture_count` 汇总字段？详见 `Doc/00_open_questions.md`。
> 🟡 **待确认（Q-004）**：`manual_init` 批次封存后，`batches.status` 是否需要从现有枚举衍生 `sealed` 子状态？详见 `Doc/00_open_questions.md`。
> 🟡 **待确认（Q-005）**：解封会签是否复用 §3.4 的 sequential/parallel 引擎？详见 `Doc/00_open_questions.md`。

##### 与状态机三函数的关系

Phase 2 实现封存时，`fixture.is_sealed` 的写入**不走** `transition()` 函数（封存不是标准 12 状态流转），而是独立的 `seal_batch()` Service 函数，并在注释中标注"Phase 4 审批流接入后 unseal 将触发 `transition()` 的解封路径"。

`transition()` 函数签名**永远不允许**加 `force` / `bypass` 参数（§e.4 铁律）。

> §3.3 修订记录：Phase 2 Step 2-2-1（2026-05-15）——state_machine.py 按本节代码首次落地；audit_service.log_force_action() 新建；enums.py FixtureStatus 12状态常量落定；前端 status.js 追加 FIXTURE_STATUS_MAP。

---

### 3.4 审批流实现

(同 V1.3,顺序+并行双模式分支,approved/rejected 都透传 decision_type;通知统一邮件)

### 3.5 文件上传

(同 V1.3,pathlib 跨平台 + send_from_directory)

### 3.6 邮件告警 [V1.4 修订:事务隔离]

#### 主方案:Flask-APScheduler 内嵌

(同 V1.3)

#### 关键修订:`send_alert_dedup` 加事务隔离

```python
# app/services/alert_service.py
from app.extensions import db, mail
from flask_mail import Message

def send_alert_dedup(alert_type, target_table, target_id,
                     recipients, subject, body):
    """
    [V1.4 修订] 单封邮件失败不应株连同批次其他告警。
    所有数据库操作和邮件发送都包在 try/except 里,异常时 rollback。
    """
    today = date.today()

    try:
        alert = Alert.query.filter_by(
            alert_type=alert_type,
            target_table=target_table,
            target_id=target_id
        ).first()

        # 去重判定
        if alert and alert.is_active and alert.last_sent_at.date() == today:
            return False

        # 发送邮件(本步骤可能因 SMTP 超时/认证失败而抛异常)
        mail.send(Message(
            subject=subject,
            recipients=recipients,
            body=body,
        ))

        # 更新告警状态
        if alert:
            alert.last_sent_at = datetime.now()
            alert.is_active = True
        else:
            db.session.add(Alert(
                alert_type=alert_type,
                target_table=target_table,
                target_id=target_id,
                last_sent_at=datetime.now(),
                is_active=True,
            ))
        db.session.commit()
        return True

    except Exception as e:
        # ★ V1.4 关键:回滚 + 记日志,但不抛出,确保循环继续
        db.session.rollback()
        current_app.logger.error(
            f"send_alert_dedup failed: {alert_type}/{target_table}/{target_id}: {e}",
            exc_info=True
        )
        return False
```

#### `check_all_alerts` 的循环调用安全性

```python
# app/tasks/alert_checker.py
def check_po_urgent():
    """每个告警在独立事务中处理,互不干扰"""
    threshold = date.today() + timedelta(days=URGENT_THRESHOLD_DAYS)
    fixtures = Fixture.query.join(Batch).filter(...).all()
    for f in fixtures:
        # 每次调用都是独立事务边界,失败不影响下一条
        send_alert_dedup(
            alert_type='po_urgent',
            target_table='fixtures',
            target_id=f.id,
            recipients=[f.project.owner.email],
            subject=f"[紧急] {f.fixture_code} 距交期不足 3 天",
            body=...,
        )
```

#### 必测场景

1. 首次触发 → 发送
2. 同日相同 target 再次触发 → 跳过
3. `is_active=FALSE` 后再次触发 → 重新发送
4. 跨日触发同一 alert → 发送
5. 不同 target_id 同 alert_type → 各自独立去重
6. ★ V1.4 必测:循环中第 3 条 SMTP 超时 → 第 1/2/4/5 条仍正常处理
7. ★ V1.4 必测:数据库 commit 失败时 rollback 是否生效

### 3.7 报表导出三档策略

(同 V1.3)

---

## 四、前端模块划分

### 4.1 目录结构与路由

(同 V1.3,目录无变更)

### 4.2 关键组件设计建议

(同 V1.3)

### 4.3 甘特图技术选型与降级

(同 V1.3,Frappe Gantt + 100+ 自动降级)

### 4.4 12 状态颜色映射

(同 V1.3)

### 4.5 时间处理 + axios 拦截器 [V1.4 修订:dayjs.tz 强校验]

#### 时间处理工具(必须使用)

```javascript
// frontend/src/utils/datetime.js
import dayjs from 'dayjs'
import utc from 'dayjs/plugin/utc'
import timezone from 'dayjs/plugin/timezone'
import customParseFormat from 'dayjs/plugin/customParseFormat'

dayjs.extend(utc)
dayjs.extend(timezone)
dayjs.extend(customParseFormat)
dayjs.tz.setDefault('Asia/Shanghai')

/**
 * ★ V1.4 强制规范:处理后端返回的 datetime 字符串必须用本函数
 * 不要直接用 dayjs(str)、new Date(str) 等隐式解析
 *
 * 原因:dayjs.tz.setDefault() 不影响裸调用 dayjs("2026-04-26T14:30:00"),
 * 浏览器会按本地时区解析。海外/异地访问时会出现时间偏差 bug。
 */
export function parseBackendTime(str) {
  if (!str) return null
  return dayjs.tz(str)        // 强制按 Asia/Shanghai 解析
}

export function formatBackendTime(str, fmt = 'YYYY-MM-DD HH:mm') {
  const t = parseBackendTime(str)
  return t ? t.format(fmt) : '-'
}

export function formatDate(str, fmt = 'YYYY-MM-DD') {
  return formatBackendTime(str, fmt)
}
```

#### main.js 顶层配置

```javascript
// frontend/src/main.js
import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import './utils/datetime'                 // ★ 副作用 import,确保插件已加载

import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'

const app = createApp(App)
app.use(router)
app.use(ElementPlus)
app.mount('#app')
```

#### 组件中正确使用

```vue
<!-- ✅ 正确:用工具函数 -->
<template>
  <span>{{ formatBackendTime(row.created_at) }}</span>
</template>
<script setup>
import { formatBackendTime } from '../../utils/datetime.js'
</script>

<!-- ❌ 错误(V1.4 禁止): -->
<!-- {{ dayjs(row.created_at).format('YYYY-MM-DD') }} -->
<!-- {{ new Date(row.created_at).toLocaleString() }} -->
```

#### axios 409 拦截器(同 V1.3)

```javascript
// frontend/src/api/request.js
import axios from 'axios'
import { ElMessageBox } from 'element-plus'
import './../utils/datetime'              // 确保 dayjs 配置已加载

const request = axios.create({ baseURL: '/api', timeout: 15000 })

request.interceptors.response.use(
  resp => resp,
  async err => {
    const { response } = err
    if (response?.status === 409) {
      try {
        await ElMessageBox.alert(
          '该数据已被他人修改,请刷新页面后重试。',
          '数据冲突',
          { type: 'warning', confirmButtonText: '刷新' }
        )
        window.location.reload()
      } catch { /* 用户关闭 */ }
      return Promise.reject(err)
    }
    if (response?.status === 401) {
      localStorage.removeItem('token')
      window.location.href = '/login'
    }
    return Promise.reject(err)
  }
)
export default request
```

---

## 五、开发路线图

### 5.1 模块开发顺序 [V1.4 修订:Phase 0 加 seed 脚本完善 + 09_dev_rules.md 落位]

```
Phase 0 — 基建(1 周)
  ├─ 开发机环境(同 V1.3 清单)
  ├─ 生产机预演(同 V1.3 清单)
  ├─ 代码框架
  │   □ Flask app factory + extensions + python-dotenv 三套环境
  │   □ ★ Config 含 pool_recycle=3600
  │   □ ★ TimedRotatingFileHandler 配置
  │   □ 用户/角色模型(含 is_active 软删) + JWT 登录
  │   □ ★ 各 Model 不要写 __mapper_args__ = {'version_id_col': version}
  │   □ 通用响应/异常/装饰器(含 ConflictError)
  │   □ 全局 StaleDataError 捕获返回 409
  │
  ├─ ★ V1.4 新增:scripts/seed_data.py 完整化
  │   □ 超管账号(密码从 .env 读)
  │   □ 角色字典(9 角色)
  │   □ 状态字典(12 状态)
  │   □ 设备代号字典(YN/DZ2X/DZ2S/LRJ/ZDY/YY)
  │   □ 11 项默认供应商(KFS/HR/HS/BT/HX/JC/XW/FBW/DR/XDX/XD)
  │   □ SUS VC + Cu VC 完整治具模板 40+ 项(详见编码规则文档)
  │   □ flask seed 命令封装,支持反复执行
  │
  ├─ ★ V1.4 新增:docs/09_dev_rules.md 落位
  │   □ 后端禁律(11 条)
  │   □ 前端禁律(8 条)
  │   □ 命名约定
  │   □ Code Review Checklist
  │
  └─ Vue 项目初始化
      □ Vite + Element Plus + Pinia + Router
      □ vite.config.js API 代理
      □ ★ utils/datetime.js + parseBackendTime() 工具
      □ axios 拦截器(409/401)

Phase 1-7(同 V1.3)
```

**总工期估算:13-17 周**

### 5.2 阶段里程碑

(同 V1.3)

### 5.3 CLAUDE.md 结构建议 [V1.4 修订]

```markdown
# CLAUDE.md — DBU 模治具管理系统 AI 协作指南

## 项目概览
- 业务:模治具全生命周期管理
- 技术栈:Flask 3 + Vue 3 + MySQL 8.4
- 部署:混合方案 — 开发 Docker MySQL + 本地 Flask;生产 Windows Server 原生

## 关键文档
- docs/00_open_questions.md
- docs/01_requirement_v2.1.md
- docs/02_coding_rules_v1.0.md
- docs/03_architecture_v1.4.md      ← 权威架构
- docs/04_api_spec.md
- docs/05_permissions.md
- docs/06_restore_procedure.md
- docs/07_export_guideline.md
- docs/08_deployment_windows.md
- docs/09_dev_rules.md               ← ★ V1.4 新增:开发铁律
- TASKS.md                            ← 当前任务

## 当前阶段
Phase X — XXX

## Critical Rules(继承自 vc-cost-system + 本项目)
(参考 docs/09_dev_rules.md 完整版)

## 本系统专属规则(V1.4 完整版)

### 配置与环境
- 三套环境配置:.env.development / .env.production / .env.example
- python-dotenv 按 FLASK_ENV 加载;config.py 不硬编码任何密码或密钥
- .env.* 必须 gitignored
- ★ V1.4:连接池必须配 pool_recycle=3600,防 wait_timeout 假死
- ★ V1.4:Flask logging 必须配 TimedRotatingFileHandler,backupCount=30
- 开发机连接 Docker MySQL,生产机连接 Windows MySQL,主机端口相同密码必然不同
- APScheduler 实例化时显式 timezone='Asia/Shanghai'

### 部署
- 生产用 Waitress(serve.py 入口),NSSM 注册为 Windows 服务
- ★ V1.4:Waitress threads=32, max_request_body_size=500MB(防御底线)
- Flask 同时 serve /api 与 Vue 静态文件(MVP 方案)
- 路径用 pathlib.Path 跨平台;DB 中相对路径永远存正斜杠

### 删除策略
(同 V1.3,核心表禁 DELETE)

### 状态机(★ V1.4 关键修订)
- 状态变更必须走 services/state_machine.py 提供的三个函数:
  - transition() — 正常流转,严格走 TRANSITIONS
  - reject() — 审批驳回,严格走 REJECT_CONFIG → TRANSITIONS
  - force_transition() — 超管强制(唯一绕过 TRANSITIONS 的入口)
- ★ transition() 函数签名禁止包含 force/bypass 参数
- ★ 不允许直接改 fixture.current_status
- 改流程必须同步 5 处:state_machine.py / status_history 表 / 前端 status.js / i18n / 文档

### 编码与版本
(同 V1.3)

### 审批流
(同 V1.3,顺序+并行,approved/rejected 都传 decision_type)

### 快照
(同 V1.3)

### 附件
(同 V1.3,pathlib + 不限大小,但 Waitress 物理底线 500MB)

### 调度器
- Flask-APScheduler 内嵌,Waitress 单进程多线程不会有并发问题
- 备选方案:check_alerts_standalone.py + Windows 任务计划

### 并发(★ V1.4 重大修订)
- 乐优锁仅使用手动校验,Service 层比对 version 失败抛 409
- ★ 严禁在任何 Model 上加 __mapper_args__ = {'version_id_col': version}
- 全局异常处理器仍捕获 StaleDataError 返回 409 作为兜底
- PUT/PATCH 必须包含 version 字段,前端从 GET 返回值带回

### 报表导出
(同 V1.3)

### 邮件告警(★ V1.4 修订)
- 必须经 send_alert_dedup() 去重
- ★ V1.4:send_alert_dedup 必须 try/except 兜底,失败 rollback + log,不抛出
- 紧急阈值 URGENT_THRESHOLD_DAYS=3

### 前端时间处理(★ V1.4 新增)
- 处理后端返回的 datetime 字段,一律用 utils/datetime.js 的 parseBackendTime/formatBackendTime
- ★ 严禁裸调用 dayjs(str)、new Date(str)
- main.js 顶层 import './utils/datetime' 确保 setDefault 生效
```

### 5.4 独立 AI 辅助开发的风险点 [V1.4 修订]

(在 V1.3 基础上新增 4 条 V1.4 风险)

| 风险 | 缓解措施 |
|------|----------|
| ★ V1.4 新增:AI 在 Model 中无脑加 `__mapper_args__` 自动版 | CLAUDE.md 明确禁止;Code Review 时全文 grep `version_id_col`;单元测试验证 version 手动递增正确性 |
| ★ V1.4 新增:AI 在 transition() 中加回 force 参数 | CLAUDE.md 明确禁止;test_no_back_door_in_transition 测试守住 |
| ★ V1.4 新增:AI 在告警循环中漏写 try/except | docs/09 写明;Code Review 时全文搜 `send_alert_dedup`;单元测试模拟 SMTP 失败验证不株连 |
| ★ V1.4 新增:AI 在前端用 `dayjs(str)` 或 `new Date(str)` | docs/09 写明;eslint 规则可加自定义 no-restricted-syntax 拦截 |
| 开发机配置泄漏到生产 | 严格分离 .env.* + .gitignore 双重保险 |
| 生产机 Windows 路径 Bug | pathlib.Path 全程使用 |
| 开发机 Docker MySQL 时区误用 UTC | 容器加 --default-time-zone + 连接串 init_command 双保险 |
| NSSM Windows 服务启动失败 | Phase 7 部署时手动跑一遍 serve.py 确认无报错再注册 |
| AI 自由发挥加 DELETE 端点 | CLAUDE.md 明确;Code Review 全文搜 `methods=['DELETE']` |
| 大数据量导出 OOM | CLAUDE.md 明确禁止 pandas.to_excel + openpyxl 默认模式 |
| 状态机/审批流改动失控 | 先写测试再写实现 |
| 数据库迁移不可逆错误 | 严格 Schema-First;migration 必须人工 review |
| AI 生成代码隐藏 Bug | 关键路径必须有单元测试 |
| 过度设计倾向 | "MVP 真的需要吗?" |
| 跨模块改动遗漏 | 改状态机时同步检查 5 处 |
| 邮件配置生产失败 | 开发期 MailHog;生产前单独测 send_email() |
| 备份从未验证 | 上线前完整还原演练;每月抽查 |
| 权限矩阵前后端不一致 | 派生自 docs/05_permissions.md |
| APScheduler 在 debug=True 下重复启动 | `if not app.debug or os.environ.get('WERKZEUG_RUN_MAIN') == 'true'` 守卫 |

---

## 六、附:关键决策一览表 [V1.4 修订]

| # | 决策点 | 选择 | 一句话理由 |
|---|--------|------|------------|
| 1 | 整体架构 | 单体 Flask + Vue SPA + 混合部署 | 匹配开发者经验 |
| 2 | 异步任务 | Flask-APScheduler 内嵌 | 单进程无并发陷阱 |
| 3 | 环境与配置 | .env.* + python-dotenv + ★ pool_recycle | 防生产假死 |
| 4 | 核心表删除 | 禁止 HTTP DELETE,作废走状态字段 | 制造业资产数据不可丢 |
| 5 | 快照机制 | 复制型 + 追加同步 | 简单直观 + 应对长周期演进 |
| 6 | 审批流模型 | 多场景共用 + 顺序/并行双模式 | 一套引擎覆盖所有 |
| 7 | 审批通知 | MVP 邮件统一 + 事务隔离 | ★ V1.4:单封失败不株连 |
| 8 | **状态机实现** | **transition / reject / force_transition 三函数清晰职责** | **★ V1.4:消除 force=True 后门** |
| 9 | 试产不合格→报废 | 开放(业务确认) | 业务规则明确 |
| 10 | 编码生成 | 后端服务 + 加开继承当前版本 | 与图纸一致性符合 |
| 11 | 版本升级语义 | 改字段 + drawings 追加;不新建 fixture | 实物不变图纸演进 |
| 12 | 加开复制语义 | 新建 fixture + parent_fixture_id 溯源 | 套号递增可追溯 |
| 13 | 文件存储 | UPLOAD_BASE 环境变量 + 鉴权 send_from_directory | 简单跨平台 |
| 14 | 附件大小 | 业务无限制,但 ★ Waitress max_request_body_size=500MB 物理底线 | 双层保护 |
| 15 | 甘特图库 | Frappe Gantt + 100+ 降级 | 轻量友好 |
| 16 | 状态颜色 | 自定义 :color | 12 状态需视觉区分 |
| 17 | 权限实现 | 后端字典 + 前端按钮 + 派生单一文档 | 避免前后端偏移 |
| 18 | 告警去重 | alerts 表 + 每日窗口 + 紧急阈值 3 天 + ★ try/except 隔离 | 不株连不轰炸 |
| 19 | 报表导出 | 三档策略 | 从源头规避 OOM |
| 20 | 备份方案 | Windows 任务计划 + mysqldump + robocopy | 与现有系统一致 |
| 21 | **乐观锁** | **仅手动校验(★ V1.4:删除 ORM 自动版)** | **避免双层冲突;手动版加测试覆盖即可** |
| 22 | 采购订单关系 | PO 头 + items 一对多 | 反映"一单多治具" |
| 23 | 计划日期级联 | 默认不级联,"重算后续"按钮 | 既精确又方便 |
| 24 | 409 处理 | axios 拦截器统一弹窗刷新 | 避免重复处理 |
| 25 | 用户软删 | is_active=FALSE,无 DELETE | 保审计完整 |
| 26 | **生产日志** | **★ V1.4:TimedRotatingFileHandler + 30 天保留** | **防 NSSM 单体日志撑爆磁盘** |
| 27 | **Waitress 调优** | **★ V1.4:threads=32 + max_request_body_size=500MB** | **I/O 友好 + 防 OOM** |
| 28 | **前端时间处理** | **★ V1.4:统一 parseBackendTime() 工具,禁裸调用** | **防 dayjs 隐式解析坑** |

---

## 七、文件修订记录

| 版本 | 日期 | 修订内容 | 修订人 |
|------|------|----------|--------|
| V1.0 | 2026-04-26 | 初版发布(Docker Compose 4 容器) | Claude (Opus) |
| V1.1 | 2026-04-26 | 第一轮审阅 14 处修订 | Claude (Opus) |
| V1.2 | 2026-04-26 | 第二轮审阅 9 处修订 + 业务确认 5 处落地 | Claude (Opus) |
| V1.3 | 2026-04-27 | 部署方案重大调整:混合部署替代 Docker Compose 全栈容器化 | Claude (Opus) |
| **V1.4** | **2026-04-27** | **第三轮(最终)审阅 8 处底层与机制修正:** ① **乐观锁纠偏**:删除 V1.1/V1.2/V1.3 错误提出的"双层乐观锁",仅保留 Service 层手动校验,所有 Model 删除 `__mapper_args__ = {'version_id_col': version}`;② **状态机重构**:消除 `transition(force=True)` 后门,拆分为 transition / reject / force_transition 三函数,REJECT_CONFIG 复用 TRANSITIONS 已配置的合法路径;③ **告警事务隔离**:send_alert_dedup 加 try/except + rollback,单封邮件失败不株连;④ **连接池防假死**:Config 新增 `pool_recycle=3600`;⑤ **生产日志切割**:Flask 集成 TimedRotatingFileHandler,backupCount=30,取代 NSSM 长期记录;⑥ **Waitress 调优**:threads 8→32,max_request_body_size=500MB 防御底线;⑦ **前端时间强校验**:统一 utils/datetime.js 的 parseBackendTime/formatBackendTime,禁止裸调用 dayjs(str)/new Date(str);⑧ **文档落位**:新增 docs/09_dev_rules.md 收纳开发铁律;Phase 0 完善 seed_data.py 内容清单(超管/字典/供应商/40+ 治具模板) | Claude (Opus) |

---

> **本架构文档版本:V1.4**
> **本版作为开发启动前的最终架构基线,后续若需变更:必须更新版本号 + 修订记录 + 同步到 docs/03_architecture.md**
> **项目代码仓库根目录的 CLAUDE.md 应永远引用本文档为权威架构来源。**

---

## 附录 A:仍待业务确认事项

| # | 事项 | 状态 |
|---|------|------|
| 1-5 | 试产报废、加开继承、封存隔离、紧急阈值、附件大小 | ✅ 全部已确认 |

**当前无待确认业务事项。**

---

## 附录 B:V1.3/V1.4 部署待确认事项(开发启动前需 IT 配合)

(同 V1.3,8 项 IT 协调清单)

---

## 附录 C:V1.4 必读检查清单

开发启动前请逐项确认:

- [ ] 已阅读 V1.4 全文,理解全部 8 处底层修正的原因
- [ ] **理解为什么删除 ORM 乐观锁自动版**(双层会冲突)
- [ ] **理解为什么 transition 不能有 force 参数**(消除非法状态写入路径)
- [ ] **理解 send_alert_dedup 必须 try/except**(单封失败不株连)
- [ ] 已规划 docs/09_dev_rules.md 内容(后端 11 条 + 前端 8 条 + Code Review 清单)
- [ ] 已规划 scripts/seed_data.py 完整内容(超管/字典/供应商 11 项/治具模板 40+ 项)
- [ ] 已与公司 IT 沟通附录 B 的 8 项部署事项
- [ ] CLAUDE.md 已写入"本系统专属规则(V1.4 完整版)"
- [ ] docs/ 下已建立 00/04/05/06/07/08/09 占位文档
- [ ] 已为状态机 + 编码生成 + 审批流 + 告警去重 + 计划日期推算 + 乐观锁 6 个核心模块预留单元测试位
- [ ] 已规划生产机预演节奏(Phase 7 之前至少做过 1 次完整空跑)
- [ ] 已确认 V1.4 所有 28 项关键决策与开发者本人理解一致
