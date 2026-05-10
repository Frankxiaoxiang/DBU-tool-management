# CLAUDE.md — DBU 模治具管理系统 AI 协作指南

> 本文件是 AI（Claude / Cursor / Copilot 等）参与本项目开发的**唯一权威指引**。
> 基于《DBU_System_Architecture_Design_V1.4.md》第 5.3 节扩展为完整可运行版本。
>
> ⚠️ **所有 AI 在修改任何代码前必须先完整阅读本文件。** 凡违反铁律的 PR 一律打回。

---

## a. 项目概览

### 业务场景

DBU 模治具管理系统服务于 Stoneplus Thermal Management 制造技术 / 质量管理体系，覆盖 SUS VC（不锈钢均热板）、Cu VC（铜均热板）所有产线，HP（热管）产品后续支持。

业务范围：**模治具全生命周期管理**——需求提出 → 设计 → 采购 → 来料 IQC → 安装调试 → 试产验收 → 移交入库 → 生产领用 → 保养维修 → 报废。

业务文档基线：
- 《DBU模治具全流程管控文件 V2.1》——业务流程、RACI 矩阵、表单清单
- 《DBU模治具编码规则 V1.0》——四字段编码结构、治具型号代号清单

### 技术栈

| 层级 | 技术 | 版本 |
|------|------|------|
| 后端框架 | Flask | 3.x |
| ORM | Flask-SQLAlchemy | 3.x |
| 数据库迁移 | Flask-Migrate (Alembic) | 4.x |
| 认证 | Flask-JWT-Extended | 4.x |
| 异步任务 | Flask-APScheduler 内嵌 | — |
| 数据库 | MySQL（开发 Docker / 生产 Windows 原生） | 8.4 LTS |
| 生产 WSGI | Waitress (threads=32, max_request_body_size=500MB) | — |
| 前端框架 | Vue 3 (Composition API + script setup) | 3.x |
| UI 组件 | Element Plus | 2.x |
| 构建工具 | Vite | 5.x |
| 状态管理 | Pinia（仅全局） | — |
| 路由 | Vue Router | 4.x |
| HTTP | Axios | 1.x |
| 包管理器 | pnpm（前端） / pip（后端） | — |

### 部署方式

**混合部署**：
- **开发机**（ThinkPad Windows 11）：Docker MySQL + 本地 Flask + Vite Dev Server
- **生产机**（公司 Windows Server）：Windows 原生 MySQL + Flask + Waitress（NSSM 注册为服务）+ Flask serve Vue dist

详细部署步骤见 [Doc/08_deployment_windows.md](./Doc/08_deployment_windows.md)。

---

## b. 关键文档导航

| 文档 | 用途 | 修改频率 |
|------|------|----------|
| [Doc/00_open_questions.md](./Doc/00_open_questions.md) | 待确认业务问题清单 | 高（开发中持续累积） |
| [Doc/01_requirement_v2.1.md](./Doc/01_requirement_v2.1.md) | 业务流程与需求基线 | 低（业务文档更新时） |
| [Doc/02_coding_rules_v1.0.md](./Doc/02_coding_rules_v1.0.md) | 治具编码规则与型号代号清单 | 低（编码规则更新时） |
| **[Doc/03_architecture_v1.4.md](./Doc/03_architecture_v1.4.md)** | **★ 权威架构文档** | 中（重大变更时升版本） |
| [Doc/04_api_spec.md](./Doc/04_api_spec.md) | API 端点规约 | 高（每个 API 实现前） |
| [Doc/05_permissions.md](./Doc/05_permissions.md) | 角色权限矩阵（前后端单一来源） | 中 |
| [Doc/06_restore_procedure.md](./Doc/06_restore_procedure.md) | 备份与还原手册 | 低 |
| [Doc/07_export_guideline.md](./Doc/07_export_guideline.md) | 报表导出三档策略 | 低 |
| [Doc/08_deployment_windows.md](./Doc/08_deployment_windows.md) | Windows 生产部署手册 | 低 |
| [Doc/09_dev_rules.md](./Doc/09_dev_rules.md) | 开发铁律（后端 11 + 前端 8） | 中 |
| [TASKS.md](./TASKS.md) | 当前阶段任务进度 | 极高（每日） |

---

## c. 当前阶段

**Phase 0 — 基建（约 1 周）**

详细任务清单见 [TASKS.md](./TASKS.md)。当前阶段重点：

