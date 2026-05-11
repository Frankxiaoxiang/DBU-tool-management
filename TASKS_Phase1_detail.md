## Phase 1 — 项目与批次模块（已细化）

> **细化原则**：每个 Step 在一次 CLI session 内可独立完成；前置依赖严格顺序；不越界至 Phase 2+（治具表、状态机、审批流、邮件告警均不在本阶段实现，仅接口规约与字段预留）。
>
> **共 5 个子模块、19 个 Step**，建议工期 1.5–2 周。**任何状态机/审批流相关接入需求出现时**，必须标记 TODO 留到对应 Phase，**禁止**在 Phase 1 内"顺手实现"。

### 1.0 准备：API spec & 权限矩阵补全

#### Step 1-0-1：补全 Phase 1 端点的 spec 与权限标注
- 涉及文件：`Doc/04_api_spec.md`、`Doc/05_permissions.md`、`Doc/03_architecture_v1.4.md`（仅 2.3 节字段定稿）
- 前置条件:Phase 0 已完成（包括 0.7 团队 review）
- 模板类型：**无对应模板，需手写提示词**（这是 CLAUDE.md §g「API 先写 spec 再实现」的强制前置动作，不写代码）
- 关键参数：
  - 补完项目模块 9 个端点的请求体 / 响应体 / 错误码（参见 04_api_spec.md §1.1）
  - 补完批次模块 6 个端点的请求体 / 响应体（参见 §1.2），含批次类型枚举 `manual_init / mass_prod / addon_quantity / addon_optimize`
  - 补充 `POST /api/projects/:id/sync-templates`（追加快照）与 `PATCH /api/batches/:id/seal` / `PATCH /api/batches/:id/unseal` 的草案条目（实现可分期，但 spec 先到位）
  - 在 `05_permissions.md` 中为每个端点标注 `@require_role` 范围：项目新建/编辑/作废=`super_admin + pm`；批次新建/编辑=`super_admin + pm`；同步模板/转移负责人=`super_admin`；封存 seal=`super_admin + warehouse`；解封 unseal Phase 1 暂仅 `super_admin`（PM+生产主管会签接入留 Phase 4）
  - 输出物：spec & 权限两份文档的 diff + CLAUDE.md §j 修订记录追加一行

---

### 1.1 项目模块

#### Step 1-1-1：Project Model + Migration
- 涉及文件：`backend/app/models/project.py`、`backend/app/models/__init__.py`、`backend/migrations/versions/<新>.py`
- 前置条件：Step 1-0-1 完成（spec 已定稿）
- 模板类型：**T01**
- 关键参数：
  - 表名 `projects`、类名 `Project`、文件名 `project`、table_kind=`core`
  - 字段清单（严格对齐架构 §2.3）：`id BIGINT PK`、`project_code VARCHAR(32) UNIQUE NOT NULL`、`project_name VARCHAR(128) NOT NULL`、`product_type VARCHAR(16) NOT NULL`（SUS_VC/CU_VC/HP）、`project_owner_id BIGINT NOT NULL FK users.id`、`status VARCHAR(16) NOT NULL DEFAULT 'active'`（active/closed/cancelled）、`cancelled_reason TEXT NULL`、`cancelled_at DATETIME NULL`、`cancelled_by BIGINT NULL FK users.id`、`created_by BIGINT NOT NULL FK users.id`、`created_at / updated_at`、`version INT NOT NULL DEFAULT 0`
  - 索引：`idx_owner(project_owner_id)`、`idx_product_type`、`idx_status`
  - 铁律提醒：`__table_args__` 含 `utf8mb4`；**严禁** `__mapper_args__ = {'version_id_col': version}`（CLAUDE.md §e.5）；`project_code` 由后端生成不允许前端拼接（§e.7）
  - 架构文档章节号填 `2.3 项目与批次模型`

