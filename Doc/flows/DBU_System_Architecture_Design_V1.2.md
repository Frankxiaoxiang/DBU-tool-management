# DBU 模治具管理系统 — 系统架构设计方案 V1.2

> 配套文档：《DBU模治具全流程管控文件 V2.1》、《DBU模治具编码规则 V1.0》、《CLAUDE_reference_for_opus.md》
>
> 设计原则：**清晰分层 · 模块独立 · 可维护性优先 · 复杂度可控 · 兼容 Claude Code CLI 协作开发**
>
> **本版变更**：基于 V1.1 第二轮审阅意见 + 5 项业务确认整合，共 14 处修订（9 条审阅 + 5 条业务规则落地）。详见末尾「修订记录」。

---

## 一、整体架构设计

### 1.1 架构模式选择

**推荐：经典前后端分离 + 单体 Flask 后端 + Docker Compose 全栈容器化**

| 维度 | 选择 | 理由 |
|------|------|------|
| 后端形态 | 单体 Flask（Modular Monolith） | 50 人内部使用、局域网部署，微服务过度设计 |
| 前端形态 | Vue 3 SPA + Element Plus | 与现有 vc-cost-system 一致 |
| 通信协议 | RESTful JSON over HTTP | 与现有规范一致 |
| 部署形态 | Docker Compose（5 容器）+ **统一时区配置** | **见 1.3 [V1.2 强化]** |
| 认证 | JWT（Flask-JWT-Extended） | 与现有规范一致 |
| 异步任务 | 独立 scheduler 容器 + APScheduler | 见 1.3 |

### 1.2 前后端职责划分

```
┌──────────────────────────┐         ┌─────────────────────────────┐
│       前端 (Vue 3)        │         │      后端 (Flask)            │
├──────────────────────────┤         ├─────────────────────────────┤
│ · 页面渲染、表单校验       │         │ · 业务逻辑（services/）       │
│ · 路由守卫、按钮级权限     │ ──API─▶ │ · 状态机校验                 │
│ · 数据可视化(甘特图/导出) │ ◀─JSON─ │ · 审批流流转                 │
│ · 文件上传(multipart)     │         │ · 编码自动生成               │
│                          │         │ · 权限校验(最终防线)         │
│                          │         │ · 文件落盘 / 大报表流式生成   │
│                          │         │ · 计划日期推算               │
│                          │         │ · 邮件告警调度               │
└──────────────────────────┘         └─────────────────────────────┘
```

**铁律：前端权限只用于"隐藏不该看到的按钮和菜单"，后端必须独立做权限校验。**

### 1.3 Docker Compose 服务编排 [V1.2 强化：时区四处联动]

#### docker-compose.yml

```yaml
version: '3.8'

# ★ V1.2：所有应用容器统一时区配置
x-tz-env: &tz-env
  TZ: Asia/Shanghai

services:
  nginx:
    image: nginx:alpine
    environment: { <<: *tz-env }
    volumes:
      - /etc/localtime:/etc/localtime:ro       # 宿主机时区
      - ./frontend/dist:/usr/share/nginx/html:ro
      - ./nginx.conf:/etc/nginx/conf.d/default.conf:ro
      - /data/dbu/uploads:/data/uploads:ro     # 为 X-Accel-Redirect 预留
    ports: ["80:80"]
    depends_on: [backend]

  backend:
    build: ./backend
    command: gunicorn -w 4 -b 0.0.0.0:5000 run:app
    environment:
      <<: *tz-env
      DATABASE_URL: mysql+pymysql://app:***@mysql:3306/dbu_fixture?charset=utf8mb4
      JWT_SECRET: ...
      SMTP_HOST: ...
    volumes:
      - /etc/localtime:/etc/localtime:ro
      - /data/dbu/uploads:/app/uploads
      - /data/dbu/logs:/app/logs
    depends_on: [mysql]

  scheduler:
    build: ./backend
    command: python -m app.tasks.scheduler_runner
    environment:
      <<: *tz-env                              # ★ 调度器与 backend 共享时区
      DATABASE_URL: ...
    volumes:
      - /etc/localtime:/etc/localtime:ro
      - /data/dbu/uploads:/app/uploads:ro
      - /data/dbu/logs:/app/logs
    depends_on: [mysql]
    restart: unless-stopped

  mysql:
    image: mysql:8.4
    environment:
      <<: *tz-env                              # ★ MySQL 容器时区
      MYSQL_ROOT_PASSWORD: ...
      MYSQL_DATABASE: dbu_fixture
      # [V1.2 修订] MYSQL_DEFAULT_CHARSET 为非官方变量，已删除
      # 字符集仅依靠下方 command 即可
    volumes:
      - /etc/localtime:/etc/localtime:ro
      - /data/dbu/mysql:/var/lib/mysql
      - ./mysql/conf.d:/etc/mysql/conf.d:ro
    command: >
      --character-set-server=utf8mb4
      --collation-server=utf8mb4_unicode_ci
      --default-time-zone='+08:00'             # ★ MySQL 内部时区

  backup:
    build: ./backup
    environment: { <<: *tz-env }
    volumes:
      - /etc/localtime:/etc/localtime:ro
      - /data/dbu/mysql:/source/mysql:ro
      - /data/dbu/uploads:/source/uploads:ro
      - /data/backup:/backup
    depends_on: [mysql]
```

#### [V1.2 关键说明] 时区必须四处联动配置

仅靠 Docker 环境变量不够，MySQL 和 SQLAlchemy 默认走 UTC，必须在以下四处统一：

**① docker-compose.yml**：`TZ` 环境变量 + `/etc/localtime` 挂载 + MySQL `--default-time-zone='+08:00'`（见上）

**② SQLAlchemy 数据库连接串（双保险）**

```python
# backend/app/config.py
class Config:
    SQLALCHEMY_DATABASE_URI = (
        "mysql+pymysql://app:***@mysql:3306/dbu_fixture"
        "?charset=utf8mb4&init_command=SET time_zone='+08:00'"
    )
    SQLALCHEMY_ENGINE_OPTIONS = {
        "connect_args": {
            "init_command": "SET time_zone='+08:00'",
        },
        "pool_pre_ping": True,
    }
```

**③ JWT 过期时间显式配置**

```python
from datetime import timedelta
class Config:
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=8)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=7)
```

**④ APScheduler 时区**

```python
# app/tasks/scheduler_runner.py
sched = BlockingScheduler(timezone='Asia/Shanghai')
```