- 开发机环境搭建（Docker MySQL / Python venv / pnpm）
- 生产机预演（Python / MySQL / NSSM 安装）
- Flask app factory + 三套配置 + 通用响应/异常装饰器
- 用户/角色模型 + JWT 登录
- `scripts/seed_data.py` 完整化（超管 / 9 角色 / 11 供应商 / 40+ 治具模板）
- Vue 项目初始化（含 `utils/datetime.js` + axios 409/401 拦截器）

---

## d. 继承自 vc-cost-system 的 Critical Rules

以下规则源自开发者已验证的现有项目 `vc-cost-system`，是踩过的坑总结。新系统**必须遵守**，不可重新踩坑。

### Rule 1：MySQL 编码 utf8mb4

- SQLAlchemy 连接串必须含 `?charset=utf8mb4`
- Model 表定义加 `__table_args__ = {'mysql_charset': 'utf8mb4', 'mysql_collate': 'utf8mb4_unicode_ci'}`
- mysqldump 必须用 `--default-character-set=utf8mb4`
- 关联表（多对多）`db.Table()` 必须显式传 `mysql_charset='utf8mb4'` + `mysql_collate='utf8mb4_unicode_ci'`，**不要依赖** Model 的 `__table_args__`（关联表不走 Model）：
```python
  # ✅
  user_roles = db.Table(
      'user_roles',
      db.Column('user_id', db.BigInteger, db.ForeignKey('users.id'), primary_key=True),
      db.Column('role_id', db.Integer,    db.ForeignKey('roles.id'), primary_key=True),
      mysql_charset='utf8mb4',
      mysql_collate='utf8mb4_unicode_ci',
  )
  # ❌ 遗漏 — 生产机 MySQL server 默认不是 utf8mb4 时建出错误 charset 的表
  user_roles = db.Table('user_roles', db.Column(...), db.Column(...))
```
  本规则覆盖 Phase 1+ 的 `batch_fixtures` / `fixture_attachments` 等所有未来关联表。

### Rule 2：Schema-First — 文档 → Model → 迁移 → MySQL

```
需求/设计文档 → models/*.py → migrations/ → MySQL
```
- 字段变更先改设计文档 → 再改 Model → 再生成迁移
- 严禁绕过 Flask-Migrate 直接 ALTER TABLE
- `flask db migrate` 生成脚本后必须**人工审查**再执行 `flask db upgrade`

### Rule 3：Blueprint 注册不重复前缀

```python
# blueprints/auth.py — 定义不带 url_prefix
auth_bp = Blueprint('auth', __name__)
# app/__init__.py — 注册时统一加
app.register_blueprint(auth_bp, url_prefix='/api/auth')
```
**禁止**两处同时设置 prefix（路径会翻倍）。

### Rule 4：JWT Identity 强转 int

```python
user_id = int(get_jwt_identity())   # get_jwt_identity() 返回字符串，必须强转
```

### Rule 5：PUT/PATCH 字段更新用 `'key' in body`

```python
# ✅ 正确 — 用户填 0 或 null 也能正确更新
if 'planned_date' in body:
    record.planned_date = body['planned_date']

# ❌ 错误 — 值为 0 或 None 时静默丢弃
if body.get('planned_date'):
    record.planned_date = body['planned_date']
```

### Rule 6：API 路由扁平化优先

```
✅ PUT  /api/approval-records/:id
❌ PUT  /api/fixtures/:id/approvals/:approval_id
```

### Rule 7：前端导入用相对路径

vite.config.js 未配置 `resolve.alias`，`@/` 在运行时报 404：

```javascript
// ✅ import { api } from '../../api/fixture.js'
// ❌ import { api } from '@/api/fixture.js'
```

### Rule 8：el-tag 等 type prop 兜底必须合法

```javascript
// ✅
function statusTagType(status) {
  return { pending: 'warning', passed: 'success', failed: 'danger' }[status] || 'info'
}
// ❌ || '' 会触发 prop validation 警告
```

### Rule 9：ElMessageBox.confirm 二段 try/catch

```javascript
try {
  await ElMessageBox.confirm('确认操作？', '提示', { type: 'warning' })
} catch { return }                  // 用户取消，静默退出

try {
  await apiCall()
  ElMessage.success('操作成功')
} catch (err) {
  ElMessage.error(err?.response?.data?.message || '操作失败')
}
```

### Rule 10：v-for 可编辑表格禁用 index 作 key

```javascript
import { nanoid } from 'nanoid'
items.value = data.map(item => ({ ...item, _temp_id: nanoid() }))
// <tr v-for="item in items" :key="item._temp_id">
```

### Rule 11：Element Plus 反馈组件必须显式引入

```javascript
import { ElMessage, ElMessageBox, ElNotification } from 'element-plus'
```

### Rule 12：JWT Token 过滤 'undefined' / 'null' 字符串