#### Step 1-1-2：project_service + Blueprint API
- 涉及文件：`backend/app/services/project_service.py`（新建）、`backend/app/blueprints/projects.py`（新建）、`backend/app/__init__.py`（注册）、`backend/app/services/code_generator.py`（仅新增 `generate_project_code()` 一个函数，治具编码生成器留 Phase 2）
- 前置条件：Step 1-1-1 已 `flask db upgrade` 通过
- 模板类型：**T02**
- 关键参数：
  - 资源路径 `projects`、端点清单：`GET /` / `POST /` / `GET /:id` / `PUT /:id` / `PATCH /:id/cancel` / `PUT /:id/owner` / `POST /:id/sync-templates`（**仅占位返回 501**，实现留到 Step 1-2-2）/ `GET /:id/gantt` 与 `GET /export` **不在本 Step 范围**（前者依赖 fixtures→Phase 2，后者依赖导出体系→对齐 07_export_guideline 第一档，留到 Phase 6 系统管理段）
  - 权限矩阵：见 Step 1-0-1
  - 必须落地的铁律：乐观锁手动校验 `record.version != body['version']` 抛 `ConflictError`、`PUT/PATCH` 用 `'key' in body` 判断、PATCH `/cancel` 必填 `reason` 写入 `cancelled_at/by`、core 表**禁止 DELETE 路由**（§d Rule 2 / §e.12）
  - `project_code` 生成规则：3–4 位大写字母（取 `project_name` 首字母简码或人工输入），冲突时追加序号；本期 Frank 决定:**首版允许人工输入项目代号**（避免自动生成与编码规则文档对齐复杂度），Service 仅做唯一性与正则 `^[A-Z]{2,6}$` 校验

#### Step 1-1-3：project_service 单元测试
- 涉及文件：`backend/tests/test_project_service.py`、`backend/tests/conftest.py`（按需扩展 fixture）
- 前置条件：Step 1-1-2 烟测通过（curl 五端点全 200/201）
- 模板类型：**T07**
- 关键参数：
  - 用例矩阵：`create_project`(role=pm 合法 / role=iqc 403 / 缺 project_name 400 / project_code 冲突 400) × `update_project`(version 正确 / version 缺失 400 / version 过期 409) × `cancel_project`(active → cancelled / 已 cancelled 二次 cancel 期望幂等或 400 由架构定) × `list_projects`(默认 / product_type 过滤 / status 过滤 / keyword 模糊)
  - conftest 必须新增：`seeded_pm_user` / `seeded_iqc_user` / `seeded_project(active)` / `auth_headers_pm` / `auth_headers_iqc` / `auth_headers_super_admin`
  - 严禁引入 `factory_boy` / `faker`（T07 §文档约束第 4 条 MVP 极简依赖）

#### Step 1-1-4：ProjectList 前端列表页
- 涉及文件：`frontend/src/views/project/ProjectList.vue`（新建）、`frontend/src/api/project.js`（新建）、`frontend/src/router/index.js`（追加路由）、`frontend/src/utils/status.js`（追加 project 状态映射表，新建或扩展，是 Phase 2 状态机 status.js 的前身）
- 前置条件：Step 1-1-2 完成
- 模板类型：**T03**
- 关键参数：
  - 列：项目编号 / 项目名称（可点详情）/ 产品线 / 负责人姓名 / 状态（el-tag 走 status.js）/ 创建时间（走 `formatBackendTime`）
  - 搜索：`product_type` 下拉 / `status` 下拉(默认 active) / `owner_id` 下拉 / `keyword` 模糊
  - 操作按钮：查看详情 / 编辑（hasPermission `project.edit`）/ 作废（hasPermission `project.cancel`，弹 ElMessageBox 输 reason 后 PATCH `/cancel`）
  - 铁律落地：**严禁** `from '@/'`（用相对路径）、**严禁**裸 `dayjs(str)` / `new Date(str)`、`el-tag :type` 兜底为 `'info'` 而非 `''`、`ElMessageBox.confirm` 二段 try/catch

