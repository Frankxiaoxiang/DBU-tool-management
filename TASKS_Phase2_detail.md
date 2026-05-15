## Phase 2 — 模治具核心模块（已细化）

> **细化原则**：每个 Step 在一次 CLI session 内可独立完成并验收；前置依赖严格顺序；**严禁越界至 Phase 3+**（审批流引擎、PO 头/items、IQC/试产/维修等业务单据均不在本阶段；如出现接口依赖，用 `501` 占位并注明 `TODO Phase X`）。
>
> **共 8 个子模块、16 个 Step**。两条硬顺序约束（来自架构铁律）：
> 1. `services/code_generator.py` 的 `generate_fixture_code()` 与 `services/state_machine.py` **必须排在治具 CRUD（2-3-1）之前**。
> 2. `services/state_machine.py`（2-2-1）**必须早于任何含状态流转的 Step**（2-3-1 的 `PATCH /status`、2-4-1 的 `version-bump`、2-5-1 的 `copy-to-batch`、2-7-1 的 `batch-seal`）——CLAUDE.md §e.4 铁律。
>
> **Frank 三项裁决（2026-05-15，原开放问题①②③已关闭）**：
> - ✅ **保留 `fixtures.status`**：与 `current_status`（12 状态机）两个正交维度，`status` 走 `active`/`cancelled` 行政作废，`current_status` 走工艺流程；同 `projects`/`batches` 一致（§e.3/§e.12）。
> - ❌ **不新建 `fixture_version_history` 表**：图纸版本升级复用 `fixture_status_history`，写 `trigger_type='version_bump'` + `from_status==to_status==current_status` + `reason` 记版本变化；与 `seal_batch` 同属"辅助事件直接 INSERT history、不调 `transition()`"模式。
> - ✅ **`batch-seal` 纳入 Phase 2**：新增 Step 2-7-1（`seal_batch()` + `POST /api/fixtures/batch-seal`），`is_sealed/sealed_at/sealed_by` 字段在 2-0-2 随建；`unseal` 审批流仍留 Phase 4。
>
> **细化依据**：Fixture 字段清单已结合上述裁决与《编码规则 V1.0》+ §3.3.x 收口；由于 V1.4 文档 §2.3 fixtures 部分仅写"DDL 同 V1.3"且 V1.3 文档不在仓库，**Step 2-0-1 须先把 §2.3 fixtures DDL 补写完整**（以本文件 2-0-2 字段清单为基础），2-0-2 执行时再据此对齐，符合 Schema-First 铁律。

---

### 2.0 准备与基础数据层

#### Step 2-0-1：API spec §2 核对 + §2.3 fixtures DDL 补写 + 模治具端点权限矩阵补全
- 涉及文件：`Doc/04_api_spec.md`（§2 核对）、`Doc/03_architecture_v1.4.md`（**§2.3 fixtures DDL 补写**——V1.4 当前仅为"DDL 同 V1.3"占位，V1.3 不在仓库；以本文件 Step 2-0-2 字段清单为基础落地为正式 DDL）、`Doc/05_permissions.md`（新增模治具端点 `@require_role` 映射段）、`Doc/00_open_questions.md`（关闭 Q-006/Q-007/Q-008——见 Frank 2026-05-15 三项裁决——并登记 2-7-1 衍生的小决策项）
- 前置条件：Phase 1 已全部关闭（2026-05-14）。这是 CLAUDE.md §g「API 先写 spec 再实现」+ Schema-First 的强制前置动作，不写代码——参照 Phase 1 Step 1-0-1 的做法。
- 模板类型：**手写提示词（无对应模板）**
- 关键参数：
  - 核对 `04_api_spec.md` §2「模治具核心」12 端点 + `trigger` 取值表与本细化文件一致；不一致处先改文档
  - **§2.3 fixtures DDL 补写**：以本文件 Step 2-0-2 的字段清单为基础，生成与 §2.3 `projects` DDL 同款的 fixtures `CREATE TABLE` 块（含 `is_sealed`/`sealed_at`/`sealed_by` 封存字段、`status` 行政作废字段、`current_status` 工艺流程字段、`version` 手动乐观锁字段），并在 §2.3 末尾追加修订记录一行注明"V1.4 补写自 Phase 2 Step 2-0-1，Frank 2026-05-15 三项裁决落定"
  - `05_permissions.md` 新增模治具端点 `@require_role` 映射：治具新建/编辑 = `super_admin + pm + me`（待 Frank 定）；`PATCH /:id/status` 按 trigger 分场景（IQC 相关 = `iqc`、安装 = `me`、领用归还 = `production_lead/warehouse`）；`POST /:id/force-status` **限 `super_admin`**；`version-bump`/`copy-to-batch` = `super_admin + pm + design_engineer`；**`POST /api/fixtures/batch-seal` = `super_admin + warehouse`**（§3.3.x 业务规则）
  - 在 `00_open_questions.md` 登记 2-7-1 衍生的一个待 Frank 拍板的小决策（见 2-7-1 关键参数最后一项）：`seal_batch` 时 `fixture.current_status` 是否同步改为 `sealed`，还是只置 `is_sealed=True`（§3.3.x 文本与代码示例存在轻微张力）
  - 输出物：三份文档 diff + `CLAUDE.md` §j / `TASKS.md` 修订记录各追加一行
  - **铁律落地**：文档先行（§g Schema-First / API 先写 spec）；**不把权限来源复制进本细化文件**，避免双来源漂移；本步零代码。