```javascript
const token = localStorage.getItem('token')
if (token && token !== 'undefined' && token !== 'null') {
  config.headers.Authorization = `Bearer ${token}`
}
```

### Rule 13：种子数据重置处理外键约束

```python
db.session.execute(text("SET FOREIGN_KEY_CHECKS = 0"))
# 清理所有表
db.session.execute(text("SET FOREIGN_KEY_CHECKS = 1"))
db.session.commit()
```

---

## e. V1.4 专属规则（必须逐项遵守）

### e.1 配置与环境

- ✅ 三套环境：`.env.development` / `.env.production` / `.env.example`，由 `python-dotenv` 按 `FLASK_ENV` 加载
- ✅ Config 必须配 `pool_recycle=3600`（防 MySQL `wait_timeout` 假死）
- ✅ Config 必须配 `pool_pre_ping=True`、`pool_size=10`、`max_overflow=20`
- ✅ Flask logging 必须配 `TimedRotatingFileHandler`，`backupCount=30`
- ✅ APScheduler 实例化时显式 `timezone='Asia/Shanghai'`
- ✅ APScheduler 在 `debug=True` 下加守卫 `if not app.debug or os.environ.get('WERKZEUG_RUN_MAIN') == 'true'`
- 🚫 `.env.*` 必须 gitignore，禁止提交
- 🚫 `config.py` 不得硬编码任何密码或密钥
- ✅ **dotenv 加载顺序铁律**：`load_dotenv()` 必须在**模块顶层**执行，且**早于** `from config import CONFIG_MAP`。
  根因：`config.py` 的 Config 类体在 `import` 时就求值 `os.environ.get(...)`，若 `load_dotenv()` 推迟到 `create_app()` 内部，Config 已被 Python 缓存，`DATABASE_URL` 等永远 `None`，且无报错（极难调试）。
```python
  # ✅ app/__init__.py 模块顶层
  _pre_env = os.environ.get('FLASK_ENV', 'development')
  load_dotenv(Path(__file__).resolve().parent.parent / f'.env.{_pre_env}')
  from config import CONFIG_MAP   # 必须在 load_dotenv 之后

  def create_app(config_name=None):
      ...

  # ❌ 错误：load_dotenv 在 create_app 内
  from config import CONFIG_MAP   # 此时 .env 尚未加载
  def create_app(config_name=None):
      load_dotenv(...)            # 太晚了，CONFIG_MAP 已被求值且缓存
```
- 🚫 严禁在 `create_app()` 内部首次调用 `load_dotenv()`

### e.2 部署

- ✅ 生产用 Waitress（`serve.py` 入口），NSSM 注册为 Windows 服务
- ✅ Waitress：`threads=32`、`max_request_body_size=536870912`（500MB 物理底线）
- ✅ Flask 同时 serve `/api` 与 Vue 静态文件（MVP 方案）
- ✅ 文件路径用 `pathlib.Path` 跨平台处理
- ✅ 数据库中存储相对路径，永远用正斜杠 `/`
- 🚫 不依赖 NSSM 的 stdout/stderr 作为主日志方案

### e.3 禁止物理删除核心表

- ✅ `projects` / `batches` / `fixtures` / `purchase_orders` 等核心表"作废"走 `status='cancelled'`
- ✅ 配置型表（users / suppliers / fixture_templates）走 `is_active=FALSE`
- ✅ 真·删除仅 `scripts/reset_db.py` 提供
- 🚫 在 Blueprint 中定义 `methods=['DELETE']` 路由删除核心表

### e.4 状态机三函数清晰职责

状态变更必须走 `services/state_machine.py` 三个函数：

| 函数 | 职责 | 校验 |
|------|------|------|
| `transition()` | 正常流转 | 严格走 `TRANSITIONS`，**禁止**包含 `force` / `bypass` 参数 |
| `reject()` | 审批驳回回退 | 走 `REJECT_CONFIG` 配置的合法路径 |
| `force_transition()` | 超管强制跳转 | **唯一**绕过 `TRANSITIONS` 的入口，必填 reason，自动写审计日志 |

铁律：
- ✅ 改流程时同步 5 处：`state_machine.py` / `status_history` 表 / 前端 `status.js` / i18n / 文档
- 🚫 任何代码直接 `fixture.current_status = ...`
- 🚫 `transition()` 函数签名再次出现 `force` 参数（V1.4 已消除后门）

### e.5 乐观锁仅手动校验