#### Step 1-1-5：ProjectForm 前端表单页（create / edit / detail 三合一）
- 涉及文件：`frontend/src/views/project/ProjectForm.vue`（新建）、`frontend/src/api/project.js`（追加 `getProjectById / createProject / updateProject / transferOwner`）、`frontend/src/router/index.js`（追加 `/projects/new`、`/projects/:id`、`/projects/:id/edit` 三条路由）
- 前置条件：Step 1-1-4 完成
- 模板类型：**T04**
- 关键参数：
  - 模式 = `三合一`，通过 `route.meta.mode` 区分 create/edit/detail
  - 字段表：`project_code`（create 隐藏，edit/detail 只读，**严禁前端拼接**）/ `project_name`（必填，maxLength=128）/ `product_type`（必填，三选一）/ `project_owner_id`（create/edit 可改，edit 模式提示走 `/owner` 转移接口的可选路径）/ `status`（仅 detail 只读显示）/ `version` hidden（edit 提交必带）
  - 提交契约：create → `POST /api/projects`；edit → `PUT /api/projects/:id` body 含 `version`；detail → 只读，操作按钮区放"作废"和"追加同步模板"（Step 1-2-4 实现）入口

---

### 1.2 模板快照机制

> 该子模块必须早于批次模块完成对外可见的"项目创建即生成快照"，因为后续创建治具（Phase 2）要外键引用 `fixture_template_snapshots.id`。

#### Step 1-2-1：FixtureTemplateSnapshot Model + Migration
- 涉及文件：`backend/app/models/fixture_template_snapshot.py`（新建）、`backend/app/models/__init__.py`、`backend/migrations/versions/<新>.py`
- 前置条件：Step 1-1-1 完成（项目表先建好以建外键）
- 模板类型：**T01**
- 关键参数：
  - 表名 `fixture_template_snapshots`、类名 `FixtureTemplateSnapshot`、table_kind=`business_record`
  - 字段：`id BIGINT PK`、`project_id BIGINT NOT NULL FK projects.id`、`source_template_id BIGINT NOT NULL FK fixture_templates.id`（保留溯源）、`fixture_type_code VARCHAR(32) NOT NULL`、`product_type VARCHAR(16) NOT NULL`、`default_lt_days INT NULL`、`default_iqc_interval_days INT NULL`、`default_install_interval_days INT NULL`、`default_acceptance_interval_days INT NULL`、`default_handover_interval_days INT NULL`、`default_maintenance_threshold INT NULL`（V1.4 §2.4「历史快照字段兼容策略」要求新增字段可空）、`synced_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP`、`synced_by BIGINT NOT NULL FK users.id`
  - 唯一约束：`UNIQUE KEY uk_project_type(project_id, fixture_type_code)`（同一项目同类型只能有一份快照）
  - 索引：`idx_project`、`idx_source_template`
  - 铁律：utf8mb4、**禁止** `version_id_col`、本表无 `version` 字段（快照不可编辑，只增不改不删，详见 CLAUDE.md §e.8）

#### Step 1-2-2：snapshot_service + 集成至 project_service.create_project + 实现 `/sync-templates` 端点
- 涉及文件：`backend/app/services/snapshot_service.py`（新建）、`backend/app/services/project_service.py`（修改 `create_project` 增加事务内调用 `lock_snapshot()`）、`backend/app/blueprints/projects.py`（把 Step 1-1-2 的 501 占位换为真实实现）
- 前置条件：Step 1-2-1 + Step 1-1-2 完成
- 模板类型：**T02**
- 关键参数：
  - `lock_snapshot(project_id, operator_id)`：项目创建瞬间锁定，把 `fixture_templates` 中所有 `product_type` 与项目匹配且 `is_active=True` 的模板**整行复制**到 `fixture_template_snapshots`，**同一事务**与 project 创建一起 commit；失败回滚
  - `sync_missing_templates(project_id, operator_id)`：仅追加新增模板，**严禁覆盖已有**（CLAUDE.md §e.8 红线）；执行后写审计日志 `audit_logs` 一行（action='sync_templates'，operator_id，project_id，added 数量）
  - 端点权限：`POST /api/projects/:id/sync-templates` → `super_admin + pm`；返回 `{ added_count, added_codes[] }`
  - 强制单元事务原子性：`create_project` 必须 `db.session.begin_nested()` 包裹 project 写入 + 快照批量写入，任一失败回滚全部