#### Step 2-0-2：Fixture Model + Migration
- 涉及文件：`backend/app/models/fixture.py`（新建）、`backend/app/models/__init__.py`、`backend/migrations/versions/<新>.py`
- 前置条件：Step 2-0-1 完成（spec & 权限定稿，开放问题已登记）；Batch / Project / User / Supplier 四表 Phase 0–1 已存在（fixtures 外键依赖）
- 模板类型：**T01**
- 关键参数：
  - 表名 `fixtures`、类名 `Fixture`、文件名 `fixture`、table_kind=`core`
  - 架构文档章节号填 `2.3 三层数据结构核心字段`
  - **字段清单（已对齐 Frank 2026-05-15 三项裁决，Step 2-0-1 据此补写 §2.3 fixtures DDL，CLI Step 1 字段对齐时与该 DDL 逐字段核对）**：
    `id BIGINT PK`、`fixture_code VARCHAR(32) UNIQUE NOT NULL`（系统按编码规则生成）、`batch_id BIGINT NOT NULL FK batches.id`、`project_id BIGINT NOT NULL FK projects.id`（冗余便于按项目过滤，与 `batch.project_id` 一致性由 Service 层保证）、`fixture_type_code VARCHAR(16) NOT NULL`（治具型号代号，如 `FB-YN`）、`set_no INT NOT NULL`（套号 #N 的 N，从 1）、`current_version_code VARCHAR(8) NOT NULL DEFAULT 'A1'`（图纸版本 A1/A2/A3/B1…）、`current_status VARCHAR(16) NOT NULL DEFAULT 'pending_iqc'`（12 状态机，**VARCHAR 不用 ENUM**，Service 层校验）、`parent_fixture_id BIGINT NULL FK fixtures.id`（自引用，仅"加开-复制图纸"溯源）、`supplier_id BIGINT NULL FK suppliers.id`（采购前未定故可空）、`lead_time_days INT NULL`、`planned_arrival_date DATE NULL`、`is_sealed BOOLEAN NOT NULL DEFAULT FALSE`、`sealed_at DATETIME NULL`、`sealed_by BIGINT NULL FK users.id`（封存机制字段，§3.3.x；`seal_batch()` Service 见 Step 2-7-1）、`status VARCHAR(16) NOT NULL DEFAULT 'active'`（**Frank 裁决保留**：与 `current_status` 正交——`status` 走 active/cancelled 行政作废，`current_status` 走 12 状态机；同 `projects`/`batches` 一致，§e.3/§e.12）、`version INT NOT NULL DEFAULT 0`、`created_by BIGINT NOT NULL FK users.id`、`created_at / updated_at`
  - 索引：`idx_batch(batch_id)`、`idx_project(project_id)`、`idx_status(current_status)`、`idx_type(fixture_type_code)`、`idx_parent(parent_fixture_id)`
  - **铁律落地**：`__table_args__` 含 `mysql_charset='utf8mb4'`（§d Rule 1）；**严禁** `__mapper_args__ = {'version_id_col': version}`（§e.5 / §h，写代码前 grep `version_id_col` 必须无匹配）；Model import **必须** `from extensions import db`，**不得** `from app.extensions import db`（§h 高频笔误）；core 表无 DELETE 接口；`fixture_code` 由后端 `code_generator` 生成，**禁止前端拼接**（§e.7）。