- ✅ 所有写操作请求体含 `version` 字段
- ✅ Service 层手动 `if record.version != request_version: raise ConflictError(...)`，更新后 `record.version += 1`
- ✅ 全局 `@app.errorhandler(StaleDataError)` 兜底返回 409
  - SQLAlchemy 2.x 的导入路径是 `from sqlalchemy.orm.exc import StaleDataError`
  - **不是** `from sqlalchemy.exc import StaleDataError`（2.x 已移除该路径，仍写会 `ImportError`）
  - 写错时 errorhandler 不会注册成功，乐观锁冲突会变成 500 而非 409，且无报错日志
- ✅ 关键写入路径 Service 层加 `assert request_version is not None` 守卫
- 🚫 **严禁**在任何 Model 上加 `__mapper_args__ = {'version_id_col': version}`
  （ORM 自动版会与手动版冲突，V1.1/V1.2/V1.3 错误设计已纠偏）

### e.6 审批流双模式

- ✅ 所有审批流共用一套引擎（IQC不合格 / 让步接受 / 紧急上机 / 试产不合格 / 报废 / 解封）
- ✅ 通过 `flow_type + sequential_or_parallel` 区分场景与执行模式
- ✅ `approved` 与 `rejected` 都透传 `decision_type` 字段
- ✅ 审批通知 MVP 阶段统一用邮件
- 🚫 为每种业务场景写独立审批流代码

### e.7 编码与版本

- ✅ 编码由后端 `services/code_generator.py` 生成，遵循《编码规则 V1.0》
- ✅ 加开-加量复制时 `current_version_code` **继承源治具当前版本**
- ✅ 版本升级（A1→A2、A3→B1）只改图纸版本字段，**不新建 fixture**
- ✅ `fixtures.parent_fixture_id` 仅用于"加开-复制图纸"场景溯源
- 🚫 在前端拼接编码

### e.8 快照机制

- ✅ 项目创建时锁定模板快照写入 `project_template_snapshots`
- ✅ 模板库后续修改时通过 `sync_missing_templates()` **仅追加**同步（不覆盖已有）
- ✅ 同步操作必须写审计日志
- 🚫 模板库修改反向覆盖已有项目快照

### e.9 邮件告警事务隔离

- ✅ 所有告警走 `services/alert_service.py:send_alert_dedup()`
- ✅ `send_alert_dedup` 必须 `try/except` 包裹完整逻辑
- ✅ 失败时 `db.session.rollback()` + `current_app.logger.error(..., exc_info=True)`，**不抛出**
- ✅ 循环调用场景下单封邮件失败不株连后续告警
- ✅ 紧急阈值常量 `URGENT_THRESHOLD_DAYS = 3`

### e.10 前端时间处理

- ✅ 处理后端 datetime 字符串一律走 `utils/datetime.js` 的 `parseBackendTime(str)` / `formatBackendTime(str, fmt)`
- ✅ `main.js` 顶层 `import './utils/datetime'` 副作用导入，确保 `dayjs.tz.setDefault('Asia/Shanghai')` 生效
- 🚫 **严禁**裸调用 `dayjs(str)` 或 `new Date(str)`（浏览器按本地时区解析，海外/异地访问会偏差）

### e.11 报表导出三档策略(严格对齐 V1.3)

| 档位 | 场景 | 实现 |
|------|------|------|
| 第一档 | **单表列表 < 1000 条** | 前端 `xlsx` 库(SheetJS)直接生成 |
| 第二档 | **多表关联 / >1000 条** | 后端 `openpyxl(write_only=True)` + 数据库游标分批,流式响应 |
| 第三档 | **月度大报表** | APScheduler 每月 1 日 02:30 自动生成,结果存 `attachments`,用户去附件中心下载 |

- 🚫 **严禁**使用 `pandas.DataFrame.to_excel`
- 🚫 **严禁**使用 `openpyxl` 默认(非 write_only)模式
- 🚫 **严禁**`query.all()` 一次性加载万行数据
- 🚫 **严禁**任何"用户触发的异步导出 + 邮件下载链接 / 状态轮询"工作流(V1.3 明确不采用此模式,如有特殊需求需经架构评审)

### e.12 删除策略小结

| 表类型 | 处理方式 |
|--------|----------|
| 核心表（projects/batches/fixtures/purchase_orders） | `status='cancelled'`，无 DELETE 接口 |
| 配置表（users/suppliers/fixture_templates） | `is_active=FALSE` |
| 真·删除 | 仅 `scripts/reset_db.py` 提供 |

---

## f. 编码规约引用

代码层面的命名规范、文件组织、Code Review Checklist 等详见 **[Doc/09_dev_rules.md](./Doc/09_dev_rules.md)**。

后端 11 条铁律 + 前端 8 条铁律均在该文档中完整罗列，所有 PR 必须逐条核对。