#### Step 1-2-3：snapshot_service 单元测试
- 涉及文件：`backend/tests/test_snapshot_service.py`、`backend/tests/conftest.py`（追加 `seeded_templates(product_type='SUS_VC', count=5)` fixture）
- 前置条件：Step 1-2-2 烟测通过
- 模板类型：**T07**
- 关键参数：
  - 用例矩阵：`lock_snapshot`(project_type=SUS_VC → 应锁定 5 条 / 模板 is_active=False 不锁) × `sync_missing_templates`(模板库新增 2 条 → 项目快照追加 2 条 / 已存在的不重复 / 已存在但模板 is_active=False 时不补) × `sync_missing_templates_after_create`(project 创建后立即 sync → added_count=0)
  - 必须断言审计日志已写入

#### Step 1-2-4：ProjectForm/Detail 中"追加同步模板"按钮
- 涉及文件：`frontend/src/views/project/ProjectForm.vue`（扩展 detail 模式按钮区）、`frontend/src/api/project.js`（追加 `syncProjectTemplates(id)`）
- 前置条件：Step 1-1-5 + Step 1-2-2 完成
- 模板类型：**T04**（扩展模式，仅在 detail 模式按钮区追加一个按钮 + 调用 + 结果 toast，复用 T04 现有结构无需新建组件）
- 关键参数：
  - 按钮文案"追加同步模板库"，仅 `super_admin / pm` 可见（走 `hasPermission('project.sync_templates')`）
  - 二段 try/catch ElMessageBox.confirm "确认要把模板库中本项目产品线下新增的模板追加到本项目快照吗？已有快照不会被覆盖。"
  - 成功后 `ElMessage.success('已追加 X 条模板')`，X 取自后端 `added_count`

---

### 1.3 批次模块（含批次类型业务规则与状态流转）

#### Step 1-3-1：Batch Model + Migration
- 涉及文件：`backend/app/models/batch.py`（新建）、`backend/app/models/__init__.py`、`backend/migrations/versions/<新>.py`
- 前置条件：Step 1-1-1 完成（projects 表已存在以建外键）
- 模板类型：**T01**
- 关键参数：
  - 表名 `batches`、类名 `Batch`、table_kind=`core`
  - 字段（严格对齐架构 §2.3）：`id`、`project_id BIGINT NOT NULL FK projects.id`、`batch_no VARCHAR(20) NOT NULL`、`batch_type VARCHAR(20) NOT NULL`（manual_init/mass_prod/addon_quantity/addon_optimize）、`parent_batch_id BIGINT NULL FK batches.id`（仅加开类型有值）、`flow_path VARCHAR(16) NOT NULL DEFAULT 'full'`（full/simplified，仅加开类型可填 simplified）、`status VARCHAR(16) NOT NULL DEFAULT 'draft'`（draft/confirmed/in_progress/completed/closed/cancelled）、`expected_date DATE NULL`、`remark TEXT NULL`、`cancelled_reason TEXT NULL`、`cancelled_at DATETIME NULL`、`cancelled_by BIGINT NULL FK users.id`、`created_by`、`created_at / updated_at`、`version INT NOT NULL DEFAULT 0`
  - 唯一约束：`UNIQUE KEY uk_project_batch(project_id, batch_no)`
  - 索引：`idx_parent(parent_batch_id)`、`idx_status`
  - 铁律提醒同 1-1-1