#### Step 2-0-3：FixtureStatusHistory Model + Migration
- 涉及文件：`backend/app/models/fixture_status_history.py`（新建）、`backend/app/models/__init__.py`、`backend/migrations/versions/<新>.py`
- 前置条件：Step 2-0-2 完成（`fixtures` 表已 `flask db upgrade`，本表 `fixture_id` 外键依赖）
- 模板类型：**T01**
- 关键参数：
  - 表名 `fixture_status_history`、类名 `FixtureStatusHistory`、文件名 `fixture_status_history`、table_kind=`business_record`
  - 架构文档章节号填 `2.5 状态机历史表`
  - 字段清单（对齐 §3.3 `transition()`/`reject()`/`force_transition()` 三函数实际写入字段）：`id BIGINT PK`、`fixture_id BIGINT NOT NULL FK fixtures.id`、`from_status VARCHAR(16) NULL`（首条记录可空）、`to_status VARCHAR(16) NOT NULL`、`trigger_type VARCHAR(32) NOT NULL`（`normal`/`iqc_pass`/…/`return_repair`/`forced`）、`reason VARCHAR(512) NULL`、`related_table VARCHAR(64) NULL`、`related_id BIGINT NULL`、`operator_id BIGINT NOT NULL FK users.id`、`created_at DATETIME DEFAULT CURRENT_TIMESTAMP`
  - 索引：`idx_fixture(fixture_id)`、`idx_created(created_at)`
  - **铁律落地**：`business_record` 表**只增不改不删**——**不要** `version` 字段、**不要** `status` 字段（T01 文档约束 #3）；`__table_args__` 含 `utf8mb4`；import 用 `from extensions import db`；**严禁** `__mapper_args__`。

#### Step 2-0-4：AuditLog Model + Migration
- 涉及文件：`backend/app/models/audit_log.py`（新建）、`backend/app/models/__init__.py`、`backend/migrations/versions/<新>.py`
- 前置条件：Step 2-0-1 完成（无表级外键依赖，仅 `users.id`）。本表是 §3.3 `force_transition()` → `audit_service.log_force_action()` 的写入目标，必须早于 2-2-1。
- 模板类型：**T01**
- 关键参数：
  - 表名 `audit_logs`、类名 `AuditLog`、文件名 `audit_log`、table_kind=`business_record`
  - 架构文档章节号填 `2.8 审计日志表`（⚠️ §2.8 在本次阅读范围外仅为标题，T01 Step 1 必须打开 §2.8 核对实际字段定义后再落地）
  - 字段清单（推导版，对齐 §3.3 测试 `AuditLog...filter_by(action='force_status')` 的用法）：`id BIGINT PK`、`action VARCHAR(64) NOT NULL`（如 `force_status`）、`target_table VARCHAR(64) NULL`、`target_id BIGINT NULL`、`detail TEXT NULL`（存 from/to/reason 等）、`operator_id BIGINT NOT NULL FK users.id`、`created_at DATETIME DEFAULT CURRENT_TIMESTAMP`
  - 索引：`idx_action(action)`、`idx_operator(operator_id)`、`idx_created(created_at)`
  - **铁律落地**：`business_record` 只增不改不删——无 `version` / 无 `status`；`__table_args__` 含 `utf8mb4`；import 用 `from extensions import db`；审计日志**查询端点属 Phase 6**，本步只建表，**不建** Blueprint。

---

### 2.1 编码自动生成

#### Step 2-1-1：code_generator.generate_fixture_code()
- 涉及文件：`backend/app/services/code_generator.py`（**扩展，非新建**——Phase 1 Step 1-1-2 已创建并含 `generate_project_code()`）
- 前置条件：Step 2-0-2 完成（`generate_fixture_code()` 需查询 `fixtures` 表计算同项目同型号的下一个套号）
- 模板类型：**T02（裁剪：仅扩展 Service 函数，本步不新建 Blueprint、不新建端点）**
- 关键参数：
  - 新增函数 `generate_fixture_code(project_code, fixture_type_code, version_code)` → 返回 `[项目代号]-[治具型号代号]#[套号]-[版本号]`，如 `EGL-FB-YN#1-A1`（四字段结构见《编码规则 V1.0》§2.1）
  - 套号规则：同 `project_id` + 同 `fixture_type_code` 已有记录数 + 1，从 `#1` 连续递增（《编码规则》§2.2 / §7.1 Step 6）
  - 版本号默认 `A1`；加开-复制场景由调用方（2-5-1）传入"继承的源治具当前版本"
  - 不在本步范围：图纸版本升级算法（→ 2-4-1）、加开复制（→ 2-5-1）
  - **铁律落地**：编码由后端生成、**禁止前端拼接**（§e.7）；查询用 `db.session.get(Model, pk)` / `select()`，**不用** `Model.query.get()`（§h 废弃 API）；套号并发生成需依赖 `fixture_code` 的 `UNIQUE` 约束兜底（Service 捕获 `IntegrityError` 重试或抛 `ConflictError`）。

---

### 2.2 状态机三函数