**为什么必须每处都配？**
- 仅 `TZ=Asia/Shanghai` 只影响容器内 `date` 命令和 Python `datetime.now()`
- MySQL 服务的 `time_zone` 系统变量默认是 `SYSTEM`（即容器 UTC），不受 `TZ` 影响
- 因此 `NOW()` 写入数据库的仍是 UTC，与 Python 端不一致 → "今天我下单的，数据库显示是昨天"
- 连接串 `init_command` 只在每个会话生效，所以双保险

**Phase 0 验证清单（必做）：**

```bash
# 进入各容器
docker exec backend date            # 应显示北京时间
docker exec scheduler date
docker exec mysql date

# 验证 MySQL 内部时区
docker exec mysql mysql -uapp -p*** -e "
  SELECT NOW(), @@global.time_zone, @@session.time_zone;
"
# 期望输出：NOW() 为北京时间；time_zone 为 +08:00

# 验证 Python 写入
docker exec backend python -c "
  from app.extensions import db
  from sqlalchemy import text
  print(db.session.execute(text('SELECT NOW()')).scalar())
"
```

#### scheduler_runner 入口

```python
# backend/app/tasks/scheduler_runner.py
from apscheduler.schedulers.blocking import BlockingScheduler
from app import create_app
from app.tasks.alert_checker import register_jobs

if __name__ == '__main__':
    app = create_app()
    sched = BlockingScheduler(timezone='Asia/Shanghai')
    with app.app_context():
        register_jobs(sched)
        sched.start()
```

### 1.4 备份与还原策略

| 对象 | 工具 | 频率 | 保留策略 | 存放位置 |
|------|------|------|----------|----------|
| MySQL 数据 | `mysqldump --default-character-set=utf8mb4` | 每天 02:00 | 每日 7 + 每周 4 + 每月 12 | `/data/backup/mysql/` |
| 附件目录 | `rsync -av --delete` | 每天 03:00 | 每日 7 + 每周 4 | `/data/backup/uploads/` |
| 完整目录快照 | `tar.gz` | 每周一次 | 保留 4 周 | `/data/backup/snapshot/` |

**还原流程详见 `docs/06_restore_procedure.md`，每月抽查演练 1 次。**

---

## 二、数据库设计方案（基于 MySQL 8.4）

### 2.1 核心数据表清单（共 27 张）

(同 V1.1，此处不重列；V1.2 新增"软删除原则"作为整体设计约束)

#### [V1.2 新增] 核心约束：禁止物理删除

**核心业务表禁止暴露 HTTP DELETE 端点。** 包括：
- `projects` / `batches` / `fixtures` / `purchase_orders` / `purchase_order_items`
- `iqc_reports` / `acceptance_reports` / `maintenance_records` / `repair_records` / `scrap_records`
- `drawings` / `dfm_reports`

**作废路径：**
- `projects` / `batches` 走状态字段 `cancelled`
- `fixtures` 走状态机 `SCRAPPED`（已存在）
- 其他业务单据走对应业务状态

**配置型数据可允许 DELETE（但需软删字段）：**
- `users`：物理删除会让审计日志悬空，改为 `is_active=FALSE`
- `suppliers`：用 `is_active=FALSE` 标记停用
- `fixture_templates`：用 `is_active=FALSE` 标记淘汰

**真·删除（清理脏数据）：** 仅超管在 `scripts/reset_db.py` 或数据库 CLI 执行，不暴露 API。

### 2.2 核心 ER 关系图

(同 V1.1)

### 2.3 三层数据结构核心字段 [V1.2 修订]

#### `projects` — 项目主表 [V1.2 新增 cancelled 状态]

```sql
CREATE TABLE projects (
  id              BIGINT PRIMARY KEY AUTO_INCREMENT,
  project_code    VARCHAR(10) UNIQUE NOT NULL,
  project_name    VARCHAR(100) NOT NULL,
  product_type    ENUM('SUS_VC','CU_VC','HP') NOT NULL,
  project_owner_id BIGINT NOT NULL,
  -- ★ V1.2 修订：新增 cancelled 状态用于作废
  status          ENUM('active','closed','cancelled') DEFAULT 'active',
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
-- 约束：不暴露 DELETE 接口，作废走 status='cancelled'
ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

#### `batches` — 需求批次 [V1.2 新增 cancelled 状态]

```sql
CREATE TABLE batches (
  id                BIGINT PRIMARY KEY AUTO_INCREMENT,
  project_id        BIGINT NOT NULL,
  batch_no          VARCHAR(20) NOT NULL,
  batch_type        ENUM('manual_init','mass_prod',
                         'addon_quantity','addon_optimize') NOT NULL,
  parent_batch_id   BIGINT NULL,
  flow_path         ENUM('full','simplified') DEFAULT 'full',
  -- ★ V1.2 修订：新增 cancelled 状态
  status            ENUM('draft','confirmed','in_progress',
                         'completed','closed','cancelled') DEFAULT 'draft',
  cancelled_reason  TEXT NULL,
  cancelled_at      DATETIME NULL,
  cancelled_by      BIGINT NULL,
  expected_date     DATE NULL,
  remark            TEXT,
  created_by        BIGINT NOT NULL,
  created_at        DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at        DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  version           INT DEFAULT 0,
  UNIQUE KEY uk_project_batch (project_id, batch_no),
  INDEX idx_parent (parent_batch_id),
  INDEX idx_status (status),
  CONSTRAINT fk_batch_proj FOREIGN KEY (project_id) REFERENCES projects(id),
  CONSTRAINT fk_batch_parent FOREIGN KEY (parent_batch_id) REFERENCES batches(id)
)
-- 约束：不暴露 DELETE 接口，作废走 status='cancelled'
;
```

#### `fixtures` — 模治具主表（核心）

```sql
CREATE TABLE fixtures (
  id                  BIGINT PRIMARY KEY AUTO_INCREMENT,
  fixture_code        VARCHAR(50) UNIQUE NOT NULL,
  project_id          BIGINT NOT NULL,
  batch_id            BIGINT NOT NULL,
  template_snapshot_id BIGINT NOT NULL,
  fixture_type_code   VARCHAR(20) NOT NULL,
  set_no              INT NOT NULL,
  current_version_code VARCHAR(5) NOT NULL,
  current_status      VARCHAR(30) NOT NULL,
  parent_fixture_id   BIGINT NULL,           -- 加开-复制图纸场景
  supplier_id         BIGINT NULL,
  shelf_location_id   BIGINT NULL,           -- ★ 封存仅是状态标志，物理位置不变（业务确认）
  -- 计划日期
  planned_arrival_date     DATE NULL,
  planned_iqc_date         DATE NULL,
  planned_install_date     DATE NULL,
  planned_acceptance_date  DATE NULL,
  planned_handover_date    DATE NULL,
  -- 实际日期
  actual_arrival_date      DATE NULL,
  actual_iqc_date          DATE NULL,
  actual_install_date      DATE NULL,
  actual_acceptance_date   DATE NULL,
  actual_handover_date     DATE NULL,
  -- 使用统计
  usage_count              INT DEFAULT 0,
  last_maintenance_date    DATE NULL,
  next_maintenance_threshold INT NULL,
  -- 封存
  is_sealed                BOOLEAN DEFAULT FALSE,
  sealed_at                DATETIME NULL,
  -- 审计
  created_by               BIGINT NOT NULL,
  created_at               DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at               DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  version                  INT DEFAULT 0,
  INDEX idx_project (project_id),
  INDEX idx_batch (batch_id),
  INDEX idx_status (current_status),
  INDEX idx_parent_fixture (parent_fixture_id),
  CONSTRAINT fk_parent_fixture FOREIGN KEY (parent_fixture_id) REFERENCES fixtures(id)
)
-- 约束：不暴露 DELETE 接口，报废走状态机 SCRAPPED
;
```

**[V1.2 业务规则确认补充] 加开-加量批次的版本号继承：**

加开-加量复制源治具时，**新治具的 `current_version_code` 直接继承源治具的当前有效版本号**（不重置为 A1）。例如源治具是 `EGL-FB-YN#1-A2`，加开复制后是 `EGL-FB-YN#2-A2`。这与"图纸是同一份"的业务逻辑一致。