#### Step 1-3-2：batch_service + Blueprint（CRUD + 批次类型业务规则）
- 涉及文件：`backend/app/services/batch_service.py`（新建）、`backend/app/blueprints/batches.py`（新建）、`backend/app/__init__.py`（注册 batch_bp）
- 前置条件：Step 1-3-1 + Step 1-2-2 完成（创建批次时验证项目快照已锁定）
- 模板类型：**T02**
- 关键参数：
  - 端点：`POST /` / `GET /:id` / `PUT /:id` / `PATCH /:id/cancel` / `GET /:id/fixtures`（Phase 1 阶段返回空数组占位，标注 TODO: depends on fixtures→Phase 2）/ `GET /:id/gantt`（同样 501 占位留到 Phase 5 甘特图）
  - 权限：见 Step 1-0-1
  - **批次类型业务规则**（核心，下方逐条必须在 `create_batch` Service 里落实并写单元测试）：
    1. `manual_init`：同一 `project_id` 下**至多一个** `manual_init` 批次（DB 校验或 Service 预检）；`parent_batch_id` 必须为 NULL；`flow_path` 强制 `full`
    2. `mass_prod`：同一项目下至多一个 `mass_prod`（业务规则）；`parent_batch_id` 必须为 NULL；`flow_path` 强制 `full`；创建时在响应中标记 `urgency_flag=true`（邮件告警接入留到 Phase 6，此处仅返回字段）
    3. `addon_quantity` / `addon_optimize`：`parent_batch_id` 必填且必须存在于同 `project_id` 下；`flow_path` 用户可选 `full` 或 `simplified`
    4. 业务规则 4：`batch_no` 自动生成规则 = `{project_code}-{batch_type_short}-{seq}`，其中 batch_type_short = `M0` / `MP` / `AQ` / `AO`；seq 在同类型内递增
  - 铁律落地：乐观锁、`'key' in body`、PATCH cancel 必填 reason；**不写**任何状态机三函数（Phase 2 才有 `services/state_machine.py`）；Service 内**严禁**出现 `batch.status = 'in_progress'` 这类直赋值（即便没有 state_machine 也要走 `batch_service._safe_transition()` 内部封装一个**纯批次级**的状态变更函数，并在注释里标注"Phase 4 审批流接入后此函数将与全局状态机集成"）

#### Step 1-3-3：batch_service 单元测试
- 涉及文件：`backend/tests/test_batch_service.py`、`backend/tests/conftest.py`（追加 `seeded_project_with_snapshot`、`seeded_manual_batch` fixture）
- 前置条件：Step 1-3-2 烟测通过
- 模板类型：**T07**
- 关键参数：
  - 用例矩阵：4 种批次类型各覆盖"合法创建 / 业务规则违反"成对；`update_batch`(version 三态)；`cancel_batch`；`list_batches_under_project`（按 `project_id` 过滤）
  - 必有用例 `test_second_manual_init_in_same_project_400`、`test_addon_without_parent_batch_400`、`test_addon_parent_in_different_project_400`、`test_simplified_flow_path_only_for_addon_400`

#### Step 1-3-4：BatchList 前端列表页
- 涉及文件：`frontend/src/views/batch/BatchList.vue`（新建）、`frontend/src/api/batch.js`（新建）、`frontend/src/router/index.js`（追加路由 `/projects/:projectId/batches` 嵌套或独立 `/batches?project_id=`）、`frontend/src/utils/status.js`（追加 batch 状态映射）
- 前置条件：Step 1-3-2 完成
- 模板类型：**T03**
- 关键参数：
  - 列：批次号 / 批次类型（el-tag 区分四种颜色）/ 父批次（加开类型才显示）/ 流程路径（full/simplified）/ 状态（el-tag）/ 期望日期 / 创建时间
  - 搜索：`batch_type` 下拉 / `status` 下拉 / `project_id`（路由带入则隐藏，独立访问则下拉）/ `keyword`
  - 操作：查看详情 / 编辑 / 作废（pm/super_admin 可见）

#### Step 1-3-5：BatchForm 前端表单页（create / edit / detail 三合一）
- 涉及文件：`frontend/src/views/batch/BatchForm.vue`、`frontend/src/api/batch.js`（追加 get/create/update）、`frontend/src/router/index.js`（追加三路由）
- 前置条件：Step 1-3-4 完成
- 模板类型：**T04**
- 关键参数：
  - 字段表：`batch_no`（create 隐藏由后端生成，edit/detail 只读）/ `project_id`（create 必选，可由路由预填）/ `batch_type`（create 必选，edit/detail 只读不可改类型）/ `parent_batch_id`（仅 addon 两种类型显示，下拉源为同项目下所有非 cancelled 批次）/ `flow_path`（仅 addon 显示，默认 full）/ `expected_date` / `remark` / `version` hidden
  - **前端联动校验**：选 `batch_type=addon_quantity` 或 `addon_optimize` 时 `parent_batch_id` 必填；其他类型该字段强制清空；`flow_path` 下拉仅 addon 启用
  - 必须落地：**严禁前端拼接 batch_no**（V1.4 §e.7 同样适用于批次号生成）