#### Step 2-2-1：state_machine.py 三函数 + audit_service + 前端状态映射 + 文档同步
- 涉及文件：`backend/app/services/state_machine.py`（新建）、`backend/app/services/audit_service.py`（新建，仅 `log_force_action`）、`backend/app/utils/enums.py`（确认/补 `FixtureStatus` 12 状态常量）、`frontend/src/utils/status.js`（扩展 fixture 12 状态颜色+标签）、i18n 标签字典、`Doc/03_architecture_v1.4.md`（§3.3 核对一致 + 修订记录）、`Doc/04_api_spec.md`（§2 trigger 取值表核对）
- 前置条件：Step 2-0-3（`FixtureStatusHistory` 表）+ Step 2-0-4（`audit_logs` 表）完成——三函数分别写这两张表
- 模板类型：**T05**
- 关键参数：
  - **本步是"把 §3.3 完整代码逐字落地"**：12 状态无新增、`TRANSITIONS` / `REJECT_CONFIG` 无新增触发器——若 CLI 发现需新增 status 或 trigger，**停下来等架构评审**（T05 Step 1 铁律）
  - `transition(fixture, to_status, trigger, operator_id, reason=None, related=None)` — 严格走 `TRANSITIONS`
  - `reject(fixture, operator_id, reason)` — 走 `REJECT_CONFIG`（`IQC_INSPECTING→PENDING_IQC` / `ACCEPTANCE_TESTING→INSTALLING`）
  - `force_transition(fixture, to_status, operator_id, reason)` — 唯一绕过 `TRANSITIONS` 的入口，必填 `reason`，调 `audit_service.log_force_action()` 写 `audit_logs`
  - `audit_service.log_force_action(fixture, from_status, to_status, operator_id, reason)` — 写一条 `AuditLog(action='force_status', ...)`；**审计查询端点属 Phase 6，本步不实现**
  - `state_machine.py` / `audit_service.py` 的 import 风格**参照 Phase 1 现有 service**（`project_service.py` / `batch_service.py`），**不照抄** §3.3 文档示例里的 `from app.models import`
  - **本步不触碰 `fixtures` Blueprint**（尚未创建）——`PATCH /status` 的 trigger 分发在 Step 2-3-1 接入；T05 标准 Step 4 在本阶段顺延
  - **铁律落地**：`transition()` 函数签名**严禁**出现 `force` / `bypass` 参数（§e.4 / §h，V1.4 已消除 V1.2 后门）；`force_transition` 是**唯一**绕过 `TRANSITIONS` 的入口；除 `state_machine.py` 内部外，任何代码**严禁** `fixture.current_status = ...`；改状态机**同步 5 处**（§g）；`StaleDataError` 从 `sqlalchemy.orm.exc` 导入（§e.5）。

---

### 2.3 治具 CRUD

#### Step 2-3-1：fixture_service + fixtures Blueprint（CRUD + 状态流转端点）
- 涉及文件：`backend/app/services/fixture_service.py`（新建）、`backend/app/blueprints/fixtures.py`（新建）、`backend/app/__init__.py`（注册 Blueprint）
- 前置条件：Step 2-1-1（`generate_fixture_code` 就绪，`POST /fixtures` 需调用）+ Step 2-2-1（`state_machine` 三函数就绪，`PATCH /status` 与 `POST /force-status` 需调用）。**本步含状态流转，必须在 2-2-1 之后**。
- 模板类型：**T02**
- 关键参数：
  - 资源路径 `fixtures`、端点清单（6 个）：`POST /`（新建治具，调 `generate_fixture_code` 生成 `fixture_code`）、`GET /`（列表，支持 `project_id`/`batch_id`/`current_status`/`fixture_code` 模糊 + 分页）、`GET /:id`（详情）、`PUT /:id`（编辑基本信息，含 `version`）、`PATCH /:id/status`（trigger 分发：常规 trigger → `transition()`，审批驳回类 → `reject()`）、`POST /:id/force-status`（→ `force_transition()`）
  - **不在本步范围**：`POST /:id/version-bump`（→ 2-4-1）、`POST /:id/copy-to-batch`（→ 2-5-1）、`POST /batch-seal`、`POST /:id/release-seal`（见文末范围边界提示）、`GET /export`（→ Phase 6）、`POST /:id/recalc-dates`（→ Phase 5 计划日期）——如端点框架需占位，统一返回 `501` 并注明 `TODO Phase X`
  - 权限矩阵：见 Step 2-0-1（本文件不复制权限来源）
  - **铁律落地**：Blueprint 定义**不带** `url_prefix`，注册时统一加 `/api/fixtures`（§d Rule 3）；core 表**禁止** `methods=['DELETE']`（§e.3 / §e.12）；`PUT/PATCH` 字段更新用 `'key' in body`，**禁止** `body.get('key')`（§d Rule 5）；乐观锁手动校验 `record.version != body['version']` 抛 `ConflictError`、更新后 `version += 1`（§e.5）；状态变更**必须**走 `state_machine` 三函数，**严禁** Blueprint/Service 直接 `current_status = ...`（§e.4）；`POST /force-status` **唯一**调用 `force_transition()` 的端点、`@require_role('super_admin')`；JWT identity 强转 `int(get_jwt_identity())`（§d Rule 4）；`POST /` 与 `GET /`（list）路由**加尾部斜杠**（§h curl 308 陷阱）；统一走 `success_response` / `error_response`，禁止裸 `jsonify`。