`code_generator` 实现：

```python
def generate_addon_copy_code(source_fixture, target_batch):
    project = source_fixture.project
    type_code = source_fixture.fixture_type_code
    # 套号：项目+类型维度内最大套号 +1
    max_set_no = db.session.query(func.max(Fixture.set_no)).filter_by(
        project_id=project.id, fixture_type_code=type_code
    ).scalar() or 0
    new_set_no = max_set_no + 1
    # ★ 版本号继承源治具当前版本（业务规则确认）
    new_version = source_fixture.current_version_code
    return f"{project.project_code}-{type_code}#{new_set_no}-{new_version}"
```

### 2.4 快照机制：方案 A（复制型 + 追加同步）

(同 V1.1)

### 2.5 状态机历史表

(同 V1.1，含 FK 与 idx_operator 索引)

### 2.6 审批流数据模型

(同 V1.1)

### 2.7 甘特图字段与计划日期推算

(同 V1.1，PM 显式触发"基于此节点重算后续")

### 2.8 审计日志表 [V1.2 修订：operator_id 不加 FK]

```sql
CREATE TABLE audit_logs (
  id              BIGINT PRIMARY KEY AUTO_INCREMENT,
  table_name      VARCHAR(50) NOT NULL,
  record_id       BIGINT NOT NULL,
  action          ENUM('create','update','delete','force_status',
                       'sync_snapshot','cancel') NOT NULL,
  field_name      VARCHAR(50) NULL,
  old_value       TEXT NULL,
  new_value       TEXT NULL,
  -- ★ V1.2 决策：不加 FK 约束，应用层保证
  -- 用户离职时只能 is_active=FALSE，不允许物理删除
  -- 审计日志的 operator_id 永远有有效用户引用
  operator_id     BIGINT NOT NULL,
  reason          TEXT NULL,
  created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_record (table_name, record_id, created_at),
  INDEX idx_operator (operator_id, created_at)
);
```

**配套约束（写入 `users` 表 DDL）：**

```sql
CREATE TABLE users (
  id          BIGINT PRIMARY KEY AUTO_INCREMENT,
  username    VARCHAR(50) UNIQUE NOT NULL,
  ...
  is_active   BOOLEAN DEFAULT TRUE,        -- 离职/禁用走此字段
  -- 不暴露 DELETE 接口，禁用走 is_active=FALSE
);
```

**业务约束（写入 CLAUDE.md）：** 用户表只允许停用（`is_active=FALSE`），不允许物理删除。否则审计日志会出现悬空 operator_id。

### 2.9 乐观锁（双层）

(同 V1.1)

### 2.10 告警状态去重表

(同 V1.1)

### 2.11 采购订单一对多设计

(同 V1.1)

---

## 三、后端模块划分

### 3.1 目录结构 [V1.2 修订：新增导出指南文档]

```
backend/
├── CLAUDE.md
├── TASKS.md
├── docs/
│   ├── 00_open_questions.md            # 待确认事项
│   ├── 01_requirement_v2.1.md
│   ├── 02_coding_rules_v1.0.md
│   ├── 03_architecture_v1.2.md         # 本文档
│   ├── 04_api_spec.md
│   ├── 05_permissions.md
│   ├── 06_restore_procedure.md
│   └── 07_export_guideline.md          # ★ V1.2 新增：报表导出三档策略
├── ...
├── app/
│   ├── ...
│   ├── services/
│   │   ├── ...
│   │   ├── code_generator.py           # 加开复制版本继承逻辑
│   │   ├── export_service.py           # ★ V1.2 新增：导出服务
│   │   └── notification_service.py     # ★ V1.2 新增：审批通知（MVP 邮件）
│   ├── tasks/
│   │   ├── scheduler_runner.py
│   │   ├── alert_checker.py            # 紧急阈值 3 天
│   │   └── mail_sender.py
│   └── ...
└── ...
```

### 3.2 核心 API 端点 [V1.2 修订：移除核心表 DELETE，新增 cancel/export]

