# DBU 模治具管理系统 — 系统架构设计方案 V1.3

> 配套文档:《DBU模治具全流程管控文件 V2.1》、《DBU模治具编码规则 V1.0》、《CLAUDE_reference_for_opus.md》
>
> 设计原则:**清晰分层 · 模块独立 · 可维护性优先 · 复杂度可控 · 兼容 Claude Code CLI 协作开发**
>
> **本版核心变更:部署方案由 Docker Compose 全栈容器化(V1.2)调整为混合部署。** 开发机 MySQL 容器化、Flask/Vue 本地运行;生产环境 Windows Server 原生部署(MySQL/Waitress/静态文件)。详见末尾「修订记录」。

---

## 一、整体架构设计

### 1.1 架构模式选择

**推荐:经典前后端分离 + 单体 Flask 后端 + 混合部署(开发 Docker MySQL + 生产 Windows Server 原生)**

| 维度 | 选择 | 理由 |
|------|------|------|
| 后端形态 | 单体 Flask(Modular Monolith) | 50 人内部使用、局域网部署,微服务过度设计 |
| 前端形态 | Vue 3 SPA + Element Plus | 与现有 vc-cost-system 一致 |
| 通信协议 | RESTful JSON over HTTP | 与现有规范一致 |
| **部署形态** | **混合部署(详见 1.3)** | **匹配开发者已有的 Windows Server 部署经验,Docker 学习成本高收益有限** |
| 生产 WSGI | **Waitress** | **Windows 友好,与现有 vc-cost-system 一致** |
| 认证 | JWT(Flask-JWT-Extended) | 与现有规范一致 |
| 异步任务 | **Flask-APScheduler 内嵌** | **单进程 Waitress 部署无并发陷阱** |

### 1.2 前后端职责划分

```
┌──────────────────────────┐         ┌─────────────────────────────┐
│       前端 (Vue 3)        │         │      后端 (Flask)            │
├──────────────────────────┤         ├─────────────────────────────┤
│ · 页面渲染、表单校验       │         │ · 业务逻辑(services/)        │
│ · 路由守卫、按钮级权限     │ ──API─▶ │ · 状态机校验                 │
│ · 数据可视化(甘特图/导出) │ ◀─JSON─ │ · 审批流流转                 │
│ · 文件上传(multipart)     │         │ · 编码自动生成               │
│                          │         │ · 权限校验(最终防线)         │
│                          │         │ · 文件落盘 / 大报表流式生成   │
│                          │         │ · 计划日期推算               │
│                          │         │ · 邮件告警调度(内嵌)         │
└──────────────────────────┘         └─────────────────────────────┘
```

**铁律:前端权限只用于"隐藏不该看到的按钮和菜单",后端必须独立做权限校验。**

### 1.3 混合部署方案 [V1.3 全新章节]

#### 部署形态总览

```
┌─────────────────────────────────────────┐    ┌──────────────────────────────────────┐
│ 本地开发机 (ThinkPad, Windows 11)        │    │ 公司服务器 (Windows Server)           │
├─────────────────────────────────────────┤    ├──────────────────────────────────────┤
│ ① Vue Dev Server (pnpm dev)             │    │ ① Vue 静态文件 (pnpm build → dist/)  │
│   localhost:5173 + Vite proxy /api      │    │   由 Flask 直接 serve 或 IIS 反代     │
│ ② Flask Dev (python run.py)             │    │ ② Flask + Waitress (Windows 服务)    │
│   localhost:5000                        │    │   localhost:5000                     │
│ ③ MySQL (Docker 容器, 已运行)            │    │ ③ MySQL (Windows 原生安装)           │
│   localhost:3306                        │    │   localhost:3306                     │
│ ④ APScheduler 内嵌 Flask 进程           │    │ ④ APScheduler 内嵌 Flask 进程        │
└─────────────────────────────────────────┘    └──────────────────────────────────────┘
```

#### 开发环境

**MySQL 维持 Docker 容器(已运行,不动)** — 开发机若没有 Docker MySQL 容器,可参考以下最小配置启动:

```bash
docker run -d --name dbu-mysql-dev \
  -e MYSQL_ROOT_PASSWORD=devpassword \
  -e MYSQL_DATABASE=dbu_fixture \
  -p 3306:3306 \
  -v dbu_mysql_data:/var/lib/mysql \
  mysql:8.4 \
  --character-set-server=utf8mb4 \
  --collation-server=utf8mb4_unicode_ci \
  --default-time-zone='+08:00'
```

**Flask 本地直跑:**

```bash
cd backend
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
python run.py            # Flask 内置开发服务器,debug=True
```

**Vue 本地直跑:**

```bash
cd frontend
pnpm install
pnpm dev                 # Vite Dev Server, HMR
```

`vite.config.js` 配置 API 代理:

```javascript
export default defineConfig({
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:5000',
        changeOrigin: true,
      },
      '/uploads': {
        target: 'http://localhost:5000',
        changeOrigin: true,
      }
    }
  }
})
```

#### 生产环境(Windows Server)

**部署组件:**

| 组件 | 安装方式 | 路径 / 端口 |
|------|----------|------------|
| Python 3.12 | 官方 Installer + 系统 PATH | `C:\Python312\` |
| MySQL 8.4 | MySQL Installer for Windows | `localhost:3306` |
| Flask 应用 | Git clone → venv → pip install | `C:\dbu\backend\` |
| Waitress | pip 安装 | 监听 `0.0.0.0:5000` |
| Vue 静态文件 | `pnpm build` 后拷贝 dist | `C:\dbu\frontend\dist\` |
| 附件目录 | 手动创建 | `D:\dbu\uploads\` |
| 备份目录 | 手动创建 | `D:\dbu\backup\` |

**Waitress 启动方式(生产):**

```python
# backend/serve.py — 生产入口,与现有 vc-cost-system 一致
from waitress import serve
from app import create_app
import os

os.environ.setdefault('FLASK_ENV', 'production')
app = create_app()

if __name__ == '__main__':
    serve(app, host='0.0.0.0', port=5000, threads=8)