#### Step 2-3-2：FixtureList 前端列表页
- 涉及文件：`frontend/src/views/fixture/FixtureList.vue`（新建）、`frontend/src/api/fixture.js`（新建）、`frontend/src/router/index.js`（追加路由）
- 前置条件：Step 2-3-1 完成（`GET /api/fixtures` 列表接口已通）；`utils/status.js` 的 fixture 状态映射已在 Step 2-2-1 落地
- 模板类型：**T03**
- 关键参数：
  - 列：治具编号（可点详情）/ 所属批次 / 治具型号代号 / 套号 / 当前版本 / 当前状态（`el-tag` 走 `status.js`）/ 供应商 / 计划到货日（走 `formatBackendTime`）
  - 搜索：`project_id` 下拉 / `batch_id` 下拉 / `current_status` 下拉 / `fixture_code` 模糊 / 分页
  - 操作列：详情 / 编辑（按权限）；状态流转、版本升级、加开-复制按钮留对应后续 Step 接入
  - 路由：列表页支持"场景 A"（`/projects/:projectId/batches/:batchId/fixtures`）与"场景 B"（`/fixtures` 全局列表），与 Phase 1 BatchList 双场景一致
  - **铁律落地**：前端 import 用**相对路径**，**禁止** `@/`（§d Rule 7）；`el-tag` 等 `type` prop 兜底必须合法（`|| 'info'`，不能 `|| ''`，§d Rule 8）；状态颜色统一从 `utils/status.js` 取，**禁止**组件内硬编码；时间字段走 `parseBackendTime`/`formatBackendTime`，**严禁**裸 `dayjs(str)` / `new Date(str)`（§e.10）；`ElMessage`/`ElMessageBox` 显式 import（§d Rule 11）；`ElMessageBox.confirm` 二段 try/catch（§d Rule 9）。

#### Step 2-3-3：FixtureForm 前端表单页（create/edit/detail 三合一）
- 涉及文件：`frontend/src/views/fixture/FixtureForm.vue`（新建）、`frontend/src/api/fixture.js`（追加 `getFixtureById`/`createFixture`/`updateFixture`）、`frontend/src/router/index.js`（替换占位为真实组件）
- 前置条件：Step 2-3-1（`POST` / `GET /:id` / `PUT` 已通）+ Step 2-3-2（`api/fixture.js` 与路由骨架已建）
- 模板类型：**T04**
- 关键参数：
  - 模式：`create` / `edit` / `detail` 三合一（参照 Phase 1 ProjectForm / BatchForm 模式）
  - 字段表：所属批次（create 时必选，决定 `project_id`）/ 治具型号代号（从模板库按产品类型过滤的下拉）/ 套数（create 时输入，由后端逐套生成编码）/ 供应商（可空，可后补）/ 计划到货日 / LT 天数；`fixture_code`、`current_version_code`、`current_status` 在 detail 模式**只读展示**（编码后端生成、版本走 2-4、状态走流转端点）
  - **铁律落地**：相对路径 import；`version` 字段从最近一次 GET 带回、`PUT` 提交时携带（乐观锁，§e.5）；`parseBackendTime` 处理后端时间；提交走 `ElMessageBox` 二段 try/catch + `ElMessage` 反馈（§d Rule 9/11）；`fixture_code` **只读**，前端不拼接（§e.7）。

---

### 2.4 图纸版本管理

#### Step 2-4-1：fixture_service.version_bump() + POST /api/fixtures/:id/version-bump
- 涉及文件：`backend/app/services/fixture_service.py`（扩展）、`backend/app/blueprints/fixtures.py`（追加端点）
- 前置条件：Step 2-3-1 完成（`fixture_service` 与 `fixtures` Blueprint 已建）。**含状态/版本变更，必须在 2-2-1 之后。**
- 模板类型：**T02**
- 关键参数：
  - 新增 `version_bump(fixture_id, request_version, operator_id)`：按《编码规则 V1.0》§4.2 规则推进 `current_version_code`——`A1→A2→A3`（A 系上限 A3），`A3→B1`，`B1→B2→B3`，依此类推；规则校验在 **Service 层**
  - 端点 `POST /api/fixtures/:id/version-bump`，请求体含 `version`（乐观锁）；**只改 `current_version_code` 字段，不新建 fixture**（§e.7）
  - **History 写入（Frank 2026-05-15 裁决）**：版本升级**复用** `fixture_status_history` 表——`version_bump()` 成功后 Service **直接 INSERT** 一条 `FixtureStatusHistory(fixture_id=fixture.id, from_status=fixture.current_status, to_status=fixture.current_status, trigger_type='version_bump', reason=f"图纸版本升级: {old_ver} → {new_ver}", operator_id=operator_id)`——`from_status==to_status==current_status`（工艺状态不变），版本差异记入 `reason`。**不调 `transition()`**：版本升级不是状态机流转，`transition()` 会因 `from→from` 无 TRANSITIONS 路径而拒绝；此为与 `seal_batch`（Step 2-7-1）一致的"辅助事件直接写 history、不走状态机"模式。
  - 因此本步对 `fixture_status_history` 表为**直接 INSERT**（与 `state_machine.py` 写入同表，但不经其函数），需在 Service 注释中明确标记 `# auxiliary event: bypasses state_machine.transition() by design`（防止后续 CLI 误改为调状态机）
  - **铁律落地**：版本升级**只改图纸版本字段、不新建 fixture、不产生新套号**（§e.7 / 《编码规则》§4.2）；乐观锁手动校验 `version` + 自增；`PUT/PATCH` 类更新用 `'key' in body`；端点路径**不引入"动词"**之外的嵌套层级（扁平化，§d Rule 6）。