```
# 项目（无 DELETE）
GET    /api/projects
POST   /api/projects
GET    /api/projects/:id
PUT    /api/projects/:id
PATCH  /api/projects/:id/cancel              ★ V1.2 新增：作废
PUT    /api/projects/:id/owner
GET    /api/projects/:id/gantt?batch_id=
POST   /api/projects/:id/sync-templates
GET    /api/projects/export?ids=&format=xlsx ★ V1.2 新增：列表导出

# 批次（无 DELETE）
POST   /api/batches
GET    /api/batches/:id
PUT    /api/batches/:id
PATCH  /api/batches/:id/cancel               ★ V1.2 新增
GET    /api/batches/:id/fixtures
GET    /api/batches/:id/gantt

# 模治具（无 DELETE，作废走状态机 SCRAPPED）
POST   /api/fixtures
GET    /api/fixtures
GET    /api/fixtures/:id
PUT    /api/fixtures/:id
PATCH  /api/fixtures/:id/status
POST   /api/fixtures/:id/version-bump
POST   /api/fixtures/:id/copy-to-batch
POST   /api/fixtures/batch-seal
POST   /api/fixtures/:id/release-seal
POST   /api/fixtures/:id/force-status
POST   /api/fixtures/:id/recalc-dates
GET    /api/fixtures/export?...&format=xlsx  ★ V1.2 新增

# 采购（无 DELETE）
POST   /api/purchase-orders
POST   /api/purchase-orders/:id/items
GET    /api/purchase-orders/:id

# 业务单据（无 DELETE，全部走对应状态）
POST   /api/iqc-reports
POST   /api/acceptance-reports
POST   /api/install-records
POST   /api/maintenance-records
POST   /api/repair-records
POST   /api/scrap-records
...

# 审批流
POST   /api/approvals
GET    /api/approvals/my-pending
PUT    /api/approval-steps/:id

# 系统管理（用户允许 PATCH 禁用，不允许 DELETE）
GET    /api/admin/users
POST   /api/admin/users
PUT    /api/admin/users/:id
PATCH  /api/admin/users/:id/deactivate       ★ V1.2 新增：禁用账号
PATCH  /api/admin/users/:id/activate         ★ V1.2 新增：恢复账号
# ✗ DELETE /api/admin/users/:id              ★ 不提供
```

### 3.3 状态机核心逻辑 [V1.2 修订：业务确认开放报废路径 + trigger 笔误修正]

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