```

**注册为 Windows 服务**(推荐 NSSM):

```powershell
nssm install DBU-Fixture-Backend "C:\Python312\python.exe" "C:\dbu\backend\serve.py"
nssm set DBU-Fixture-Backend AppDirectory "C:\dbu\backend"
nssm set DBU-Fixture-Backend AppStdout "C:\dbu\logs\stdout.log"
nssm set DBU-Fixture-Backend AppStderr "C:\dbu\logs\stderr.log"
nssm start DBU-Fixture-Backend
```

**Vue 静态文件 serve 方案(二选一):**

- **方案 A(MVP 推荐,与 vc-cost-system 一致):由 Flask 直接 serve**

  ```python
  # app/__init__.py
  app = Flask(__name__,
              static_folder='C:/dbu/frontend/dist',
              static_url_path='')

  @app.route('/', defaults={'path': ''})
  @app.route('/<path:path>')
  def serve_spa(path):
      if path and os.path.exists(os.path.join(app.static_folder, path)):
          return send_from_directory(app.static_folder, path)
      return send_from_directory(app.static_folder, 'index.html')   # SPA history mode
  ```

  优点:零依赖,Waitress 一并 serve;缺点:静态文件并发占用 Flask 线程

- **方案 B(后期可升级):IIS 作为反向代理**

  - IIS 监听 80 端口,直接 serve `C:\dbu\frontend\dist\`
  - `/api/*` 通过 URL Rewrite + ARR 反代到 `localhost:5000`
  - 当并发或大文件下载成为瓶颈时再切换

MVP 用方案 A,Phase 7 评估是否需要切到方案 B。

#### 配置管理(python-dotenv)

**环境变量分离,密码绝不入仓:**

```bash
# backend/.env.development      （仅开发机,不提交 git）
FLASK_ENV=development
DATABASE_URL=mysql+pymysql://root:devpassword@localhost:3306/dbu_fixture?charset=utf8mb4
JWT_SECRET=dev_jwt_secret_change_me
SMTP_HOST=localhost
SMTP_PORT=1025                          # MailHog
UPLOAD_BASE=./uploads
```

```bash
# backend/.env.production       （仅生产机,不提交 git）
FLASK_ENV=production
DATABASE_URL=mysql+pymysql://dbu_app:<生产密码>@localhost:3306/dbu_fixture?charset=utf8mb4
JWT_SECRET=<32 位随机串>
SMTP_HOST=smtp.company.com
SMTP_PORT=25
UPLOAD_BASE=D:/dbu/uploads
```

```bash
# backend/.env.example          （示例文件,提交 git,展示结构不含密码）
FLASK_ENV=development
DATABASE_URL=mysql+pymysql://USER:PASSWORD@localhost:3306/dbu_fixture?charset=utf8mb4
JWT_SECRET=please_change_me
...
```

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
    # ★ 全部从环境变量读取,绝不硬编码任何密码或密钥
    SQLALCHEMY_DATABASE_URI = os.environ['DATABASE_URL']
    SQLALCHEMY_ENGINE_OPTIONS = {
        "connect_args": {"init_command": "SET time_zone='+08:00'"},
        "pool_pre_ping": True,
    }
    JWT_SECRET_KEY = os.environ['JWT_SECRET']
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=8)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=7)

    UPLOAD_BASE = os.environ.get('UPLOAD_BASE', './uploads')
    UPLOAD_MAX_SIZE = 0                      # 0 = 不限制(业务规则)
    UPLOAD_ALLOWED_EXT = {'jpg','jpeg','png','pdf','heic','mp4','mov'}

    MAIL_SERVER = os.environ['SMTP_HOST']
    MAIL_PORT = int(os.environ.get('SMTP_PORT', 25))

    SCHEDULER_TIMEZONE = 'Asia/Shanghai'     # ★ APScheduler 时区显式设定
```

`.gitignore` 中务必加入:

```
.env.development
.env.production
.env.local
```

#### 时区处理(简化版)

**生产环境(Windows Server 原生):**
- Windows 系统时区 = Asia/Shanghai → MySQL Windows 服务自动继承 → 无需特殊配置
- Python `datetime.now()` 自动使用系统时区
- 唯一需显式配置的是 APScheduler:`BackgroundScheduler(timezone='Asia/Shanghai')`(在 Flask app 中初始化时传入)

**开发环境(Docker MySQL):**
- Docker 容器默认 UTC,**唯一需要修一处**:启动 MySQL 容器时加 `--default-time-zone='+08:00'`(见 1.3 启动命令)
- 或者在 SQLAlchemy 连接串中加 `init_command='SET time_zone=+08:00'`(已在 config.py 中)
- 两者任一即可,推荐都做以保险

**Phase 0 验证:** 开发机执行 `SELECT NOW()` 确认输出北京时间;生产机部署完执行同样检查。

### 1.4 备份与还原策略 [V1.3 修订:Windows Server 原生]

#### 备份目标与频率

| 对象 | 工具 | 频率 | 保留策略 | 存放位置 |
|------|------|------|----------|----------|
| MySQL 数据 | `mysqldump.exe` | 每天 02:00 | 每日 7 + 每周 4 + 每月 12 | `D:\dbu\backup\mysql\` |
| 附件目录 | `robocopy /MIR` | 每天 03:00 | 每日 7 | `D:\dbu\backup\uploads\` |
| 完整目录归档 | 7-Zip 命令行 | 每周一次 | 保留 4 周 | `D:\dbu\backup\snapshot\` |

#### 备份脚本示例

```batch
:: D:\dbu\scripts\backup_mysql.bat
@echo off
set BACKUP_DIR=D:\dbu\backup\mysql
set DATE_TAG=%date:~0,4%-%date:~5,2%-%date:~8,2%
set MYSQL_PWD=<密码,从 .env.production 读取或经过加密 Vault>

if not exist "%BACKUP_DIR%" mkdir "%BACKUP_DIR%"

"C:\Program Files\MySQL\MySQL Server 8.4\bin\mysqldump.exe" ^
  --default-character-set=utf8mb4 ^
  --single-transaction --routines --triggers ^
  -u root -p%MYSQL_PWD% ^
  dbu_fixture > "%BACKUP_DIR%\dbu_fixture_%DATE_TAG%.sql"

:: 删除 7 天前的备份
forfiles /P "%BACKUP_DIR%" /M *.sql /D -7 /C "cmd /c del @path" 2>nul

echo [%date% %time%] Backup completed >> D:\dbu\logs\backup.log
```

```batch
:: D:\dbu\scripts\backup_uploads.bat
@echo off
robocopy D:\dbu\uploads D:\dbu\backup\uploads /MIR /R:2 /W:5 ^
  /LOG+:D:\dbu\logs\backup_uploads.log
```

#### Windows 任务计划程序配置

```powershell
# PowerShell 创建任务(管理员执行)
schtasks /Create /SC DAILY /ST 02:00 /TN "DBU-Backup-MySQL" ^
  /TR "D:\dbu\scripts\backup_mysql.bat" /RU SYSTEM /F
schtasks /Create /SC DAILY /ST 03:00 /TN "DBU-Backup-Uploads" ^
  /TR "D:\dbu\scripts\backup_uploads.bat" /RU SYSTEM /F
schtasks /Create /SC WEEKLY /D MON /ST 04:00 /TN "DBU-Backup-Snapshot" ^
  /TR "D:\dbu\scripts\backup_snapshot.bat" /RU SYSTEM /F
```

#### 还原流程详见 `docs/06_restore_procedure.md`,核心步骤:

```batch
:: 1. 停 Flask 服务
nssm stop DBU-Fixture-Backend

:: 2. 还原 MySQL
"C:\Program Files\MySQL\MySQL Server 8.4\bin\mysql.exe" ^
  -u root -p<密码> dbu_fixture < D:\dbu\backup\mysql\dbu_fixture_2026-04-25.sql

:: 3. 还原附件
robocopy D:\dbu\backup\uploads D:\dbu\uploads /MIR

:: 4. 校验
mysql -u root -p<密码> dbu_fixture -e "SELECT COUNT(*) FROM fixtures;"

:: 5. 重启服务
nssm start DBU-Fixture-Backend
```

**还原演练制度:** 上线前必做 1 次完整还原;上线后每月抽查 1 次;每次重大升级前先备份再演练。

---

## 二、数据库设计方案(基于 MySQL 8.4)

> **本章节内容与 V1.2 完全一致**,部署方式变更不影响 Schema 设计。以下保留全部 DDL 与设计要点。

### 2.1 核心数据表清单(共 27 张)

| 模块 | 表名 | 用途 |
|------|------|------|
| **基础** | `users` | 用户账号(含 is_active 软删) |
| **基础** | `audit_logs` | 审计日志 |
| **基础** | `attachments` | 附件元数据 |
| **基础** | `alerts` | 告警状态去重表 |
| **项目** | `projects` | 项目主表(含 cancelled 状态) |
| **项目** | `batches` | 需求批次(含 cancelled 状态) |
| **模治具** | `fixtures` | 模治具主表(核心) |
| **模治具** | `fixture_status_history` | 状态变更历史 |
| **模治具** | `fixture_usage_records` | 领用归还流水 |
| **模板库** | `fixture_templates` | 模板库主表(is_active 软删) |
| **模板库** | `fixture_template_snapshots` | 项目维度模板快照 |
| **设计** | `drawings` | 图纸版本表(版本升级链记录在此) |
| **设计** | `dfm_reports` | DFM 报告(可选) |
| **采购** | `suppliers` | 供应商库(is_active 软删) |
| **采购** | `purchase_orders` | 采购订单头 |
| **采购** | `purchase_order_items` | 订单明细(一对多) |
| **质量** | `iqc_reports` | IQC 检验报告 |
| **质量** | `acceptance_reports` | 试产验收报告 |
| **质量** | `emergency_authorizations` | 紧急上机授权 |
| **生产** | `install_records` | 安装调试记录 |
| **生产** | `shelf_locations` | 货架库位 |
| **维保** | `maintenance_records` | 保养记录 |
| **维保** | `repair_records` | 维修记录 |
| **生命周期** | `scrap_records` | 报废记录 |
| **审批流** | `approvals` | 审批主表(支持 sequential/parallel) |
| **审批流** | `approval_steps` | 审批步骤明细 |
| **字典** | `system_dicts` | 系统字典 |

#### 核心约束:禁止物理删除

**核心业务表禁止暴露 HTTP DELETE 端点:**
- `projects` / `batches` 走 `status='cancelled'`
- `fixtures` 走状态机 `SCRAPPED`
- 业务单据(IQC/验收/保养/维修/报废)走对应状态
- `users` / `suppliers` / `fixture_templates` 走 `is_active=FALSE`
- 真·删除仅 `scripts/reset_db.py` 提供,不暴露 API

### 2.2 核心 ER 关系图

```mermaid
erDiagram
    USERS ||--o{ PROJECTS : "project_owner"
    PROJECTS ||--o{ BATCHES : "包含"
    BATCHES ||--o{ BATCHES : "parent_batch (加开)"
    BATCHES ||--o{ FIXTURES : "包含"
    FIXTURES ||--o{ FIXTURES : "parent_fixture (加开复制)"
    FIXTURE_TEMPLATES ||--o{ FIXTURE_TEMPLATE_SNAPSHOTS : "项目快照"
    PROJECTS ||--o{ FIXTURE_TEMPLATE_SNAPSHOTS : "持有快照"
    FIXTURE_TEMPLATE_SNAPSHOTS ||--o{ FIXTURES : "套用模板"
    FIXTURES ||--o{ FIXTURE_STATUS_HISTORY : "状态历史"
    FIXTURES ||--o{ DRAWINGS : "图纸版本链"
    PURCHASE_ORDERS ||--o{ PURCHASE_ORDER_ITEMS : "订单明细"
    PURCHASE_ORDER_ITEMS }o--|| FIXTURES : "关联治具"
    FIXTURES ||--o{ IQC_REPORTS : "IQC报告"
    FIXTURES ||--o{ ACCEPTANCE_REPORTS : "试产报告"
    FIXTURES ||--o{ MAINTENANCE_RECORDS : "保养"
    FIXTURES ||--o{ REPAIR_RECORDS : "维修"
    FIXTURES ||--o{ FIXTURE_USAGE_RECORDS : "领用"
    FIXTURES ||--o| SHELF_LOCATIONS : "库位"
    FIXTURES ||--o| SCRAP_RECORDS : "报废"
    APPROVALS ||--o{ APPROVAL_STEPS : "包含步骤"
    PURCHASE_ORDERS }o--|| SUPPLIERS : "归属供应商"
    USERS ||--o{ AUDIT_LOGS : "操作"
    USERS ||--o{ APPROVAL_STEPS : "审批"
    FIXTURES ||--o{ ATTACHMENTS : "关联附件"
```

### 2.3 三层数据结构核心字段

#### `projects` — 项目主表

```sql
CREATE TABLE projects (
  id              BIGINT PRIMARY KEY AUTO_INCREMENT,
  project_code    VARCHAR(10) UNIQUE NOT NULL,
  project_name    VARCHAR(100) NOT NULL,
  product_type    ENUM('SUS_VC','CU_VC','HP') NOT NULL,
  project_owner_id BIGINT NOT NULL,
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
ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
-- 约束:不暴露 DELETE 接口,作废走 status='cancelled'
```

#### `batches` — 需求批次

```sql
CREATE TABLE batches (
  id                BIGINT PRIMARY KEY AUTO_INCREMENT,
  project_id        BIGINT NOT NULL,
  batch_no          VARCHAR(20) NOT NULL,
  batch_type        ENUM('manual_init','mass_prod',
                         'addon_quantity','addon_optimize') NOT NULL,
  parent_batch_id   BIGINT NULL,
  flow_path         ENUM('full','simplified') DEFAULT 'full',
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
);
-- 约束:不暴露 DELETE 接口,作废走 status='cancelled'
```

#### `fixtures` — 模治具主表(核心)

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
  parent_fixture_id   BIGINT NULL,           -- 仅用于"加开-复制图纸"场景
  supplier_id         BIGINT NULL,
  shelf_location_id   BIGINT NULL,           -- 封存仅状态变更,物理位置不变(业务确认)
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
);
-- 约束:不暴露 DELETE 接口,报废走状态机 SCRAPPED
```

**[业务规则] 加开-加量批次的版本号继承:**

加开-加量复制源治具时,**新治具的 `current_version_code` 直接继承源治具的当前有效版本号**(不重置为 A1)。

```python
def generate_addon_copy_code(source_fixture, target_batch):
    project = source_fixture.project
    type_code = source_fixture.fixture_type_code
    max_set_no = db.session.query(func.max(Fixture.set_no)).filter_by(
        project_id=project.id, fixture_type_code=type_code
    ).scalar() or 0
    new_set_no = max_set_no + 1
    new_version = source_fixture.current_version_code     # 继承源版本
    return f"{project.project_code}-{type_code}#{new_set_no}-{new_version}"
```

### 2.4 快照机制:方案 A(复制型 + 追加同步)

#### 项目创建时的快照

```
项目创建 → 把 fixture_templates 中所有该产品类型的模板,整行复制到
         fixture_template_snapshots 表(带 project_id)
fixtures 表 → 外键引用 fixture_template_snapshots.id
```

#### 快照"追加同步"机制

```python
def sync_missing_templates(project_id: int, operator_id: int):
    """
    将系统模板库中该项目产品类型下、当前快照不存在的模板【追加】到项目快照。
    严禁覆盖已有快照(保护历史数据完整性)。
    """
    project = Project.query.get(project_id)
    existing_codes = {s.fixture_type_code for s in
                      FixtureTemplateSnapshot.query.filter_by(project_id=project_id)}
    latest_templates = FixtureTemplate.query.filter_by(
        product_type=project.product_type, is_active=True).all()

    new_snapshots = []
    for tpl in latest_templates:
        if tpl.fixture_type_code not in existing_codes:
            new_snapshots.append(FixtureTemplateSnapshot(
                project_id=project_id,
                fixture_type_code=tpl.fixture_type_code,
                synced_at=datetime.now(),
                synced_by=operator_id,
            ))
    db.session.add_all(new_snapshots)
    log_audit(operator_id, 'sync_templates', f'project={project_id}',
              f'added {len(new_snapshots)} snapshots')
    db.session.commit()
    return new_snapshots
```

仅超管/PM 在项目详情页有按钮触发,每次执行写审计日志。

#### 历史快照字段兼容策略

```python
# 模板新增字段后,Alembic 迁移加列默认 NULL
def get_acceptance_interval(snapshot):
    return snapshot.default_acceptance_interval_days or DEFAULT_INTERVALS['acceptance']
# 前端 NULL 显示为 "—" 或 "采用系统默认"
```

### 2.5 状态机历史表

```sql
CREATE TABLE fixture_status_history (
  id              BIGINT PRIMARY KEY AUTO_INCREMENT,
  fixture_id      BIGINT NOT NULL,
  from_status     VARCHAR(30) NULL,
  to_status       VARCHAR(30) NOT NULL,
  trigger_type    VARCHAR(30) NOT NULL,
  reason          TEXT,
  related_table   VARCHAR(50) NULL,
  related_id      BIGINT NULL,
  operator_id     BIGINT NOT NULL,
  created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_fixture_time (fixture_id, created_at),
  INDEX idx_operator (operator_id, created_at),
  CONSTRAINT fk_status_fixture FOREIGN KEY (fixture_id) REFERENCES fixtures(id),
  CONSTRAINT fk_status_op FOREIGN KEY (operator_id) REFERENCES users(id)
);
```

### 2.6 审批流数据模型

```sql
CREATE TABLE approvals (
  id              BIGINT PRIMARY KEY AUTO_INCREMENT,
  approval_type   VARCHAR(30) NOT NULL,
  business_table  VARCHAR(50) NOT NULL,
  business_id     BIGINT NOT NULL,
  flow_mode       ENUM('sequential','parallel') DEFAULT 'sequential',
  status          ENUM('pending','approved','rejected','cancelled') DEFAULT 'pending',
  initiator_id    BIGINT NOT NULL,
  initiated_at    DATETIME DEFAULT CURRENT_TIMESTAMP,
  finished_at     DATETIME NULL,
  INDEX idx_business (business_table, business_id),
  INDEX idx_status (status)
);

CREATE TABLE approval_steps (
  id              BIGINT PRIMARY KEY AUTO_INCREMENT,
  approval_id     BIGINT NOT NULL,
  step_no         INT NOT NULL,
  approver_role   VARCHAR(30) NOT NULL,
  approver_id     BIGINT NULL,
  decision        ENUM('pending','approved','rejected') DEFAULT 'pending',
  decision_type   VARCHAR(30) NULL,
  comment         TEXT,
  decided_at      DATETIME NULL,
  UNIQUE KEY uk_approval_step (approval_id, step_no),
  INDEX idx_approver (approver_id, decision)
);
```

### 2.7 甘特图字段与计划日期推算

字段嵌入 fixtures 表(见 2.3)。**计划日期推算:**

```python
def recalculate_planned_dates(fixture, snapshot, anchor_date, anchor_node='arrival'):
    """显式重算逻辑,由 PM 主动触发"""
    fixture.planned_arrival_date = anchor_date if anchor_node == 'arrival' else fixture.planned_arrival_date
    if anchor_node in ('arrival',):
        fixture.planned_iqc_date = fixture.planned_arrival_date + days(snapshot.iqc_interval_days)
    if anchor_node in ('arrival','iqc'):
        fixture.planned_install_date = fixture.planned_iqc_date + days(snapshot.install_interval_days)
    # ... 依次类推
```

**修改某节点是否级联调整后续?**
- MVP 默认行为:**不级联**
- 提供"基于此节点重算后续"按钮,PM 显式点击才触发级联

### 2.8 审计日志表

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
  operator_id     BIGINT NOT NULL,        -- 不加 FK,应用层保证用户走 is_active 软删
  reason          TEXT NULL,
  created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_record (table_name, record_id, created_at),
  INDEX idx_operator (operator_id, created_at)
);
```

### 2.9 乐观锁(双层)

#### 第一层:跨请求乐观锁(手动校验,主防线)

```python
fixture = Fixture.query.get(fixture_id)
if fixture.version != request_version:
    raise ConflictError("Modified by another user. Please refresh.", 409)
fixture.version += 1
db.session.commit()
```

#### 第二层:Session 内自动乐观锁(ORM 兜底)

```python
class Fixture(db.Model):
    version = db.Column(db.Integer, nullable=False, default=0)
    __mapper_args__ = {'version_id_col': version}
```

#### 全局异常处理器

```python
from sqlalchemy.orm.exc import StaleDataError

@app.errorhandler(StaleDataError)
def handle_stale(e):
    return error_response("Conflict: please refresh", 409)
```

### 2.10 告警状态去重表

```sql
CREATE TABLE alerts (
  id              BIGINT PRIMARY KEY AUTO_INCREMENT,
  alert_type      VARCHAR(30) NOT NULL,
  target_table    VARCHAR(50) NOT NULL,
  target_id       BIGINT NOT NULL,
  last_sent_at    DATETIME NOT NULL,
  is_active       BOOLEAN DEFAULT TRUE,
  resolved_at     DATETIME NULL,
  UNIQUE KEY uk_alert (alert_type, target_table, target_id)
);
```

### 2.11 采购订单一对多设计

```sql
CREATE TABLE purchase_orders (
  id              BIGINT PRIMARY KEY AUTO_INCREMENT,
  po_number       VARCHAR(30) UNIQUE NOT NULL,
  supplier_id     BIGINT NOT NULL,
  ordered_at      DATE NOT NULL,
  total_amount    DECIMAL(12,2) NULL,
  currency        VARCHAR(10) DEFAULT 'CNY',
  status          ENUM('draft','placed','in_transit','received','closed') DEFAULT 'placed',
  remark          TEXT,
  created_by      BIGINT NOT NULL,
  created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  version         INT DEFAULT 0,
  INDEX idx_supplier (supplier_id)
);

CREATE TABLE purchase_order_items (
  id                BIGINT PRIMARY KEY AUTO_INCREMENT,
  purchase_order_id BIGINT NOT NULL,
  fixture_id        BIGINT NOT NULL,
  unit_price        DECIMAL(10,2) NOT NULL,
  quantity          INT DEFAULT 1,
  remark            VARCHAR(200),
  created_at        DATETIME DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uk_po_fixture (purchase_order_id, fixture_id),
  INDEX idx_fixture (fixture_id),
  CONSTRAINT fk_poi_po FOREIGN KEY (purchase_order_id) REFERENCES purchase_orders(id),
  CONSTRAINT fk_poi_fix FOREIGN KEY (fixture_id) REFERENCES fixtures(id)
);
```

---

## 三、后端模块划分

### 3.1 目录结构 [V1.3 修订:删除 scheduler_runner.py,新增 serve.py]

```
backend/
├── CLAUDE.md
├── TASKS.md
├── docs/
│   ├── 00_open_questions.md
│   ├── 01_requirement_v2.1.md
│   ├── 02_coding_rules_v1.0.md
│   ├── 03_architecture_v1.3.md         # 本文档
│   ├── 04_api_spec.md
│   ├── 05_permissions.md
│   ├── 06_restore_procedure.md
│   ├── 07_export_guideline.md
│   └── 08_deployment_windows.md        # ★ V1.3 新增:Windows Server 部署指南
├── requirements.txt
├── run.py                              # 开发入口(Flask 内置 dev server)
├── serve.py                            # ★ V1.3 新增:生产入口(Waitress)
├── .env.example
├── .env.development                    # gitignored
├── .env.production                     # gitignored,仅生产机
├── .gitignore
│
├── app/
│   ├── __init__.py                     # create_app + APScheduler 初始化
│   ├── config.py                       # 三套配置 + dotenv 加载
│   ├── extensions.py                   # db / jwt / migrate / mail / scheduler 单例
│   │
│   ├── models/                         # (略,见 V1.2)
│   ├── services/
│   │   ├── ...
│   │   ├── code_generator.py
│   │   ├── snapshot_service.py
│   │   ├── state_machine.py
│   │   ├── approval_service.py
│   │   ├── gantt_service.py
│   │   ├── upload_service.py
│   │   ├── audit_service.py
│   │   ├── permission_service.py
│   │   ├── export_service.py           # 报表导出(三档策略)
│   │   └── notification_service.py     # 审批通知(MVP 邮件)
│   ├── blueprints/                     # (略,见 V1.2)
│   ├── tasks/
│   │   ├── __init__.py                 # 注册 APScheduler 任务到 app
│   │   ├── alert_checker.py            # 告警检测(紧急阈值 3 天)
│   │   └── mail_sender.py              # 邮件发送 + 去重
│   │   # ★ V1.3 删除:scheduler_runner.py(不再需要独立容器入口)
│   └── utils/
│       ├── decorators.py
│       ├── responses.py
│       ├── exceptions.py
│       ├── enums.py
│       └── helpers.py
│
├── migrations/                         # Alembic
└── scripts/
    ├── seed_data.py
    ├── reset_db.py
    └── check_alerts_standalone.py      # ★ V1.3 新增:备选方案,供 Windows 任务计划独立调用
```

### 3.2 核心 API 端点

(同 V1.2,无变更)

```
# 项目(无 DELETE)
GET    /api/projects
POST   /api/projects
GET    /api/projects/:id
PUT    /api/projects/:id
PATCH  /api/projects/:id/cancel
PUT    /api/projects/:id/owner
GET    /api/projects/:id/gantt?batch_id=
POST   /api/projects/:id/sync-templates
GET    /api/projects/export?ids=&format=xlsx

# 批次(无 DELETE)
POST   /api/batches
GET    /api/batches/:id
PUT    /api/batches/:id
PATCH  /api/batches/:id/cancel
GET    /api/batches/:id/fixtures
GET    /api/batches/:id/gantt

# 模治具(无 DELETE)
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
GET    /api/fixtures/export?...

# 采购、业务单据、审批、系统管理:同 V1.2
```

### 3.3 状态机核心逻辑

(同 V1.2,内容无变更)

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
        S.INSTALLING:  'normal',                     # 业务正向场景(让步通过仍需返工)
        S.SCRAPPED:    'acceptance_fail_scrap',      # 业务确认:试产不合格可直接报废
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
    S.SCRAPPED:     {},
}

REJECT_FALLBACK = {
    S.IQC_INSPECTING:      S.PENDING_IQC,
    S.ACCEPTANCE_TESTING:  S.INSTALLING,
}

def transition(fixture, to_status, trigger, operator_id,
               reason=None, related=None, force=False):
    from app.models import FixtureStatusHistory, db
    from_status = fixture.current_status
    if not force:
        allowed = TRANSITIONS.get(from_status, {})
        if to_status not in allowed:
            raise StateMachineError(f"非法状态转换:{from_status} -> {to_status}")
        if allowed[to_status] != trigger:
            raise StateMachineError(f"触发器不匹配")
    history = FixtureStatusHistory(
        fixture_id=fixture.id, from_status=from_status, to_status=to_status,
        trigger_type='forced' if force else trigger, reason=reason,
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
    fallback = REJECT_FALLBACK.get(fixture.current_status)
    if not fallback:
        raise StateMachineError(f"{fixture.current_status} 不支持驳回回退")
    return transition(fixture, fallback, 'rejected_fallback',
                       operator_id, reason=reason, force=True)
```

### 3.4 审批流实现(顺序 + 并行 + 驳回)

(同 V1.2,内容无变更)

```python
def initiate_approval(approval_type, business, steps_config, initiator_id,
                      flow_mode='sequential'):
    approval = Approval(
        approval_type=approval_type,
        business_table=business.__tablename__,
        business_id=business.id,
        flow_mode=flow_mode,
        initiator_id=initiator_id,
    )
    db.session.add(approval)
    db.session.flush()
    for cfg in steps_config:
        db.session.add(ApprovalStep(approval_id=approval.id, **cfg))
    db.session.commit()
    if flow_mode == 'parallel':
        notify_all_approvers(approval)
    else:
        notify_next_approver(approval)
    return approval


def decide_step(step_id, approver_id, decision, decision_type=None, comment=None):
    step = ApprovalStep.query.get(step_id)
    approval = step.approval

    if approval.flow_mode == 'sequential':
        current = next_pending_step(approval)
        if current.id != step.id:
            raise BusinessError("非当前审批步骤,无权操作")
    else:
        if step.decision != 'pending':
            raise BusinessError("该步骤已完成审批")

    step.approver_id = approver_id
    step.decision = decision
    step.decision_type = decision_type
    step.comment = comment
    step.decided_at = datetime.now()

    if decision == 'rejected':
        approval.status = 'rejected'
        approval.finished_at = datetime.now()
        on_approval_rejected(approval, decision_type, comment)
    else:
        if approval.flow_mode == 'parallel':
            all_approved = all(s.decision == 'approved' for s in approval.steps)
            if all_approved:
                approval.status = 'approved'
                approval.finished_at = datetime.now()
                on_approval_approved(approval)
        else:
            next_step = next_pending_step(approval, exclude_id=step.id)
            if next_step is None:
                approval.status = 'approved'
                approval.finished_at = datetime.now()
                on_approval_approved(approval)
            else:
                notify_next_approver(approval)
    db.session.commit()
```

#### 审批场景与 flow_mode 配置

| 审批场景 | flow_mode | 步骤 |
|----------|-----------|------|
| IQC 不合格三方审批 | `sequential` | PM → 设计 → ME |
| 试产不合格三部门评审 | `sequential` | PM → 设计/ME → 质量 |
| 报废三方会签 | `parallel` | PM + 生产部负责人 + 业务工程师 |
| 手动版解封 | `sequential` | PM → 生产主管 |
| 紧急上机授权 | `sequential` | PM → 质量部 IQC |

#### 审批通知(MVP 邮件统一实现)

```python
# app/services/notification_service.py
"""
[决策] MVP 阶段通知统一为邮件。后续如需系统内通知中心,新建 notifications 表。
"""
from app.tasks.mail_sender import send_mail_async

def notify_next_approver(approval):
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
    for step in approval.steps:
        recipient = resolve_approver(step.approver_role, approval.business_id)
        send_mail_async(to=recipient.email, ...)
```

### 3.5 文件上传 [V1.3 修订:移除 X-Accel-Redirect 选项]

```python
# app/config.py
UPLOAD_BASE = os.environ.get('UPLOAD_BASE', './uploads')   # 开发: ./uploads, 生产: D:/dbu/uploads
UPLOAD_MAX_SIZE = 0                                         # 0 = 不限制(业务规则)
UPLOAD_ALLOWED_EXT = {'jpg','jpeg','png','pdf','heic','mp4','mov'}
```

```python
# app/services/upload_service.py
import os
from pathlib import Path
from uuid import uuid4
from werkzeug.utils import secure_filename
from datetime import date

def save_attachment(file, business_table, business_id, uploader_id):
    today = date.today()
    sub = f"{business_table}/{today:%Y%m}"
    filename = f"{uuid4().hex}_{secure_filename(file.filename)}"
    # ★ V1.3 用 Path 跨平台:Windows 生产机 D:/dbu/uploads,开发机 ./uploads
    fs_path = Path(Config.UPLOAD_BASE) / sub / filename
    fs_path.parent.mkdir(parents=True, exist_ok=True)
    file.save(str(fs_path))

    if Config.UPLOAD_MAX_SIZE > 0:
        size = fs_path.stat().st_size
        if size > Config.UPLOAD_MAX_SIZE:
            fs_path.unlink()
            raise ValidationError("附件超过限制")

    att = Attachment(
        business_table=business_table,
        business_id=business_id,
        relative_path=f"{sub}/{filename}",         # ★ DB 永远存正斜杠相对路径
        original_name=file.filename,
        size=fs_path.stat().st_size,
        uploader_id=uploader_id,
    )
    db.session.add(att)
    db.session.commit()
    return att

@bp.route('/attachments/<int:att_id>')
@jwt_required()
def download(att_id):
    att = Attachment.query.get_or_404(att_id)
    if not can_view_business(current_user, att.business_table, att.business_id):
        abort(403)
    # ★ V1.3:统一用 send_from_directory(无 X-Accel-Redirect)
    # 单进程 Waitress 多线程足够 50 人内部使用;若大文件多并发成瓶颈,Phase 7 评估前置 IIS
    return send_from_directory(
        Config.UPLOAD_BASE, att.relative_path,
        download_name=att.original_name, as_attachment=True
    )
```

**[V1.3 提示] 路径跨平台兼容:**
- 开发机 Windows 11 与生产机 Windows Server 都用反斜杠,但 Python 用 `Path` 自动处理
- DB 中 `relative_path` 永远存**正斜杠**,跨平台一致

### 3.6 邮件告警 [V1.3 重写:Flask-APScheduler 内嵌]

#### 主方案:APScheduler 内嵌 Flask 进程

```python
# app/extensions.py
from flask_apscheduler import APScheduler

scheduler = APScheduler()
db = SQLAlchemy()
jwt = JWTManager()
mail = Mail()
migrate = Migrate()
```

```python
# app/__init__.py
from flask import Flask
from app.config import Config
from app.extensions import db, jwt, mail, migrate, scheduler

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    jwt.init_app(app)
    mail.init_app(app)
    migrate.init_app(app, db)

    # ★ V1.3 关键:APScheduler 时区显式设置(唯一仍需注意时区的地方)
    app.config['SCHEDULER_TIMEZONE'] = 'Asia/Shanghai'
    app.config['SCHEDULER_API_ENABLED'] = False
    scheduler.init_app(app)

    # 仅在生产或主进程注册任务,避免 Flask debug reload 时重复注册
    if not app.debug or os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
        from app.tasks import register_jobs
        register_jobs(scheduler)
        scheduler.start()

    # 注册 blueprints
    from app.blueprints import register_blueprints
    register_blueprints(app)
    return app
```

```python
# app/tasks/__init__.py
from app.tasks.alert_checker import check_all_alerts

def register_jobs(scheduler):
    scheduler.add_job(
        id='check_all_alerts',
        func=check_all_alerts,
        trigger='cron',
        hour=8, minute=0,
        replace_existing=True,
    )
```

```python
# app/tasks/alert_checker.py
URGENT_THRESHOLD_DAYS = 3

def check_all_alerts():
    """每日 08:00 触发,扫描各类告警条件"""
    with scheduler.app.app_context():
        check_po_overdue()
        check_po_urgent()
        check_maintenance_due()
        check_acceptance_overdue()
        check_planned_date_yellow()

def check_po_urgent():
    """量产版批次距交期 ≤3 天预警"""
    threshold = date.today() + timedelta(days=URGENT_THRESHOLD_DAYS)
    fixtures = Fixture.query.join(Batch).filter(
        Batch.batch_type == 'mass_prod',
        Fixture.actual_arrival_date.is_(None),
        Fixture.planned_arrival_date <= threshold,
        Fixture.planned_arrival_date > date.today(),
    ).all()
    for f in fixtures:
        send_alert_dedup(
            alert_type='po_urgent',
            target_table='fixtures', target_id=f.id,
            recipients=[f.project.owner.email],
            subject=f"[紧急] {f.fixture_code} 距交期不足 3 天",
            body=...,
        )
```

#### 为什么单进程内嵌不会有并发问题?

- 生产环境用 Waitress **单进程多线程**(`threads=8`)
- APScheduler 默认 jobstore 是内存,单进程内不会出现多调度器实例
- 这是 V1.2 独立 scheduler 容器方案要解决的多 Worker 问题——本方案不存在该问题
- 50 人系统单进程足够,无需 Gunicorn 多 Worker 或独立调度进程

#### 备选方案:Windows 任务计划程序独立调用

如未来发现 APScheduler 内嵌存在问题(例如 Flask 重启导致任务丢失),可切换为外部调度:

```python
# backend/scripts/check_alerts_standalone.py
"""
独立可执行脚本,供 Windows 任务计划程序定时调用
执行方式:python scripts/check_alerts_standalone.py
"""
from app import create_app
from app.tasks.alert_checker import check_all_alerts

if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        check_all_alerts()
        print(f"[OK] Alerts checked at {datetime.now()}")
```

```powershell
# 注册 Windows 任务计划程序
schtasks /Create /SC DAILY /ST 08:00 /TN "DBU-Alert-Check" ^
  /TR "C:\Python312\python.exe C:\dbu\backend\scripts\check_alerts_standalone.py" ^
  /RU SYSTEM /F
```

切换决策时机:Phase 6 实施 APScheduler 后观察 1-2 周,如稳定即沿用;如有异常切到独立脚本。

#### 告警去重必测场景

1. 首次触发 → 发送
2. 同日相同 alert_type+target 再次触发 → 跳过
3. `is_active=FALSE` 后再次触发 → 重新发送并激活
4. 跨日触发同一 alert → 发送
5. 不同 target_id 同 alert_type → 各自独立去重
6. 状态从 `po_urgent` 升级为 `po_overdue` → 不同 alert_type,独立发送

### 3.7 报表导出三档策略

详见 `docs/07_export_guideline.md`,核心规则:

| 场景 | 方案 | 实现位置 |
|------|------|----------|
| 单表列表 < 1000 条 | 前端 xlsx 库 | 浏览器内 JSON → Excel |
| 多表关联 / >1000 条 | 后端流式响应 | `services/export_service.py` + `yield` |
| 月度大报表 | APScheduler 后台生成 | 每月 1 日 02:30 跑,结果存 `attachments` |

```python
# app/services/export_service.py
import openpyxl
from pathlib import Path
import tempfile

def export_fixtures_streaming(filters):
    """openpyxl write_only 模式 + 分页查询,内存占用恒定"""
    wb = openpyxl.Workbook(write_only=True)
    ws = wb.create_sheet("Fixtures")
    ws.append(['编码','项目','批次','类型','状态','计划到货','实际到货'])

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

    tmp = tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False)
    wb.save(tmp.name)
    return tmp.name
```

**约束写入 CLAUDE.md:** 禁止 `pandas.to_excel(BytesIO())` 或 `openpyxl` 默认模式(非 write_only),否则大数据量 OOM。

---

## 四、前端模块划分

> **本章节内容与 V1.2 一致**,仅在 4.1 加入 vite.config.js 的 API 代理配置。

### 4.1 目录结构与路由

(同 V1.2,目录结构无变更)

**vite.config.js 关键配置 [V1.3 强调]:**

```javascript
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    port: 5173,
    proxy: {
      '/api': { target: 'http://localhost:5000', changeOrigin: true },
      '/uploads': { target: 'http://localhost:5000', changeOrigin: true },
    }
  },
  build: {
    outDir: 'dist',
    sourcemap: false,
  }
})
```

**生产构建后部署:**

```bash
cd frontend
pnpm build              # 生成 dist/
# 拷贝至生产机 C:\dbu\frontend\dist\
# Flask 通过 static_folder 配置直接 serve
```

### 4.2 关键组件设计建议

| 组件 | 关键设计点 |
|------|------------|
| `StatusTag.vue` | 12 状态颜色映射,集中维护 |
| `AttachmentUploader.vue` | 封装 el-upload,multipart 上传,无大小限制 |
| `PermissionButton.vue` | v-if 判断角色权限 |
| `ApprovalDrawer.vue` | 通用审批侧抽屉,支持顺序/并行展示 |
| `GanttChart.vue` | Frappe Gantt 包装;>100 任务自动降级到批次视图 |
| `StatusHistoryTimeline.vue` | el-timeline 展示状态变更历史 |
| `DateCascadeButton.vue` | "基于此节点重算后续"按钮 |
| `CancelButton.vue` | 作废按钮,二次确认 + 必填原因 |
| `ExportButton.vue` | 列表导出,<1000 条前端导,否则触发后端流式 |

### 4.3 甘特图技术选型与降级

(同 V1.2)Frappe Gantt + 100+ 自动降级到批次视图。

### 4.4 12 状态颜色映射

(同 V1.2)

### 4.5 权限控制 + axios 拦截器

```javascript
// frontend/src/api/request.js
import axios from 'axios'
import { ElMessageBox } from 'element-plus'
import dayjs from 'dayjs'
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

### 5.1 模块开发顺序 [V1.3 修订:Phase 0 改为 Windows Server 部署清单]

```
Phase 0 — 基建(1 周)
  ├─ 开发机环境
  │   □ Python 3.12 安装,创建 venv
  │   □ pnpm 安装
  │   □ Docker MySQL 容器已运行(若无,按 1.3 命令启动)
  │   □ MySQL 容器加 --default-time-zone='+08:00'
  │   □ .env.development 创建并配置(密码不入仓)
  │   □ Flask run.py 启动,/api/health 返回 200
  │   □ Vue pnpm dev 启动,代理 /api 通到 Flask
  │   □ 验证:进入 mysql 容器执行 SELECT NOW(),输出北京时间
  │
  ├─ ★ 生产机预演(关键!上线前数月即开始)
  │   □ 与公司 IT 确认目标 Windows Server 版本(2019/2022)
  │   □ 确认服务器有 Python 3.12 安装权限
  │   □ 确认 MySQL 8.4 可在 Windows Server 安装
  │   □ 确认服务器系统时区为 Asia/Shanghai (China Standard Time)
  │   □ 确认防火墙端口 80(前端)、5000(可对外或仅本机) 可开放
  │   □ 确认公司 SMTP 服务可从服务器访问
  │   □ 确认有 D:\ 盘可用于附件与备份(或调整路径变量)
  │   □ NSSM 工具可下载或公司允许安装
  │   □ 生产机 .env.production 提前规划(数据库账号、JWT 密钥、SMTP 配置)
  │
  ├─ 代码框架
  │   □ Flask app factory + extensions + python-dotenv 三套环境
  │   □ 用户/角色模型(含 is_active 软删) + JWT 登录
  │   □ 通用响应/异常/装饰器
  │   □ 全局 StaleDataError 捕获返回 409
  │
  └─ Vue 项目初始化
      □ Vite + Element Plus + Pinia + Router
      □ vite.config.js API 代理
      □ dayjs 时区配置
      □ axios 拦截器(409/401)

Phase 1 — 基础数据(1 周)
  ├─ 治具模板库 CRUD(is_active 软停用)
  ├─ 供应商库 CRUD
  ├─ 系统字典
  └─ 用户管理 CRUD(PATCH activate/deactivate,无 DELETE)

Phase 2 — 核心业务主线(3-4 周)⭐ MVP 关键路径
  ├─ 项目管理 CRUD(含 cancel 接口)
  ├─ 模板快照创建 + 追加同步
  ├─ 需求批次(含 parent_batch_id, cancel)
  ├─ 模治具创建 + 编码生成(加开继承版本号)
  ├─ 状态机服务 + 状态历史(含完整单元测试)
  ├─ 采购订单(头/明细分离)+ 计划日期推算
  └─ 列表/详情页 + 状态 Tag + 作废按钮

Phase 3 — 流程节点(2-3 周)
  ├─ IQC 标准路径
  ├─ 紧急上机路径
  ├─ 安装调试 + 试产验收
  ├─ 移交接收 + 货架绑定
  └─ 附件上传(send_from_directory,无大小限制)

Phase 4 — 审批流(1-2 周)
  ├─ 审批服务(顺序+并行双模式 + 驳回)
  ├─ 审批通知(MVP 邮件实现)
  ├─ IQC 不合格三方审批(sequential)
  ├─ 试产不合格三部门评审(sequential, 含报废分支)
  ├─ 报废三方会签(parallel)
  └─ 我的待审 + 审批侧抽屉

Phase 5 — 使用与维保(1-2 周)
  ├─ 领用/归还
  ├─ 封存/解封
  ├─ 保养记录 + 阈值检测
  └─ 维修记录

Phase 6 — 可视化与告警(1-2 周)
  ├─ 甘特图(项目/批次两层 + 100+ 自动降级)
  ├─ Flask-APScheduler 内嵌 + 显式 Asia/Shanghai 时区
  ├─ 告警去重 + 必测场景全覆盖
  ├─ 紧急阈值 3 天告警
  ├─ "基于此节点重算后续"按钮
  └─ 成本统计页

Phase 7 — 系统化与上线(1-2 周)
  ├─ 审计日志页
  ├─ 超管强制跳转入口
  ├─ 报表导出(三档策略)
  ├─ ★ 生产部署
  │   □ 生产机 Python/MySQL/NSSM 安装
  │   □ Git clone backend → venv → pip install
  │   □ pnpm build → 拷贝 dist 到生产机
  │   □ 生产机 .env.production 配置
  │   □ Flask Migrate 执行(空库初始化)
  │   □ seed_data.py 跑种子数据(超管账号、模板、供应商)
  │   □ NSSM 注册 Flask 为 Windows 服务
  │   □ 配置 Windows 任务计划(MySQL 备份、附件备份)
  │   □ 完整还原演练(按 docs/06)
  │   □ 50 人测试账号实地试用 1 周
  └─ 部署文档 + 用户手册
```

**总工期估算:13-17 周**(比 V1.2 多 1 周用于生产机预演与适配)

### 5.2 阶段里程碑

| 阶段 | 里程碑 | 验收标准 |
|------|--------|----------|
| M0 | 基建可用 | 本地 Vue+Flask+MySQL 三件套联通;生产机环境清单全部 ✅ |
| M1 | 后台可配 | 模板/供应商/字典/用户全部能 CRUD |
| M2 | **MVP 主干** | PM 能完整走通 项目→批次→治具→编码→甘特图 |
| M3 | 流程闭环 | 治具能从 IQC 走到验收合格、入库 |
| M4 | 审批可用 | IQC 三方审批流转正确;报废并行会签生效 |
| M5 | 维保闭环 | 领用→归还→保养→维修闭环,使用次数累加 |
| M6 | 告警与统计 | 邮件告警按预期去重(单进程内嵌验证),甘特图逾期标红 |
| M7 | 上线 | 生产机部署完成,备份还原演练成功,50 人小范围试用 |

### 5.3 CLAUDE.md 结构建议 [V1.3 修订:删除时区四处联动,新增环境配置规则]

```markdown
# CLAUDE.md — DBU 模治具管理系统 AI 协作指南

## 项目概览
- 业务:模治具全生命周期管理
- 技术栈:Flask 3 + Vue 3 + MySQL 8.4
- 部署:混合方案 — 开发机 Docker MySQL + Flask 本地;生产 Windows Server 原生

## 关键文档
- docs/00_open_questions.md
- docs/01_requirement_v2.1.md
- docs/02_coding_rules_v1.0.md
- docs/03_architecture_v1.3.md      ← 权威架构
- docs/04_api_spec.md
- docs/05_permissions.md
- docs/06_restore_procedure.md
- docs/07_export_guideline.md
- docs/08_deployment_windows.md     ← Windows Server 部署细节
- TASKS.md                           ← 当前任务

## 当前阶段
Phase X — XXX

## Critical Rules(继承自 vc-cost-system 已踩坑总结)
- MySQL 必须 utf8mb4
- Schema-First:文档→Model→Migration→DB,禁止逆向
- Blueprint url_prefix 只在注册时设
- JWT identity 强转 int
- 关键表带 version 乐观锁
- PUT/PATCH 用 'key' in body 而非 body.get()
- 前端 import 一律相对路径,禁用 @/
- el-tag type 兜底必须合法值
- ElMessageBox.confirm 二段 try/catch

## 本系统专属规则(V1.3 完整版)

### 配置与环境(★ V1.3 替换原时区四处联动)
- 三套环境配置:.env.development / .env.production / .env.example
- python-dotenv 按 FLASK_ENV 加载;config.py 不硬编码任何密码或密钥
- .env.development 与 .env.production 必须 gitignored
- 所有秘密(数据库密码、JWT 密钥、SMTP 凭证)走环境变量
- 开发机连接 Docker MySQL:DATABASE_URL=...@localhost:3306/...
- 生产机连接 Windows MySQL:DATABASE_URL=...@localhost:3306/...
  (主机端口相同,密码必然不同)
- APScheduler 实例化时显式 timezone='Asia/Shanghai'(唯一仍需注意时区的地方)
- 前端 dayjs.tz.setDefault('Asia/Shanghai');禁止 new Date() 解析无时区字符串

### 部署
- 生产用 Waitress(serve.py 入口),通过 NSSM 注册为 Windows 服务
- Flask 同时 serve /api 与 Vue 静态文件(MVP 方案)
- 路径用 pathlib.Path 跨平台;DB 中相对路径永远存正斜杠
- 备份用 Windows 任务计划 + mysqldump.exe + robocopy

### 删除策略
- 核心业务表禁止暴露 HTTP DELETE
- projects/batches 作废走 status='cancelled'
- fixtures 作废走状态机 SCRAPPED
- 用户/供应商/模板用 is_active=FALSE 停用
- 真·删除仅 scripts/reset_db.py 提供

### 状态机
- 状态变更必须走 services/state_machine.py 的 transition() 或 reject()
- 不允许直接改 fixture.current_status
- 改流程必须同步 5 处:state_machine.py / status_history 表 / 前端 status.js / i18n / 文档

### 编码与版本
- 编码生成必须走 services/code_generator.py
- 加开-加量复制时 current_version_code 继承源治具,不重置 A1
- 版本升级 A1→A2:改 fixtures.current_version_code + drawings 追加,不新建 fixture
- 加开复制 #1→#2:新建 fixture + parent_fixture_id 指向源

### 审批流
- 所有审批走 services/approval_service.py
- 报废会签 flow_mode='parallel',其他场景 'sequential'
- approved/rejected 都要传 decision_type
- 通知统一走 services/notification_service.py(MVP 邮件实现)

### 快照
- 项目创建时一次性生成;追加新模板走 sync_missing_templates() 写审计

### 附件
- 大小默认不限制(业务规则);UPLOAD_MAX_SIZE 配置项保留为 0
- 落盘相对 UPLOAD_BASE,DB 只存 relative_path(正斜杠)
- 下载经鉴权 endpoint(send_from_directory),不直接暴露目录
- 路径用 pathlib.Path 处理跨平台

### 调度器
- Flask-APScheduler 内嵌即可,Waitress 单进程多线程不会有并发问题
- ★ 生产环境 Flask 重启时 APScheduler 任务会重新加载;不依赖任务持久化
- 备选方案:check_alerts_standalone.py + Windows 任务计划

### 并发
- PUT/PATCH 必须包含 version 字段;手动校验 + ORM 自动校验双保险
- 全局异常处理器捕获 StaleDataError 返回 409

### 报表导出
- < 1000 条用前端 xlsx 库
- > 1000 条或多表关联走 services/export_service.py 流式响应
- 禁止 pandas.to_excel(BytesIO()) 或 openpyxl 非 write_only 模式

### 邮件告警
- 必须经 send_alert_dedup() 去重
- 紧急阈值 URGENT_THRESHOLD_DAYS=3(业务规则)
```

### 5.4 独立 AI 辅助开发的风险点 [V1.3 修订]

| 风险 | 缓解措施 |
|------|----------|
| **★ V1.3 新增:开发机配置泄漏到生产** | 严格分离 .env.development / .env.production;.gitignore 双重保险 |
| **★ V1.3 新增:生产机 Windows 路径 Bug** | 全程用 pathlib.Path,禁止用字符串拼接 `\` 或 `/`;DB 相对路径统一正斜杠 |
| **★ V1.3 新增:开发机 Docker MySQL 时区误用 UTC** | 启动容器加 `--default-time-zone='+08:00'`;config 双保险加 `init_command` |
| **★ V1.3 新增:NSSM Windows 服务启动失败** | Phase 7 部署时手动跑一遍 `python serve.py` 确认无报错再注册服务 |
| AI 自由发挥加 DELETE 端点 | CLAUDE.md 明确禁止;代码 review 时全文搜 `methods=['DELETE']` |
| 大数据量导出 OOM | CLAUDE.md 明确禁止 pandas.to_excel + openpyxl 默认模式 |
| 状态机/审批流改动失控 | 先写测试再写实现 |
| 数据库迁移不可逆错误 | 严格 Schema-First;migration 必须人工 review |
| AI 生成代码隐藏 Bug | 关键路径必须有单元测试 |
| 过度设计倾向 | "MVP 真的需要吗?" |
| 跨模块改动遗漏 | 改状态机时同步检查 5 处 |
| 乐观锁未覆盖 | 高频写入表带 version + ORM `__mapper_args__` |
| 邮件配置生产失败 | 开发期 MailHog;生产前单独测 send_email() |
| 备份从未验证 | 上线前完整还原演练;每月抽查 |
| 权限矩阵前后端不一致 | 派生自 docs/05_permissions.md |
| **APScheduler 在 debug=True 下重复启动** | `if not app.debug or os.environ.get('WERKZEUG_RUN_MAIN') == 'true'` 守卫(已写入 3.6) |

---

## 六、附:关键决策一览表 [V1.3 修订:第 1/2/3 条更新]

| # | 决策点 | 选择 | 一句话理由 |
|---|--------|------|------------|
| **1** | **整体架构** | **单体 Flask + Vue SPA + 混合部署(Docker MySQL 开发,Windows Server 原生生产)** | **匹配开发者已有部署经验,Docker 全栈对独立开发者收益有限** |
| **2** | **异步任务** | **Flask-APScheduler 内嵌(单进程 Waitress 部署)** | **50 人单进程足够,无多 Worker 并发陷阱** |
| **3** | **环境与配置** | **.env.development / .env.production + python-dotenv** | **Windows 原生部署时区自动继承,仅 APScheduler 需显式时区** |
| 4 | 核心表删除 | 禁止 HTTP DELETE,作废走状态字段 | 制造业资产数据不可丢 |
| 5 | 快照机制 | 复制型 + 追加同步 | 简单直观 + 应对长周期演进 |
| 6 | 审批流模型 | 多场景共用 + 顺序/并行双模式 | 一套引擎覆盖所有场景 |
| 7 | 审批通知 | MVP 邮件统一实现 | 避免 AI 自由发挥引入额外模块 |
| 8 | 状态机实现 | 字典 + transition() 函数 | 可测试、可枚举 |
| 9 | 试产不合格→报废 | 开放(业务确认) | 业务规则明确 |
| 10 | 编码生成 | 后端服务 + 加开继承当前版本 | 与图纸一致性符合 |
| 11 | 版本升级语义 | 改字段 + drawings 追加;不新建 fixture | 实物不变图纸演进 |
| 12 | 加开复制语义 | 新建 fixture + parent_fixture_id 溯源 | 套号递增可追溯 |
| 13 | 文件存储 | UPLOAD_BASE 环境变量 + 鉴权 send_from_directory | 简单 + 跨平台 |
| 14 | 附件大小限制 | 默认不限(业务确认) | 避免影响业务上传现场图 |
| 15 | 甘特图库 | Frappe Gantt + 100+ 降级 | 轻量 + 大数据量友好 |
| 16 | 状态颜色 | 自定义 :color,5 type 不够 | 12 状态需视觉区分 |
| 17 | 权限实现 | 后端字典 + 前端按钮 + 派生自单一文档 | 避免前后端偏移 |
| 18 | 告警去重 | alerts 表 + 每日窗口;紧急阈值 3 天 | 避免邮件轰炸 |
| 19 | 报表导出 | 三档策略(前端/流式/后台) | 从源头规避 OOM |
| 20 | 备份方案 | Windows 任务计划 + mysqldump + robocopy | 与现有 vc-cost-system 一致 |
| 21 | 乐观锁 | 手动校验 + ORM 自动 双层 | 双保险 |
| 22 | 采购订单关系 | PO 头 + items 一对多 | 反映"一单多治具" |
| 23 | 计划日期级联 | 默认不级联,"重算后续"按钮 | 既精确又方便 |
| 24 | 409 处理 | axios 拦截器统一弹窗刷新 | 避免每个组件重复处理 |
| 25 | 用户软删 | is_active=FALSE,无 DELETE | 保审计日志完整 |

---

## 七、文件修订记录

| 版本 | 日期 | 修订内容 | 修订人 |
|------|------|----------|--------|
| V1.0 | 2026-04-26 | 初版发布(Docker Compose 4 容器) | Claude (Opus) |
| V1.1 | 2026-04-26 | 第一轮审阅 14 处修订(独立 scheduler、parent_fixture_id、追加快照同步、purchase_order_items、级联日期、双层乐观锁、approved 透传 decision_type、X-Accel-Redirect 预留、axios 409 拦截、甘特图降级等)| Claude (Opus) |
| V1.2 | 2026-04-26 | 第二轮审阅 9 处修订 + 业务确认 5 处落地(时区四处联动、核心表禁 DELETE、并行审批分支、报表导出三档、试产报废路径、加开继承版本、紧急阈值 3 天、附件无限制等)| Claude (Opus) |
| **V1.3** | **2026-04-27** | **部署方案重大调整:混合部署替代 Docker Compose 全栈容器化。** 修订内容:① 1.1 部署形态改为混合部署 ② 1.3 全新章节:开发(Docker MySQL + 本地 Flask/Vue)与生产(Windows Server 原生 MySQL/Waitress/静态文件) ③ python-dotenv 三套环境配置 ④ 1.4 备份替换为 Windows 任务计划 + mysqldump + robocopy ⑤ 3.5 文件上传移除 X-Accel-Redirect,改用 pathlib 跨平台路径 ⑥ 3.6 调度器简化为 Flask-APScheduler 内嵌(50 人单进程足够),备选 Windows 任务计划独立调用 ⑦ 4.1 新增 vite.config.js API 代理示例 ⑧ Phase 0 替换为开发机 + 生产机预演双清单 ⑨ Phase 7 新增生产部署详细步骤 ⑩ CLAUDE.md 删除时区四处联动规则,新增环境配置与部署规则 ⑪ 风险点新增 4 条 Windows 特有风险 ⑫ 关键决策第 1/2/3 条更新 ⑬ docs/ 新增 08_deployment_windows.md 占位 ⑭ 工期 12-16 周 → 13-17 周(预留生产机预演时间) | Claude (Opus) |

---

> **本架构文档版本:V1.3**
> **后续若需变更:必须更新版本号 + 修订记录 + 同步到 docs/03_architecture.md**
> **项目代码仓库根目录的 CLAUDE.md 应永远引用本文档为权威架构来源。**

---

## 附录 A:仍待业务确认事项

| # | 事项 | 状态 |
|---|------|------|
| 1 | 试产不合格三部门评审是否包含"直接报废"? | ✅ 已确认:包含 |
| 2 | 加开-加量批次治具是否继承原批次当前版本号? | ✅ 已确认:继承 |
| 3 | 手动版封存物理隔离是否影响货架绑定? | ✅ 已确认:不影响 |
| 4 | 量产版交期"紧急"判定阈值? | ✅ 已确认:3 天 |
| 5 | 单个治具附件总大小是否限制? | ✅ 已确认:不限制 |

**当前无待确认业务事项。** 后续若有新疑问,在 `docs/00_open_questions.md` 中维护。

---

## 附录 B:V1.3 部署待确认事项(开发启动前需 IT 配合)

| # | 事项 | 影响 | 确认方 |
|---|------|------|--------|
| 1 | 生产服务器 Windows Server 版本(2019/2022/其他) | NSSM、Python、MySQL 兼容性 | 公司 IT |
| 2 | 是否允许在生产机安装 Python 3.12 及第三方库 | 应用部署可行性 | 公司 IT |
| 3 | 是否允许 MySQL 8.4 在 Windows Server 安装 | 数据库部署可行性 | 公司 IT |
| 4 | 防火墙是否允许 80 / 5000 端口对内网开放 | 用户访问 | 公司 IT |
| 5 | 公司 SMTP 服务地址、端口、是否需要认证 | 邮件告警 | 公司 IT |
| 6 | 服务器 D:\ 盘可用空间(建议预留 200GB+) | 附件与备份存放 | 公司 IT |
| 7 | 服务器系统时区是否为 Asia/Shanghai | MySQL 自动继承 | 公司 IT |
| 8 | 是否允许 NSSM 工具下载与安装 | Windows 服务化 | 公司 IT |

**这些必须在 Phase 0 阶段就向公司 IT 确认完毕,任何一项卡住都会影响 Phase 7 上线。**

---

## 附录 C:V1.3 必读检查清单

开发启动前请逐项确认:

- [ ] 已阅读 V1.3 全文,理解混合部署的开发/生产差异
- [ ] 已理解 .env.development / .env.production 分离原则,密码绝不入仓
- [ ] 已理解核心表禁止 DELETE 的设计原则
- [ ] 已理解版本升级 vs 加开复制的两种语义边界
- [ ] 已理解审批流顺序模式 vs 并行模式的差异
- [ ] 已与公司 IT 沟通附录 B 的 8 项部署事项,得到初步答复
- [ ] CLAUDE.md 已写入"本系统专属规则(V1.3 完整版)"
- [ ] docs/ 下已建立 00/04/05/06/07/08 占位文档
- [ ] 已为状态机 + 编码生成 + 审批流 + 告警去重 + 计划日期推算 5 个核心模块预留单元测试
- [ ] 已规划生产机预演节奏(Phase 7 之前至少做过 1 次完整空跑)