#### Step 2-4-2：FixtureForm/Detail「图纸版本升级」按钮
- 涉及文件：`frontend/src/views/fixture/FixtureForm.vue`（detail 模式追加按钮）、`frontend/src/api/fixture.js`（追加 `bumpFixtureVersion`）
- 前置条件：Step 2-4-1（端点已通）+ Step 2-3-3（FixtureForm 已建）
- 模板类型：**T04（扩展，参照 Phase 1 Step 1-2-4 的"追加按钮"做法）**
- 关键参数：
  - detail 模式追加"图纸版本升级"按钮，`hasPermission` 控制可见性；点击 `ElMessageBox.confirm` 提示"将从 `A1` 升级到 `A2`"，确认后调 `bumpFixtureVersion`，成功 toast 新版本号并刷新详情
  - **铁律落地**：相对路径 import；`ElMessageBox` 二段 try/catch（用户取消静默退出）；按钮权限 `hasPermission` 控制；请求携带最新 `version`。

---

### 2.5 加开-复制图纸

#### Step 2-5-1：fixture_service.copy_to_batch() + POST /api/fixtures/:id/copy-to-batch
- 涉及文件：`backend/app/services/fixture_service.py`（扩展）、`backend/app/blueprints/fixtures.py`（追加端点）
- 前置条件：Step 2-3-1（`fixture_service`/Blueprint 已建）+ Step 2-1-1（`generate_fixture_code` 需为新治具生成递增套号）
- 模板类型：**T02**
- 关键参数：
  - 新增 `copy_to_batch(source_fixture_id, target_batch_id, operator_id)`：以源治具为模板**生成新 fixture**，`parent_fixture_id` = 源治具 id（溯源），套号由 `generate_fixture_code` 在目标项目+型号下递增，`current_version_code` **继承源治具当前有效版本**（§e.7 / 《编码规则》§4.3 "EGL-FB-YN#2-A3" 示例）
  - 端点 `POST /api/fixtures/:id/copy-to-batch`，请求体含 `target_batch_id`
  - 新 fixture 是 core 表，走正常 create 路径（`current_status` 默认 `pending_iqc`、`version=0`、`status='active'`）
  - **铁律落地**：`parent_fixture_id` **仅用于**"加开-复制图纸"场景溯源（§e.7），不得挪作他用；`current_version_code` 继承源治具当前版本（§e.7）；套号由后端 `code_generator` 递增生成，**禁止前端拼接**（§e.7）；core 表无 DELETE。

#### Step 2-5-2：FixtureList/Form「加开-复制」按钮
- 涉及文件：`frontend/src/views/fixture/FixtureList.vue`（操作列追加按钮）或 `FixtureForm.vue`（detail 模式追加）、`frontend/src/api/fixture.js`（追加 `copyFixtureToBatch`）
- 前置条件：Step 2-5-1（端点已通）+ Step 2-3-2 / 2-3-3（列表页/表单页已建）
- 模板类型：**T04（扩展）**
- 关键参数：
  - 追加"加开-复制"按钮，`hasPermission` 控制；点击弹出目标批次选择对话框，确认后调 `copyFixtureToBatch`，成功 toast 新治具编码并跳转/刷新
  - **铁律落地**：相对路径 import；`ElMessageBox` 二段 try/catch；按钮权限控制；新编码由后端返回，前端只展示不拼接（§e.7）。

---

### 2.6 单元测试覆盖