TRANSITIONS = {
    S.PENDING_IQC: {
        S.IQC_INSPECTING:    'normal',
        S.EMERGENCY_PENDING: 'emergency_auth',
    },
    S.IQC_INSPECTING: {
        S.INSTALLING:          'iqc_pass',
        S.CONCESSION_ACCEPTED: 'concession_approved',
        S.PENDING_IQC:         'return_repair',
    },
    S.EMERGENCY_PENDING: { S.INSTALLING: 'normal' },
    S.CONCESSION_ACCEPTED: { S.INSTALLING: 'normal' },
    S.INSTALLING: { S.ACCEPTANCE_TESTING: 'normal' },
    S.ACCEPTANCE_TESTING: {
        S.IN_STOCK:    'acceptance_pass',
        # ★ V1.2 修订：trigger 改为 'normal'，与 reject() 路径完全分离
        # reject 走 reject_fallback 通道，不走 TRANSITIONS 校验
        # 此 'normal' 通道用于"审批后让步通过仍需返工"等显式正向场景
        S.INSTALLING:  'normal',
        # ★ V1.2 业务确认：试产不合格三部门联合决策可直接判报废
        S.SCRAPPED:    'acceptance_fail_scrap',
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
    S.MAINTAINING:  { S.IN_STOCK: 'normal' },
    S.REPAIRING:    { S.IN_STOCK: 'normal' },
    S.SEALED:       { S.IN_STOCK: 'release_seal' },
    S.SCRAPPED:     {},                                 # 终态
}

# 驳回回退（不走 TRANSITIONS 校验，由 reject() 自行处理）
REJECT_FALLBACK = {
    S.IQC_INSPECTING:      S.PENDING_IQC,
    S.ACCEPTANCE_TESTING:  S.INSTALLING,
}

class StateMachineError(Exception): pass

def transition(fixture, to_status, trigger, operator_id,
               reason=None, related=None, force=False):
    from app.models import FixtureStatusHistory, db
    from_status = fixture.current_status
    if not force:
        allowed = TRANSITIONS.get(from_status, {})
        if to_status not in allowed:
            raise StateMachineError(f"非法状态转换：{from_status} -> {to_status}")
        if allowed[to_status] != trigger:
            raise StateMachineError(
                f"触发器不匹配：期望 {allowed[to_status]}，实际 {trigger}"
            )
    history = FixtureStatusHistory(
        fixture_id=fixture.id,
        from_status=from_status,
        to_status=to_status,
        trigger_type='forced' if force else trigger,
        reason=reason,
        related_table=related[0] if related else None,
        related_id=related[1] if related else None,
        operator_id=operator_id,
    )
    db.session.add(history)
    if force:
        from app.services.audit_service import log_force_action
        log_force_action(fixture, from_status, to_status, operator_id, reason)
    fixture.current_status = to_status
    return fixture

def reject(fixture, operator_id, reason):
    """审批驳回 → 回退到流程入口前状态"""
    fallback = REJECT_FALLBACK.get(fixture.current_status)
    if not fallback:
        raise StateMachineError(f"{fixture.current_status} 不支持驳回回退")
    return transition(fixture, fallback, 'rejected_fallback',
                       operator_id, reason=reason, force=True)
    # ★ V1.2 注：reject 用 force=True 绕过 TRANSITIONS 校验
    # 因为 'rejected_fallback' 不在 TRANSITIONS 任何 trigger 里，但仍记录到历史
```

**[V1.2 业务规则] 试产不合格三部门评审的处置选项现在包括：**
1. 返供应商整改 → 状态回退到 `INSTALLING`（reject 路径）
2. 内部修模 → 状态回退到 `INSTALLING`（reject 路径）
3. 重新设计 → 状态回退到 `INSTALLING`（reject 路径）+ 设计工程师后续走升版
4. 让步试用 → `transition` 正向通过（acceptance_pass 走 `IN_STOCK`，备注让步）
5. **直接报废** → `transition(... 'acceptance_fail_scrap')` → `SCRAPPED`（V1.2 新增）

实际选哪条由 `decision_type` 决定，在审批回调 handler 中分发。

### 3.4 审批流实现 [V1.2 修订：并行审批分支 + 通知策略]

```python
# app/services/approval_service.py

def initiate_approval(approval_type, business, steps_config, initiator_id,
                      flow_mode='sequential'):
    approval = Approval(
        approval_type=approval_type,
        business_table=business.__tablename__,
        business_id=business.id,
        flow_mode=flow_mode,                  # ★ 显式传入
        initiator_id=initiator_id,
    )
    db.session.add(approval)
    db.session.flush()
    for cfg in steps_config:
        db.session.add(ApprovalStep(approval_id=approval.id, **cfg))
    db.session.commit()

    # ★ V1.2 修订：并行模式时通知所有审批人，顺序模式仅通知第一个
    if flow_mode == 'parallel':
        notify_all_approvers(approval)
    else:
        notify_next_approver(approval)
    return approval


def decide_step(step_id, approver_id, decision, decision_type=None, comment=None):
    """
    [V1.2 修订] 同时支持顺序和并行两种 flow_mode
    """
    step = ApprovalStep.query.get(step_id)
    approval = step.approval

    # 校验当前用户有权审批此步骤
    if approval.flow_mode == 'sequential':
        # 顺序模式：必须是当前待审步骤
        current = next_pending_step(approval)
        if current.id != step.id:
            raise BusinessError("非当前审批步骤，无权操作")
    else:
        # 并行模式：本步骤未完成即可
        if step.decision != 'pending':
            raise BusinessError("该步骤已完成审批")

    step.approver_id = approver_id
    step.decision = decision
    step.decision_type = decision_type
    step.comment = comment
    step.decided_at = datetime.now()

    if decision == 'rejected':
        # ★ 不论顺序还是并行，任一人驳回 → 整体 rejected
        approval.status = 'rejected'
        approval.finished_at = datetime.now()
        on_approval_rejected(approval, decision_type, comment)
    else:
        if approval.flow_mode == 'parallel':
            # ★ 并行模式：检查所有步骤是否都已通过
            all_approved = all(
                s.decision == 'approved'
                for s in approval.steps
            )
            if all_approved:
                approval.status = 'approved'
                approval.finished_at = datetime.now()
                on_approval_approved(approval)
            # 否则继续等待其他审批人
        else:
            # 顺序模式：找下一个未审批步骤
            next_step = next_pending_step(approval, exclude_id=step.id)
            if next_step is None:
                approval.status = 'approved'
                approval.finished_at = datetime.now()
                on_approval_approved(approval)
            else:
                notify_next_approver(approval)

    db.session.commit()
```

#### 审批通知策略 [V1.2 明确]

```python
# app/services/notification_service.py
"""
[V1.2 决策] MVP 阶段通知统一为邮件。
后续如需系统内通知中心，新建 notifications 表，本模块改为双通道发送。
不在 MVP 引入额外复杂度。
"""
from app.tasks.mail_sender import send_mail_async

def notify_next_approver(approval):
    """顺序模式：通知当前待审步骤的审批人"""
    step = next_pending_step(approval)
    if not step:
        return
    recipient = resolve_approver(step.approver_role, approval.business_id)
    send_mail_async(
        to=recipient.email,
        subject=f"[模治具系统] 您有一项 {approval_type_label(approval)} 审批待处理",
        body=build_approval_mail_body(approval, step),
    )

def notify_all_approvers(approval):
    """并行模式：审批发起时同时通知所有人"""
    for step in approval.steps:
        recipient = resolve_approver(step.approver_role, approval.business_id)
        send_mail_async(to=recipient.email, ...)

def notify_purchase_to_return(approval):
    """IQC 退货返修通知采购"""
    recipients = [u.email for u in get_users_by_role('purchase')]
    send_mail_async(to=recipients, ...)
```

#### 审批场景与 flow_mode 配置

| 审批场景 | flow_mode | 步骤 | 备注 |
|----------|-----------|------|------|
| IQC 不合格三方审批 | `sequential` | PM → 设计 → ME | 业务流程文件明确顺序 |
| 试产不合格三部门评审 | `sequential` | PM → 设计/ME → 质量 | 由 PM 召集 |
| 报废三方会签 | **`parallel`** | PM + 生产部负责人 + 业务工程师 | 业务流程文件描述为"会签"，并行更高效 |
| 手动版解封 | `sequential` | PM → 生产主管 | 简单两步 |
| 紧急上机授权 | `sequential` | PM → 质量部 IQC | 需先有需求才能授权 |

### 3.5 文件上传

(同 V1.1，注：附件大小不强制限制，由 Config 配置)

```python
# app/config.py
class Config:
    UPLOAD_BASE = '/app/uploads'
    UPLOAD_MAX_SIZE = 0           # ★ V1.2 业务规则：0 = 不限制
    UPLOAD_ALLOWED_EXT = {'jpg','jpeg','png','pdf','heic','mp4','mov'}
    USE_XACCEL_REDIRECT = False   # MVP 关闭，Phase 7 开启
```

```python
# app/services/upload_service.py
def save_attachment(file, ...):
    if Config.UPLOAD_MAX_SIZE > 0:
        # 仅当 MAX_SIZE>0 时才校验
        size = ...
        if size > Config.UPLOAD_MAX_SIZE:
            raise ValidationError("附件超过限制")
    ...
```

**[V1.2 业务确认] 单个治具附件总大小不限制**——但需在 docs/ 中说明：
- 备份系统会扫描 uploads 目录大小，每周生成报告邮件给超管
- 若发现某治具附件累积过大（如 >1GB），由超管手动评估清理

### 3.6 邮件告警 [V1.2 业务规则：紧急阈值 3 天]

```python
# app/tasks/alert_checker.py
URGENT_THRESHOLD_DAYS = 3   # ★ V1.2 业务确认：量产版距交期 3 天内视为紧急

def register_jobs(scheduler):
    scheduler.add_job(check_all_alerts, 'cron', hour=8, minute=0,
                      id='check_alerts', replace_existing=True)

def check_all_alerts():
    check_po_overdue()             # 已逾期
    check_po_urgent()              # 距交期 ≤3 天
    check_maintenance_due()
    check_acceptance_overdue()
    check_planned_date_yellow()

def check_po_urgent():
    """量产版批次距交期 ≤3 天预警（区别于已逾期）"""
    threshold = date.today() + timedelta(days=URGENT_THRESHOLD_DAYS)
    fixtures = Fixture.query.join(Batch).filter(
        Batch.batch_type == 'mass_prod',
        Fixture.actual_arrival_date.is_(None),
        Fixture.planned_arrival_date <= threshold,
        Fixture.planned_arrival_date > date.today(),    # 排除已逾期
    ).all()
    for f in fixtures:
        send_alert_dedup(
            alert_type='po_urgent',
            target_table='fixtures', target_id=f.id,
            recipients=[f.project.owner.email, ...],
            subject=f"[紧急] {f.fixture_code} 距交期不足 3 天",
            body=...,
        )
```

**告警去重必测场景：**
1. 首次触发 → 发送
2. 同日相同 alert_type+target 再次触发 → 跳过
3. `is_active=FALSE` 后再次触发 → 重新发送并激活
4. 跨日触发同一 alert → 发送
5. 不同 target_id 同 alert_type → 各自独立去重
6. **★ V1.2 新增：状态从 `po_urgent` 升级为 `po_overdue` → 不同 alert_type，独立发送**

### 3.7 [V1.2 新增] 报表导出三档策略

详见 `docs/07_export_guideline.md`，核心规则：

| 场景 | 方案 | 实现位置 |
|------|------|----------|
| 单表列表 < 1000 条 | **前端 xlsx 库** | 浏览器内 JSON → Excel，后端无感知 |
| 多表关联 / >1000 条 | **后端流式响应** | `services/export_service.py` + `yield` + `StreamingResponse` |
| 月度大报表 | **scheduler 容器后台生成** | 每月 1 日凌晨跑，结果存 `attachments`，超管下载 |

后端流式导出骨架（避免内存堆积）：

```python
# app/services/export_service.py
import openpyxl

def export_fixtures_streaming(filters):
    """
    使用 openpyxl write_only 模式 + Flask 流式响应
    内存占用恒定，与数据量无关
    """
    wb = openpyxl.Workbook(write_only=True)
    ws = wb.create_sheet("Fixtures")
    ws.append(['编码','项目','批次','类型','状态','计划到货','实际到货'])

    # 分页查询，避免一次性加载全部
    page_size = 500
    page = 0
    while True:
        rows = Fixture.query.filter_by(**filters).limit(page_size).offset(
            page * page_size).all()
        if not rows:
            break
        for r in rows:
            ws.append([r.fixture_code, r.project.project_code, ...])
        page += 1

    # 写入临时文件后流式发送
    import tempfile
    tmp = tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False)
    wb.save(tmp.name)
    return tmp.name