---

## g. 工作方式

### Schema-First

任何数据库字段变更必须：
1. 先更新设计文档（[Doc/03_architecture_v1.4.md](./Doc/03_architecture_v1.4.md) 第 2 章）
2. 再修改 `models/*.py`
3. 执行 `flask db migrate -m "描述变更"`
4. **人工审查**生成的迁移脚本（确保无误删字段、无破坏性修改）
5. 执行 `flask db upgrade` 应用迁移
6. 单元测试通过
7. 同步更新 [Doc/04_api_spec.md](./Doc/04_api_spec.md) 中受影响的 API 字段

### API 先写 spec 再实现

任何新 API 必须：
1. 先在 [Doc/04_api_spec.md](./Doc/04_api_spec.md) 中加入条目（方法、路径、说明、请求体、响应体）
2. 在 [Doc/05_permissions.md](./Doc/05_permissions.md) 标注权限要求
3. 写测试用例（至少含成功路径 + 权限拒绝 + 数据校验失败 3 种场景）
4. 实现 Service + Blueprint
5. 前端调用与集成

### 关键流程改动同步 5 处

改动状态机时必须同步：
1. `services/state_machine.py`（TRANSITIONS / REJECT_CONFIG）
2. `status_history` 表的字段定义
3. 前端 `utils/status.js`（颜色映射 + 标签）
4. 前端 i18n 文件（中英文标签）
5. [Doc/03_architecture_v1.4.md](./Doc/03_architecture_v1.4.md) 第 3.3 节文档

### 文档同步铁律

每轮讨论产生的结论、变更、澄清，必须更新到 Doc/ 下的对应文档中。
**不允许"口头确认但文档未更新"的情况。**

---

## h. AI 协作风险点提醒

以下是开发者已识别的 AI 容易踩的坑（V1.4 第 5.4 节），AI 必须主动规避：

| 风险 | 缓解措施 |
|------|----------|
| 在 Model 中无脑加 `__mapper_args__` 自动版 | 写代码前 grep `version_id_col` 全文必须无匹配 |
| 在 `transition()` 中加回 force 参数 | 写代码前查 [Doc/09_dev_rules.md](./Doc/09_dev_rules.md) 后端 #3 |
| 告警循环中漏写 try/except | 全文搜 `send_alert_dedup` 检查每个调用点 |
| 前端用 `dayjs(str)` 或 `new Date(str)` | eslint `no-restricted-syntax` 规则拦截 |
| 自由发挥加 DELETE 端点 | 全文搜 `methods=['DELETE']` 检查 |
| 用 `pandas.to_excel` / `openpyxl` 默认模式 | 全文搜 `to_excel`、`Workbook(` 检查 |
| 改状态机漏改 5 处 | 跟随本文 §g 工作方式核对 |
| 前端用 `@/` 路径别名 | 全文搜 `from '@/` 检查 |
| 自定义业务异常类与 Python 内置名冲突（如 `PermissionError`、`ValueError`、`TypeError`、`NotImplementedError`） | HTTP 403 用 `ForbiddenError`；422 用 `UnprocessableError` 或自定义 `ValidationError`；全文搜 `class PermissionError` / `class ValueError` 等内置名必须无匹配 |

---

## i. 紧急联络

- 项目代码仓库：（待填）
- 业务对接人：（待填）
- 公司 IT 联络：（待填）

---

> ⚠️ **再次强调：所有 AI 在修改任何代码前必须先完整阅读本文件。**
>
> 凡违反本文 §d / §e 任意一条规则的 PR / Commit 一律打回重做。
> 项目代码仓库根目录的 CLAUDE.md 永远引用 [Doc/03_architecture_v1.4.md](./Doc/03_architecture_v1.4.md) 为权威架构来源。

---

## j. 修订记录

| 日期 | 内容 | 操作人 |
|------|------|--------|
| 2026-04-29 | 基于 Phase 0.3 实施反馈补入：§e.1 dotenv 加载顺序铁律、§d Rule 1 关联表 charset 子条、§e.5 StaleDataError 导入路径补充、§h 异常命名陷阱新增行 | Frank |
| 2026-05-10 | Phase 0.5 落位：① Doc/09_dev_rules.md 内 7 处 `docs/` 显示文本修正为 `Doc/`；② Doc/09_dev_rules.md 同步本表 2026-04-29 写入的 4 条 Phase 0.3 实战教训（后端 #1 dotenv 顺序、#7 StaleDataError 2.x 路径、#11 关联表 charset、命名约定表"自定义异常类"行）+ Checklist 后端段新增 4 项 | Claude |