#### Step 2-6-1：test_state_machine.py
- 涉及文件：`backend/tests/test_state_machine.py`（新建）、`backend/tests/conftest.py`（按需扩展 `make_fixture` 等 fixture）
- 前置条件：Step 2-2-1 完成（三函数 + `audit_service` 就绪）。**建议紧跟 2-2-1 执行，先验证状态机再在其上构建 CRUD。**
- 模板类型：**T07**
- 关键参数：
  - 用例矩阵参照架构 §3.3「单元测试覆盖矩阵（必做）」：合法流转（`PENDING_IQC→IQC_INSPECTING`）/ 非法流转抛 `StateMachineError` / 触发器不匹配抛 `StateMachineError` / `reject()` 合法回退 + history `trigger_type` 正确 / `reject()` 不支持的状态抛错 / `force_transition()` 空 reason 抛 `ValueError` / `force_transition()` 写 `audit_logs` 一条
  - **必含** `test_no_back_door_in_transition`：`inspect.signature(transition)` 断言 `'force'` 与 `'bypass'` 均不在参数中（§h / T07）
  - **铁律落地**：测试代码**不修改被测代码**（T07 职责边界——发现被测 bug 转 T06）；**禁止**引入 `factory_boy`/`faker`/`mimesis`（T07 MVP 极简依赖）；测试内查询用 `db.session.get()` / `select()`，**不用** `Model.query.get()`（§h）；conftest 用 connection-level transaction + nested savepoint 隔离用例（T07 文档约束 #3）。

#### Step 2-6-2：test_fixture_service.py
- 涉及文件：`backend/tests/test_fixture_service.py`（新建）、`backend/tests/conftest.py`（扩展 `seeded_fixture` / 各角色 `auth_headers` 等）
- 前置条件：Step 2-3-1 + Step 2-4-1 + Step 2-5-1 全部烟测通过
- 模板类型：**T07**
- 关键参数：
  - 用例矩阵：`create_fixture`（合法 → `fixture_code` 生成、套号正确 / 缺权限角色 403 / 缺必填字段 400）× `update_fixture`（version 正确 / 缺 version 400 / version 过期 409）× `change_status`（合法 trigger 成功 + history 多一行 / 非法 trigger 400 / 缺 version 409）× `force_status`（`super_admin` 成功 + `audit_logs` 多一行 / 非 `super_admin` 403）× `version_bump`（`A1→A2` / `A3→B1` / 超过 B3 边界由架构定 / 成功后 `fixture_status_history` 多一行 `trigger_type='version_bump'` 且 `from_status==to_status`）× `copy_to_batch`（`parent_fixture_id` 正确、套号递增、`current_version_code` 继承）× `seal_batch`（覆盖 Step 2-7-1，见下方 2.7 用例补充）× `list_fixtures`（默认分页 / 各过滤条件）
  - **2.7 用例补充**（覆盖 `seal_batch`）：合法封存（`manual_init` 批次 + 同项目存在 `mass_prod` 批次 status∈{in_progress, completed} + 角色 `super_admin`/`warehouse`）→ batch 内所有 fixtures 的 `is_sealed=True` + 各写一条 `FixtureStatusHistory(trigger_type='batch_seal')` / `batch_type != manual_init` 时拒绝 400 / 无 mass_prod 前置批次时拒绝 400 / 缺权限角色 403 / 乐观锁 batch.version 过期 409
  - **铁律落地**：`create_access_token` **必带** `additional_claims={'role_codes': [...]}`，否则 `@require_role` 静默返回 403、正向用例全挂且无明显报错（§h / T07 文档约束 #5）；JWT identity 传 `str`（§d Rule 4）；双层断言 `status_code` + 响应体 `code`；不改被测代码；不引入新测试库。

---

### 2.7 批量封存（Phase 2 部分）