```

**约束写入 CLAUDE.md：** AI 在生成导出代码时禁止使用 `pandas.to_excel(io.BytesIO())` 或 `openpyxl` 默认模式（非 write_only），否则大数据量会 OOM。

---

## 四、前端模块划分

### 4.1 目录结构与路由

(同 V1.1)

### 4.2 关键组件设计建议 [V1.2 修订：新增导出按钮]

| 组件 | 关键设计点 |
|------|------------|
| `StatusTag.vue` | 输入 status code，输出带颜色和文案的 el-tag |
| `AttachmentUploader.vue` | 封装 el-upload，处理 multipart 上传 |
| `PermissionButton.vue` | 内部 v-if 判断当前用户角色权限 |
| `ApprovalDrawer.vue` | 通用审批侧抽屉，**支持顺序/并行两种 flow_mode 展示** |
| `GanttChart.vue` | Frappe Gantt 包装；任务数 >100 自动降级到批次视图 |
| `StatusHistoryTimeline.vue` | el-timeline 展示状态变更历史 |
| `DateCascadeButton.vue` | "基于此节点重算后续"按钮 |
| `CancelButton.vue` | **★ V1.2 新增**：作废按钮，二次确认 + 必填原因 |
| `ExportButton.vue` | **★ V1.2 新增**：列表导出按钮，<1000 条前端导，否则触发后端流式 |

### 4.3 甘特图技术选型与降级

(同 V1.1)

### 4.4 12 状态颜色映射

(同 V1.1)

### 4.5 权限控制 + axios 拦截器 [V1.2 修订：补充时区注释]

```javascript
// frontend/src/api/request.js
import axios from 'axios'
import { ElMessageBox } from 'element-plus'
import dayjs from 'dayjs'                     // ★ V1.2 新增：前端统一时区
import utc from 'dayjs/plugin/utc'
import timezone from 'dayjs/plugin/timezone'
dayjs.extend(utc); dayjs.extend(timezone)
dayjs.tz.setDefault('Asia/Shanghai')

const request = axios.create({ baseURL: '/api', timeout: 15000 })