---

### 1.4 手动版封存 / 解封（API 规约 + 业务规则文档化）

> **范围声明**：流程文档 4.1.4 节定义的"封存"对象是**治具**（fixtures.is_sealed），不是批次。fixtures 表在 Phase 2 才建。因此 Phase 1 本子模块**仅完成接口规约 + 业务规则文档化 + 批次级别的"是否含已封存治具"汇总视图占位**，**不实现** fixtures 批量写入；同时**解封会签**依赖审批流（Phase 4）。
>
> 若 Frank 评估认为应该在 Phase 1 内完成 fixture 表与批量封存，需要先把 Phase 2 的"治具 Model + Migration"前置完成；否则下面 Step 1-4-x 是当前 Phase 范围内合理的最小落地。

#### Step 1-4-1：封存 / 解封 API spec 与业务规则文档化
- 涉及文件：`Doc/04_api_spec.md`（§1.2 末尾追加）、`Doc/05_permissions.md`（§2 末尾追加）、`Doc/03_architecture_v1.4.md`（§3.3 状态机预留章节追加"手动版封存联动设计"小节，标注实现里程碑 Phase 2/4）、`Doc/00_open_questions.md`（追加待确认条目)
- 前置条件：Step 1-3-2 完成
- 模板类型：**无对应模板，需手写提示词**
- 关键参数：
  - 端点草案：`PATCH /api/batches/:id/seal` body=`{ version, operator_role_confirm }`、`PATCH /api/batches/:id/unseal` body=`{ version, reason, approval_id? }`
  - 业务规则文档化：① 仅 `batch_type=manual_init` 可触发 seal；② seal 触发条件 = 同项目下 `mass_prod` 批次状态 ∈ {in_progress, completed}（前置校验）；③ seal 执行 = 标记该批次内所有 fixtures `is_sealed=TRUE`+ sealed_at + 写 fixture_status_history（**Phase 2 实现**）；④ unseal 走审批流（PM+生产主管会签，**Phase 4 实现**）
  - 在 `00_open_questions.md` 加 3 条：① "封存"是否需要在 batches 表上加汇总字段 `sealed_fixture_count` 以避免每次查询 join fixtures？② manual_init 批次封存后，状态机要不要从 `closed` 衍生 `sealed` 状态？还是仅由 fixtures.is_sealed 反映？③ 解封会签是否复用 §3.4 的 sequential/parallel 引擎？

#### Step 1-4-2（可选，Frank 决策后再执行）：batch_service.seal/unseal 接口骨架
- 涉及文件：`backend/app/services/batch_service.py`（追加两个函数）、`backend/app/blueprints/batches.py`（追加两个路由）、`backend/tests/test_batch_service.py`（追加权限/参数校验用例）
- 前置条件：Step 1-4-1 完成且 Frank 明确同意"在 Phase 1 内做接口骨架"
- 模板类型：**T02**
- 关键参数：
  - `seal_batch(batch_id, operator_id, version)`：① 校验 batch_type=manual_init；② 校验同项目下存在 mass_prod 且状态 in_progress/completed；③ **不写 fixtures**（标注 `# TODO(Phase 2): batch-update fixtures.is_sealed=True`）；④ 写审计日志；⑤ 返回 200 + `{ pending_fixture_seal: true }`
  - `unseal_batch(batch_id, operator_id, reason, version)`：Phase 1 阶段仅 `super_admin` 直接通过（无审批），写审计日志，标注 `# TODO(Phase 4): integrate dual-approval flow (PM + production supervisor)`
  - 单元测试矩阵：合法 seal、非 manual_init 类型 seal 拒绝 400、缺少 mass_prod 前置 seal 拒绝 400、权限拒绝 403、version 过期 409

---

### 1.5 Phase 1 收尾