#### Step 2-7-1：batch_service.seal_batch() + POST /api/fixtures/batch-seal
- 涉及文件：`backend/app/services/batch_service.py`（扩展，新增 `seal_batch()` 函数）、`backend/app/blueprints/fixtures.py`（扩展，追加 `POST /api/fixtures/batch-seal` 端点）
- 前置条件：Step 2-3-1 完成（`fixtures` Blueprint 已建，本步在其上追加端点）；Step 2-0-2（`fixtures.is_sealed/sealed_at/sealed_by` 字段就绪）+ Step 2-0-3（`fixture_status_history` 表就绪）+ Phase 1 `batch_service` 已建
- 模板类型：**T02**
- 关键参数：
  - 端点：`POST /api/fixtures/batch-seal`，请求体 `{batch_id: int, version: int}`，`@require_role('super_admin', 'warehouse')`（§3.3.x 业务规则，Step 2-0-1 权限矩阵）
  - 函数 `batch_service.seal_batch(batch_id, request_version, operator_id)` 业务规则（§3.3.x）：
    1. 加载 batch；乐观锁手动校验 `batch.version != request_version` 抛 `ConflictError`
    2. 校验 `batch.batch_type == 'manual_init'`，否则抛 `ValidationError`
    3. 校验同 `project_id` 下存在至少一个 `mass_prod` 批次且其 `status ∈ {in_progress, completed}`，否则抛 `ValidationError`
    4. 遍历 batch 下所有 fixtures：写 `is_sealed=True`、`sealed_at=db.func.now()`（**不用** `datetime.now()`，§h 风险点）、`sealed_by=operator_id`；**直接 INSERT** 一条 `FixtureStatusHistory(fixture_id, from_status=fixture.current_status, to_status=fixture.current_status, trigger_type='batch_seal', operator_id=operator_id)`——与 `version_bump` 同属"辅助事件直接写 history、不调 `transition()`"模式
    5. `batch.version += 1`；`db.session.commit()`；返回封存的 fixture 数量
  - **⚠️ 一项待 Frank 拍板的小决策（Step 2-0-1 已登记到 open_questions）**：§3.3.x 代码示例写 `to_status='sealed'` 但其文本又说"封存状态当前仅由 `fixtures.is_sealed` 字段反映"——CLI 执行前请 Frank 二选一：(a) `to_status=fixture.current_status`（保持不变，与本步 version_bump 模式对称，推荐）；(b) `to_status='sealed'`（严格照搬 §3.3.x 代码示例，需同步评估是否影响 `current_status` 字段）。本细化默认(a)。
  - 不在本步范围：`unseal`（解封需 PM + 生产主管双人会签审批流，Q-005，**留 Phase 4**，端点 `POST /api/fixtures/:id/release-seal` 在 2-3-1 已 501 占位）
  - **铁律落地**：核心表（`batches` / `fixtures`）无 DELETE，乐观锁手动校验 `version` 自增（§e.5）；`fixture.is_sealed=True` + history 写入在**同一事务**内完成（一次 `db.session.commit()`），任一 fixture 失败整体回滚；`seal_batch()` **不调 `transition()`**（§3.3.x 明确，封存为辅助事件）；时间字段统一 `db.func.now()`，**禁止** `datetime.now()`（§h）；端点路径 `/api/fixtures/batch-seal`（kebab-case、扁平化，§d Rule 6）；`POST` 加尾部斜杠（§h）；统一 `success_response` 返回封存 fixture 数；JWT identity 强转 `int`（§d Rule 4）。

---

### ✅ Frank 三项裁决登记（2026-05-15）

1. **`POST /api/fixtures/batch-seal` 批量封存** → ✅ **纳入 Phase 2**，已加 Step 2-7-1。`unseal` 审批流（PM + 生产主管双人会签）仍留 Phase 4。
2. **`fixtures.status` 独立字段** → ✅ **保留**。与 `current_status` 两个正交维度：`status` 走行政作废（active/cancelled），`current_status` 走 12 状态机；同 `projects`/`batches` 一致（§e.3/§e.12）。已落定为 Step 2-0-2 字段清单。
3. **`fixture_version_history` 独立表** → ❌ **不新建**。复用 `fixture_status_history`：`version_bump()` 直接 INSERT `trigger_type='version_bump'` + `from_status==to_status==current_status` + `reason` 记版本变化；与 `seal_batch` 同属"辅助事件直接写 history、不调 `transition()`"模式。已落定为 Step 2-4-1 关键参数。

### ⚠️ 仍留待后续阶段的边界项

- **`POST /api/fixtures/:id/recalc-dates`**：依赖 Phase 5 计划日期级联重算；Step 2-3-1 端点骨架以 `501 + TODO Phase 5` 占位。
- **`GET /api/fixtures/export`**：依赖 Phase 6 导出三档体系；Step 2-3-1 端点骨架以 `501 + TODO Phase 6` 占位。
- **`POST /api/fixtures/:id/release-seal`**：依赖 Phase 4 审批流引擎（PM + 生产主管会签，Q-005）；Step 2-3-1 端点骨架以 `501 + TODO Phase 4` 占位。
- **`seal_batch` 中 `to_status` 取值**（Step 2-7-1 关键参数最后一项的小决策）：§3.3.x 文本与代码示例存在轻微张力，CLI 执行 2-7-1 前请 Frank 拍板二选一。

---

**建议执行顺序**：2-0-1 → 2-0-2 → 2-0-3 → 2-0-4 → 2-1-1 → 2-2-1 → 2-6-1 → 2-3-1 → 2-7-1 → 2-3-2 → 2-3-3 → 2-4-1 → 2-4-2 → 2-5-1 → 2-5-2 → 2-6-2

### Phase 2 模板使用统计

| 模板 | 使用次数 | 使用 Step |
|------|---------|-----------|
| 手写提示词 | 1 | 2-0-1 |
| T01 | 3 | 2-0-2 / 2-0-3 / 2-0-4 |
| T02 | 5 | 2-1-1 / 2-3-1 / 2-4-1 / 2-5-1 / 2-7-1 |
| T03 | 1 | 2-3-2 |
| T04 | 3 | 2-3-3 / 2-4-2 / 2-5-2 |
| T05 | 1 | 2-2-1 |
| T06 | 0 | （Bug 修复，按需触发） |
| T07 | 2 | 2-6-1 / 2-6-2 |