request.interceptors.response.use(
  (resp) => resp,
  async (err) => {
    const { response } = err
    if (response?.status === 409) {
      try {
        await ElMessageBox.alert(
          '该数据已被他人修改，请刷新页面后重试。',
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

**前端时区约定：** 后端返回的 datetime 字段约定为 ISO 格式带时区（如 `2026-04-26T14:30:00+08:00`），前端用 dayjs 解析并显示。**禁止前端用 `new Date()` 隐式解析无时区字符串**——会按浏览器本地时区误读。

---

## 五、开发路线图

### 5.1 模块开发顺序 [V1.2 修订：Phase 0 强化时区验证]

```
Phase 0 — 基建（1 周）
  ├─ ★ V1.2 强化：部署环境 + 时区验证清单
  │   □ 目标服务器是否能跑 Docker？(Windows Server 确认 Hyper-V/WSL2)
  │   □ 端口、卷挂载、镜像拉取畅通？
  │   □ 公司 SMTP 服务能从容器内访问？
  │   □ docker exec backend date 输出北京时间？
  │   □ docker exec scheduler date 输出北京时间？
  │   □ docker exec mysql date 输出北京时间？
  │   □ MySQL: SELECT NOW(), @@global.time_zone, @@session.time_zone 全为北京时间/+08:00？
  │   □ Python 写入: SELECT NOW() 与容器 date 一致？
  │   □ JWT 过期时间在 config 中显式 timedelta 配置？
  │   □ APScheduler 实例化时显式 timezone='Asia/Shanghai'？
  │   全部✅再进 Phase 1
  ├─ Docker Compose 五容器 + 时区四处联动
  ├─ Flask app factory + extensions + 配置
  ├─ 用户/角色模型（含 is_active 软删机制）+ JWT 登录
  ├─ 通用响应/异常/装饰器
  └─ Vue 项目初始化（含 dayjs 时区配置）

Phase 1 — 基础数据（1 周）
  ├─ 治具模板库 CRUD（is_active 软停用）
  ├─ 供应商库 CRUD（is_active 软停用）
  ├─ 系统字典
  └─ 用户管理 CRUD（PATCH activate/deactivate，无 DELETE）

Phase 2 — 核心业务主线（3-4 周）⭐ MVP 关键路径
  ├─ 项目管理 CRUD（含 cancel 接口，无 DELETE）
  ├─ 模板快照创建 + 追加同步
  ├─ 需求批次（含 parent_batch_id, cancel 接口）
  ├─ 模治具创建 + 编码生成
  │   · 加开-加量版本号继承业务规则
  │   · parent_fixture_id 复制路径
  ├─ 状态机服务 + 状态历史（含完整单元测试）
  │   · 含 ACCEPTANCE_TESTING → SCRAPPED 路径
  ├─ 采购订单（头/明细分离）+ 计划日期推算
  └─ 列表/详情页 + 状态 Tag + 作废按钮

Phase 3 — 流程节点（2-3 周）
  ├─ IQC 标准路径
  ├─ 紧急上机路径
  ├─ 安装调试 + 试产验收
  ├─ 移交接收 + 货架绑定
  └─ 附件上传（MVP：send_from_directory，无大小限制）

Phase 4 — 审批流（1-2 周）
  ├─ 审批服务（顺序+并行双模式 + 驳回）
  ├─ 审批通知（MVP 邮件实现）
  ├─ IQC 不合格三方审批（sequential）
  ├─ 试产不合格三部门评审（sequential，含报废分支）
  ├─ 报废三方会签（parallel）
  └─ 我的待审 + 审批侧抽屉

Phase 5 — 使用与维保（1-2 周）
  ├─ 领用/归还
  ├─ 封存/解封（不影响货架绑定）
  ├─ 保养记录 + 阈值检测
  └─ 维修记录

Phase 6 — 可视化与告警（1-2 周）
  ├─ 甘特图（项目/批次两层 + 100+ 自动降级）
  ├─ 独立 scheduler 容器 + APScheduler
  ├─ 告警去重表 + 必测场景全覆盖
  ├─ 紧急阈值 3 天告警（po_urgent）
  ├─ "基于此节点重算后续"按钮
  └─ 成本统计页

Phase 7 — 系统化与上线（1 周）
  ├─ 审计日志页
  ├─ 超管强制跳转入口
  ├─ ★ 报表导出（三档策略：前端导/后端流式/月度后台）
  ├─ 备份脚本 + 还原演练
  ├─ Nginx X-Accel-Redirect 切换（如需要）
  └─ 部署文档 + 用户手册
```

**总工期估算：12-16 周**

### 5.2 阶段里程碑

(同 V1.1，M0 验收新增：完成时区四处联动验证)

### 5.3 CLAUDE.md 结构建议 [V1.2 增补本系统专属规则]

```markdown
## 本系统专属规则（V1.2 完整版）

### 时区与时间
- 所有容器统一 TZ=Asia/Shanghai；MySQL 必须 default-time-zone='+08:00'
- SQLAlchemy 连接串必须 init_command='SET time_zone=+08:00'
- JWT 过期时间用 timedelta 显式配置
- APScheduler 实例化时显式 timezone='Asia/Shanghai'
- 前端统一 dayjs.tz.setDefault('Asia/Shanghai')；禁止 new Date() 解析无时区字符串

### 删除策略
- 核心业务表（projects/batches/fixtures/purchase_orders 及所有业务单据）禁止暴露 HTTP DELETE
- projects/batches 作废走 status='cancelled'
- fixtures 作废走状态机 SCRAPPED
- 用户/供应商/模板用 is_active=FALSE 停用
- 真·删除仅 scripts/reset_db.py 提供，不暴露 API

### 状态机
- 状态变更必须走 services/state_machine.py 的 transition() 或 reject()
- 不允许直接改 fixture.current_status
- 改流程必须同步：state_machine.py / status_history 表 / 前端 status.js / i18n / 文档

### 编码与版本
- 编码生成必须走 services/code_generator.py
- 加开-加量复制时 current_version_code 继承源治具，不重置 A1
- 版本升级 A1→A2：改 fixtures.current_version_code + drawings 追加，不新建 fixture
- 加开复制 #1→#2：新建 fixture + parent_fixture_id 指向源

### 审批流
- 所有审批走 services/approval_service.py
- 报废会签 flow_mode='parallel'，其他场景 'sequential'
- approved/rejected 都要传 decision_type
- 通知统一走 services/notification_service.py（MVP 邮件实现）

### 快照
- 项目创建时一次性生成；如需追加新模板走 sync_missing_templates() 写审计

### 附件
- 大小默认不限制（业务规则）；可通过 Config.UPLOAD_MAX_SIZE 配置
- 落盘相对 /app/uploads，DB 只存 relative_path
- 下载经鉴权 endpoint，禁止 nginx 直接暴露 uploads 目录

### 调度器
- ★ 永远不要在 backend 容器中初始化 APScheduler
- 只在独立 scheduler 容器的 scheduler_runner.py 入口启动

### 并发
- PUT/PATCH 必须包含 version 字段；service 层手动校验 + ORM 自动校验双保险
- 全局异常处理器捕获 StaleDataError 返回 409

### 报表导出
- < 1000 条用前端 xlsx 库导出
- > 1000 条或多表关联走 services/export_service.py 流式响应
- 禁止 pandas.to_excel(BytesIO()) 或 openpyxl 非 write_only 模式
- 月度大报表由 scheduler 后台生成，结果存 attachments 表

### 邮件告警
- 必须经 send_alert_dedup() 去重
- 紧急阈值 URGENT_THRESHOLD_DAYS=3（业务规则）
```

### 5.4 独立 AI 辅助开发的风险点 [V1.2 修订]

(在 V1.1 基础上新增 3 条)

| 风险 | 缓解措施 |
|------|----------|
| **★ 时区错乱** | Phase 0 验证清单全部通过才进 Phase 1；CLAUDE.md 时区规则写明四处联动 |
| **★ AI 自由发挥加 DELETE 端点** | CLAUDE.md 明确禁止；代码 review 时全文搜 `DELETE` `methods=` 做检查 |
| **★ 大数据量导出 OOM** | CLAUDE.md 明确禁止 pandas.to_excel + openpyxl 默认模式 |
| 状态机/审批流改动失控 | 先写测试再写实现；流程节点变更先写文档再实现 |
| 数据库迁移不可逆错误 | 严格 Schema-First；上线前必备份；migration 必须人工 review |
| AI 生成代码隐藏 Bug | 关键路径必须有单元测试 |
| 过度设计倾向 | 看到 AI 提"也许可以加…"先问：MVP 真的需要吗？ |
| 跨模块改动遗漏 | 改状态机时同步检查 5 处 |
| 附件目录权限问题 | Dockerfile 显式 chown 对齐宿主机 |
| 乐观锁未覆盖 | 高频写入表带 version + ORM `__mapper_args__` |
| 邮件配置生产失败 | 开发期 MailHog；生产前单独测 send_email() |
| 备份从未验证 | 上线前完整还原演练；每月抽查 |
| 权限矩阵前后端不一致 | 派生自 docs/05_permissions.md |
| Scheduler 误回 backend 容器 | 永远不在 Flask app factory 中 scheduler.start()；只在 scheduler_runner.py 启动 |

---

## 六、附：关键决策一览表 [V1.2 修订]

| # | 决策点 | 选择 | 一句话理由 |
|---|--------|------|------------|
| 1 | 整体架构 | 单体 Flask + Vue SPA + Docker Compose（5 容器） | 50 人规模无微服务必要 |
| 2 | 异步任务 | 独立 scheduler 容器 | 避免多 worker 并发陷阱 |
| 3 | **时区** | **TZ + MySQL + SQLAlchemy + JWT + APScheduler 五处联动** | **少配一处即写错时间** |
| 4 | **核心表删除** | **禁止 HTTP DELETE，作废走状态字段** | **制造业资产数据不可丢** |
| 5 | 快照机制 | 复制型 + 追加同步 | 简单直观 + 应对长周期演进 |
| 6 | 审批流模型 | 多场景共用 + 顺序/并行双模式 | 一套引擎覆盖所有场景 |
| 7 | 审批通知 | MVP 邮件统一实现 | 避免 AI 自由发挥引入额外模块 |
| 8 | 状态机实现 | 字典 + transition() 函数 | 可测试、可枚举 |
| 9 | 试产不合格→报废 | 开放（业务确认） | 业务规则明确 |
| 10 | 编码生成 | 后端服务 + 加开继承当前版本 | 与图纸一致性符合 |
| 11 | 版本升级语义 | 改字段 + drawings 追加；不新建 fixture | 实物不变图纸演进 |
| 12 | 加开复制语义 | 新建 fixture + parent_fixture_id 溯源 | 套号递增可追溯 |
| 13 | 文件存储 | 宿主机挂载 + 鉴权下发；预留 X-Accel-Redirect | 简单 + 后期可升级 |
| 14 | 附件大小限制 | 默认不限（业务确认）；周报告监控 | 避免影响业务上传现场图 |
| 15 | 甘特图库 | Frappe Gantt + 100+ 降级 | 轻量 + 大数据量友好 |
| 16 | 状态颜色 | 自定义 :color，5 type 不够 | 12 状态需视觉区分 |
| 17 | 权限实现 | 后端字典 + 前端按钮 + 派生自单一文档 | 避免前后端偏移 |
| 18 | 告警去重 | alerts 表 + 每日窗口；紧急阈值 3 天 | 避免邮件轰炸 |
| 19 | 报表导出 | 三档策略（前端/流式/后台） | 从源头规避 OOM |
| 20 | 备份方案 | 独立 backup 容器 + 还原演练制度 | 容器化最简方案 |
| 21 | 乐观锁 | 手动校验 + ORM 自动 双层 | 双保险 |
| 22 | 采购订单关系 | PO 头 + items 一对多 | 反映"一单多治具" |
| 23 | 计划日期级联 | 默认不级联，"重算后续"按钮 | 既精确又方便 |
| 24 | 409 处理 | axios 拦截器统一弹窗刷新 | 避免每个组件重复处理 |
| 25 | 用户软删 | is_active=FALSE，无 DELETE | 保审计日志完整 |

---

## 七、文件修订记录

| 版本 | 日期 | 修订内容 | 修订人 |
|------|------|----------|--------|
| V1.0 | 2026-04-26 | 初版发布 | Claude (Opus) |
| V1.1 | 2026-04-26 | 第一轮审阅 14 处修订（独立 scheduler、parent_fixture_id、追加快照同步、purchase_order_items、级联日期、双层乐观锁、approved 透传 decision_type、X-Accel-Redirect 预留、axios 409 拦截、甘特图降级、状态机 trigger 待业务确认等）| Claude (Opus) |
| **V1.2** | **2026-04-26** | **第二轮审阅 9 处修订 + 业务确认 5 处落地：** ① 时区四处联动（docker-compose / SQLAlchemy 连接串 / JWT timedelta / APScheduler）+ Phase 0 验证清单 ② 核心业务表禁止 HTTP DELETE，projects/batches 加 cancelled 状态 ③ 审批流 decide_step 增加并行模式分支（all_approved 判定）④ 报表导出三档策略（docs/07_export_guideline.md）⑤ docker-compose MYSQL_DEFAULT_CHARSET 删除（非官方变量）⑥ ACCEPTANCE_TESTING→INSTALLING trigger 改 'normal' + reject 用 force=True 绕过 TRANSITIONS 校验 ⑦ 审批通知 MVP 统一邮件实现（services/notification_service.py）⑧ Phase 0 加 9 项时区验证清单 ⑨ audit_logs.operator_id 不加 FK，用户走 is_active 软删；**业务确认整合：** ① 试产不合格开放→SCRAPPED 路径（trigger=acceptance_fail_scrap）② 加开-加量继承 current_version_code ③ 紧急阈值 URGENT_THRESHOLD_DAYS=3 ④ 附件无大小限制 ⑤ 封存不影响货架绑定（注释明确） | Claude (Opus) |

---

> **本架构文档版本：V1.2**
> **后续若需变更：必须更新版本号 + 修订记录 + 同步到 docs/03_architecture.md**
> **项目代码仓库根目录的 CLAUDE.md 应永远引用本文档为权威架构来源。**

---

## 附录 A：仍待业务确认事项（V1.2 已清空 5 项）

| # | 事项 | 状态 |
|---|------|------|
| 1 | 试产不合格三部门评审是否包含"直接报废"？ | ✅ 已确认：包含 |
| 2 | 加开-加量批次治具是否继承原批次当前版本号？ | ✅ 已确认：继承 |
| 3 | 手动版封存物理隔离是否影响货架绑定？ | ✅ 已确认：不影响 |
| 4 | 量产版交期"紧急"判定阈值？ | ✅ 已确认：3 天 |
| 5 | 单个治具附件总大小是否限制？ | ✅ 已确认：不限制 |

**当前无待确认事项。** 后续若有新业务规则疑问，在 `docs/00_open_questions.md` 中维护。

---

## 附录 B：V1.2 必读检查清单

开发启动前请逐项确认：

- [ ] 已阅读 V1.2 全文，理解时区四处联动配置
- [ ] 已理解核心表禁止 DELETE 的设计原则
- [ ] 已理解版本升级 vs 加开复制的两种语义边界
- [ ] 已理解审批流顺序模式 vs 并行模式的差异
- [ ] 已规划 Phase 0 时区验证清单为强制门禁
- [ ] CLAUDE.md 中已写入"本系统专属规则（V1.2 完整版）"
- [ ] docs/ 下已建立 00/04/05/06/07 占位文档
- [ ] 已为状态机 + 编码生成 + 审批流 + 告警去重 + 计划日期推算 5 个核心模块预留单元测试