#### Step 1-5-1：项目—批次链路联调与冒烟测试
- 涉及文件：无新代码；`Doc/00_open_questions.md`（记录联调发现的问题）
- 前置条件：1.1 ~ 1.4 所有 Step 完成且单元测试全绿
- 模板类型：**无对应模板，需手写提示词**
- 关键参数（5 条端到端冒烟脚本，逐条 curl + 前端点击双通道验证）：
  1. PM 登录 → 创建 SUS_VC 项目 → 验证 `fixture_template_snapshots` 表里被锁定 N 条（N=种子数据 SUS_VC 模板数）
  2. 同一项目下创建 `manual_init` 批次 → 再次尝试创建第二个 `manual_init` → 期望 400
  3. 创建 `addon_quantity` 批次但不传 `parent_batch_id` → 期望 400；正确传入后创建成功
  4. 修改 manual_init 批次（PUT），第二次提交时故意带过期 `version` → 期望 409 弹窗刷新
  5. 模板库新增一条 SUS_VC 模板（直接 DB 插或调超管 API）→ 项目详情页点"追加同步模板"→ 期望 toast 提示 added=1
- 验收输出：联调报告（含失败项 + 修复记录）+ 修订 Phase 1 已勾选项

#### Step 1-5-2：TASKS.md / CLAUDE.md 进度同步
- 涉及文件：`TASKS.md`（Phase 1 全部子项打勾 + 修订记录追加）、`CLAUDE.md`（§j 修订记录追加）、`Doc/03_architecture_v1.4.md`（如有字段定稿差异）
- 前置条件：Step 1-5-1 通过
- 模板类型：**无对应模板，需手写提示词**
- 关键参数：
  - 将 Phase 1 的 6 个原顶层勾选项替换为本细化版的 19 个 Step 勾选记录
  - 修订记录追加格式：`| 2026-XX-XX | Phase 1 全部完成：项目模块 / 模板快照 / 批次模块 / 封存解封规约 + 端到端联调通过 | Claude |`
  - **切换标记**：`## 当前阶段` 在 CLAUDE.md §c 改为 `Phase 2 — 模治具核心模块`

---

### Phase 1 模板使用统计

| 模板 | 使用次数 | 使用 Step |
|------|---------|-----------|
| T01  | 3 | 1-1-1 / 1-2-1 / 1-3-1 |
| T02  | 4 | 1-1-2 / 1-2-2 / 1-3-2 /（可选）1-4-2 |
| T03  | 2 | 1-1-4 / 1-3-4 |
| T04  | 3 | 1-1-5 / 1-2-4(扩展) / 1-3-5 |
| T07  | 3 | 1-1-3 / 1-2-3 / 1-3-3 |
| **无对应模板** | 4 | 1-0-1 / 1-4-1 / 1-5-1 / 1-5-2 |

> **建议执行顺序**：1-0-1 → 1-1-1 → 1-1-2 → 1-1-3 → 1-2-1 → 1-2-2 → 1-2-3 → 1-1-4 → 1-1-5 → 1-2-4 → 1-3-1 → 1-3-2 → 1-3-3 → 1-3-4 → 1-3-5 → 1-4-1 →（决策点）→ 1-4-2 → 1-5-1 → 1-5-2

---

## 落实建议（贴回 TASKS.md 之外的 3 个动作）

1. **PROMPT_TEMPLATES.md 增补**：在 T03 / T04 的"使用示例"小节，把当前贴的"项目"案例拓展成完整可粘贴的提示词（已在文档中有骨架，但 1-2-4「扩展模式」目前无样例），可在 Phase 1 推进过程中迭代补入。
2. **00_open_questions.md 优先级**：Step 1-4-1 提的 3 个开放问题，建议在批次模块开工前（即 Step 1-3-2 启动前）跟业务方对齐第②条（封存状态归属层级），避免做完再返工。
3. **Phase 2 前置预热**：Phase 1 跑完 Step 1-2-2 后，可以同步起一份 Phase 2 的细化提案（治具 Model + 编码生成器 + 状态机三函数），但**严禁**在 Phase 1 内提前写代码。
