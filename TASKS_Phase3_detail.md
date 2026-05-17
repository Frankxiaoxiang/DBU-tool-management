## Phase 3 — 流程节点模块（已细化）

> **细化原则**：每个 Step 在一次 CLI session 内可独立完成并验收；前置依赖严格顺序；**严禁越界至 Phase 4+**（审批流引擎、月度报表、甘特图、成本展示权限、计划日期级联重算均不在本阶段；如出现接口依赖，用 `501` 占位并注明 `TODO Phase X`）。
>
> **共 12 个子模块、28 个 Step。**
>
> **三条关键边界（来自架构铁律 + 文档对照，CLI 必须遵守）**：
> 1. **Phase 3 不修改状态机**。§3.3 `TRANSITIONS` / `REJECT_CONFIG` 已涵盖全部 12 状态流转触发器，本阶段所有流程节点用到的 trigger（`normal`/`iqc_pass`/`acceptance_pass`/`checkout`/`return`/`maintenance_due`/`repair_request` 等）均已存在。**本阶段无 T05 步骤**。
> 2. **单据与状态变更解耦**（api_spec §3）：`*-records` 端点**仅落库业务单据**，状态流转由前端在单据 POST 成功后**另发** `PATCH /api/fixtures/:id/status`（Phase 2 已实现）。各 T02 步骤**不调 `transition()`、不改 `current_status`**。
> 3. **审批-gated 流转留 Phase 4**：`emergency_auth`（紧急上机授权）/ `concession_approved`（让步接受）/ `return_repair`（退厂返修）/ `rework`（试产返工）/ `acceptance_fail_scrap`（试产报废）/ `scrap`（报废会签）这 6 条流转受审批流门控（CLAUDE.md §e.6）。Phase 3 **只建对应业务单据表与录入端点**，审批流引擎与审批-gated 流转一律 `501 + TODO Phase 4`。
>
> **细化依据**：架构 §2.4–2.8、§3.4、§3.5 在 V1.4 文档中均标注"同 V1.3"，业务单据表的字段清单本文件依据《全流程管控文件 V2.1》§4 各阶段表 + api_spec §3/§5 推导。**所有 T01 步骤的字段清单为推导版，CLI 执行 T01 Step 1「字段对齐」时必须与 V1.3 架构文档对应章节 + 《全流程管控文件 V2.1》§4 逐字段核对**，差异列出等 Frank 确认。

---

### 3.0 准备：API spec、权限矩阵与文件上传基础设施

#### Step 3-0-1：API spec §3/§5/§6 补全 + 模治具流程节点权限矩阵补全
- 涉及文件：`Doc/04_api_spec.md`（§3 业务单据、§5 采购、§6 附件——三节当前均极简，需补完请求体/响应体/错误码）、`Doc/05_permissions.md`（新增流程节点端点 `@require_role` 映射段）、`Doc/00_open_questions.md`（登记本阶段开放问题）
- 前置条件：Phase 2 已全部关闭（治具 CRUD / 状态机 / 编码生成器就绪）。CLAUDE.md §g「API 先写 spec 再实现」的强制前置动作，参照 Phase 1 Step 1-0-1 / Phase 2 Step 2-0-1。
- 模板类型：**手写提示词（无对应模板）**
- 关键参数：
  - 补完 `04_api_spec.md` §3 六类业务单据（`iqc-reports`/`acceptance-reports`/`install-records`/`maintenance-records`/`repair-records`/`scrap-records`）+ 补充本阶段新增单据（`drawings`/`purchase-requisitions`/`goods-receipts`/`emergency-auth-records`/`handover-records`/`checkout-records`）的请求体/响应体；§5 采购订单 PO 头+items 的请求体/响应体
  - `05_permissions.md` 新增流程节点端点权限映射：图纸/采购申请单 = `design_engineer`（+ PM 确认）；PO = `purchaser`；到货签收/移交 = `warehouse`；IQC 报告 = `iqc`；紧急上机授权单 = `pm + iqc`；安装记录 = `me`；验收报告 = `iqc`（质量工程师）；领用归还 = `production_lead`；保养/维修执行 = `me`；报废申请 = `pm`
  - 在 `00_open_questions.md` 登记开放问题（编号接续现有序列）：① 移交确认与状态机的关系——§3.3 `TRANSITIONS` 无"移交"流转，`acceptance_pass` 已直接 `ACCEPTANCE_TESTING→IN_STOCK`；移交确认是否仅作业务单据（不改状态），还是需"验收合格-待移交"中间态；② 单据 POST 与状态流转是否维持解耦（api_spec §3）还是单据 POST 内联流转（原子性更强但与 §e.4「状态变更唯一入口」张力）；③ 计划日期推算归属——flow §4.3 称采购下单时自动推算各节点计划日期，但 TASKS.md 将「计划日期推算与级联重算」列在 Phase 5，Phase 3 PO 步骤是否仅存采购下单日；④ 货架/库位与使用次数是否需作为 `fixtures` 表的活属性字段（领用/保养会用到），还是仅存于业务单据
  - 输出物：三份文档 diff + `CLAUDE.md` §j / `TASKS.md` 修订记录各追加一行
  - **铁律落地**：文档先行（§g Schema-First / API 先写 spec）；**不把权限来源复制进本细化文件**，避免双来源漂移；本步零代码。

#### Step 3-0-2：文件上传基础设施
- 涉及文件：`backend/app/utils/upload.py`（新建）、`backend/app/blueprints/files.py`（新建）、`backend/app/__init__.py`（注册 Blueprint）、`.env.development` / `.env.production` / `.env.example`（确认 `UPLOAD_BASE` 变量）
- 前置条件：Step 3-0-1 完成。本步是 §3.5 文件上传 + 决策 #13 的基础设施，**所有含附件的流程节点单据（图纸/DFM/IQC 照片/安装照片/验收照片/移交照片/故障照片等）都依赖本步**，必须早于 3-1-1 之后的所有带文件字段的 Step。
- 模板类型：**手写提示词（无对应模板，infra util + 轻量 Blueprint）**
- 关键参数：
  - `utils/upload.py`：`save_upload(file_storage, subdir)` → 用 `pathlib.Path` 将文件存入 `UPLOAD_BASE/subdir/`，返回**相对路径**（始终正斜杠 `/`，§e.2）；校验扩展名白名单与单文件大小
  - `blueprints/files.py`：`GET /api/files/<path:relpath>`，`@jwt_required()`，用 `send_from_directory(UPLOAD_BASE, relpath)` 鉴权下载（决策 #13）
  - `UPLOAD_BASE` 由 `.env.*` 提供（开发机本地目录 / 生产机 `D:\dbu\uploads`）
  - **铁律落地**：文件路径一律 `pathlib.Path` 跨平台处理，数据库存**相对路径 + 正斜杠**（§e.2）；下载必须 `@jwt_required()` + `send_from_directory`，**严禁**直接拼接路径暴露文件系统；Waitress `max_request_body_size=536870912`（500MB 物理底线）Phase 0 已配，本步不重配但注明；Blueprint 不带 `url_prefix`，注册时加 `/api/files`。

---

### 3.1 设计阶段：图纸/DFM 上传、采购申请单（功能点 1）

#### Step 3-1-1：Drawing + PurchaseRequisition Models + Migration
- 涉及文件：`backend/app/models/drawing.py`（新建）、`backend/app/models/purchase_requisition.py`（新建）、`backend/app/models/__init__.py`、`backend/migrations/versions/<新>.py`
- 前置条件：Step 3-0-1 完成（spec & 权限定稿）。本步建两张紧耦合的设计阶段业务单据表。
- 模板类型：**T01**
- 关键参数：
  - 表 1：`drawings` / 类 `Drawing` / table_kind=`business_record`。⚠️ 字段清单为推导版（核对 V1.3 + flow §4.2）：`id BIGINT PK`、`fixture_id BIGINT NOT NULL FK fixtures.id`、`version_code VARCHAR(8) NOT NULL`（对应图纸版本 A1/A2/…）、`drawing_file_path VARCHAR(512) NOT NULL`、`dfm_report_path VARCHAR(512) NULL`（DFM 选填附件）、`acceptance_standard TEXT NULL`（关键尺寸/验收标准）、`bom_info TEXT NULL`、`is_copied BOOLEAN NOT NULL DEFAULT FALSE`（是否复制既有图纸-简化流程）、`source_drawing_id BIGINT NULL FK drawings.id`、`uploaded_by BIGINT NOT NULL FK users.id`、`confirmed_by BIGINT NULL FK users.id`、`confirmed_at DATETIME NULL`、`created_at DATETIME`。索引：`idx_fixture(fixture_id)`、`idx_version(version_code)`
  - 表 2：`purchase_requisitions` / 类 `PurchaseRequisition` / table_kind=`business_record`。字段：`id BIGINT PK`、`fixture_id BIGINT NOT NULL FK fixtures.id`、`requisition_no VARCHAR(32) UNIQUE NOT NULL`、`drawing_id BIGINT NULL FK drawings.id`、`quantity INT NOT NULL`、`spec_note TEXT NULL`、`required_date DATE NULL`、`confirm_status VARCHAR(16) NOT NULL DEFAULT 'pending'`（pending/confirmed，仅 PM 确认动作可改）、`created_by BIGINT NOT NULL FK users.id`、`confirmed_by BIGINT NULL FK users.id`、`confirmed_at DATETIME NULL`、`created_at DATETIME`。索引：`idx_fixture(fixture_id)`
  - **铁律落地**：两表均 `business_record`——**只增不改不删，无 `version` 字段、无 12 状态机 `current_status` 字段**；`purchase_requisitions.confirm_status` 仅由专用 `PATCH .../confirm` 端点写（3-1-2），不是可任意改的核心表状态；`drawings.drawing_file_path` / `dfm_report_path` 存**相对路径正斜杠**（§e.2）；`__table_args__` 含 `utf8mb4`；import 用 `from extensions import db`，**不得** `from app.extensions import db`（§h）；**严禁** `__mapper_args__`。

#### Step 3-1-2：drawing_service + purchase_requisition_service + Blueprint（含 Phase 2 version_bump ↔ drawings 联动回填）
- 涉及文件：`backend/app/services/drawing_service.py`（新建）、`backend/app/services/purchase_requisition_service.py`（新建）、`backend/app/blueprints/drawings.py`（新建）、`backend/app/blueprints/purchase_requisitions.py`（新建）、`backend/app/__init__.py`（注册）、`backend/app/services/fixture_service.py`（**回填**：`version_bump()` 成功后追加一条 `drawings` 记录）
- 前置条件：Step 3-1-1（两表已 `upgrade`）+ Step 3-0-2（上传基础设施就绪，图纸/DFM 走 multipart）
- 模板类型：**T02**
- 关键参数：
  - 端点：`POST /api/drawings`（multipart，图纸+可选 DFM 上传）、`GET /api/drawings?fixture_id=`、`PATCH /api/drawings/:id/confirm`（PM 确认，仅写 `confirmed_by/at`）；`POST /api/purchase-requisitions`、`GET /api/purchase-requisitions?fixture_id=`、`PATCH /api/purchase-requisitions/:id/confirm`（PM 确认，仅写 `confirm_status='confirmed'` + `confirmed_by/at`）
  - 简化流程：`POST /api/drawings` 支持 `is_copied=true` + `source_drawing_id`（复制既有图纸，flow §4.2 简化路径）
  - **回填 Phase 2 联动**：架构决策 #11「版本升级 = 改字段 + drawings 追加」——`fixture_service.version_bump()`（Phase 2 Step 2-4-1 实现的最小版仅改 `current_version_code`）在本步补全为：成功后追加一条 `drawings` 记录（新 `version_code`）。这是 Phase 2 遗留的 ⚠️ 开放问题（Phase 2 detail Step 2-0-1 登记的 ②）在 Phase 3 的收口点。
  - 权限矩阵：见 Step 3-0-1
  - **铁律落地**：`business_record` 端点**无 DELETE、无任意 PUT**（只 `POST` + `GET` + 专用 `PATCH .../confirm`）；扁平化资源 `/api/drawings`，**不**嵌套在 `/fixtures/:id/` 下（§d Rule 6 / api_spec §3）；`fixture_id` 在 body 中传；文件走 3-0-2 `save_upload()`，存相对路径正斜杠；**本步不调 `transition()`、不改 `current_status`**（设计阶段无状态流转，fixture 维持 `pending_iqc`）；Blueprint 不带 `url_prefix`；`POST` / `GET`-list 路由加尾部斜杠（§h）；统一 `success_response`/`error_response`。

---

### 3.2 采购阶段：PO 头 + items 一对多（功能点 2）

#### Step 3-2-1：PurchaseOrder + PurchaseOrderItem Models + Migration
- 涉及文件：`backend/app/models/purchase_order.py`（新建）、`backend/app/models/purchase_order_item.py`（新建）、`backend/app/models/__init__.py`、`backend/migrations/versions/<新>.py`
- 前置条件：Step 3-0-1 完成。本步建一对多结构两张表（§2.11 / 决策 #22）。
- 模板类型：**T01**
- 关键参数：
  - 表 1：`purchase_orders` / 类 `PurchaseOrder` / table_kind=`core`（⚠️ §2.1 明确将 `purchase_orders` 列为**核心表**——禁止 HTTP DELETE，作废走 `status='cancelled'`）。字段：`id BIGINT PK`、`po_no VARCHAR(32) UNIQUE NOT NULL`、`supplier_id BIGINT NOT NULL FK suppliers.id`、`contract_no VARCHAR(64) NULL`、`order_date DATE NOT NULL`（采购下单日）、`total_lead_time_days INT NULL`（总交期）、`total_amount DECIMAL(12,2) NULL`（成本字段，查看权限敏感）、`status VARCHAR(16) NOT NULL DEFAULT 'open'`（open/closed/cancelled）、`created_by BIGINT NOT NULL FK users.id`、`created_at / updated_at`、`version INT NOT NULL DEFAULT 0`。索引：`idx_supplier(supplier_id)`、`idx_status(status)`、`idx_order_date(order_date)`
  - 表 2：`purchase_order_items` / 类 `PurchaseOrderItem` / table_kind=`business_record`。字段：`id BIGINT PK`、`purchase_order_id BIGINT NOT NULL FK purchase_orders.id`、`fixture_id BIGINT NOT NULL FK fixtures.id`、`unit_price DECIMAL(12,2) NULL`（成本，查看权限敏感）、`item_lead_time_days INT NULL`、`created_at DATETIME`。索引：`idx_po(purchase_order_id)`、`idx_fixture(fixture_id)`
  - **铁律落地**：`purchase_orders` 是**核心表**——`__table_args__` 含 `utf8mb4`、必含 `status` + `version`、**严禁 DELETE 路由**（§e.3/§e.12）、**严禁** `__mapper_args__ = {'version_id_col': version}`（§e.5/§h）；`purchase_order_items` 是 `business_record`——只增不改不删、无 version、无 status；import 用 `from extensions import db`（§h）。

#### Step 3-2-2：purchase_order_service + Blueprint
- 涉及文件：`backend/app/services/purchase_order_service.py`（新建）、`backend/app/blueprints/purchase_orders.py`（新建）、`backend/app/__init__.py`（注册）
- 前置条件：Step 3-2-1（两表已 `upgrade`）
- 模板类型：**T02**
- 关键参数：
  - 端点：`POST /api/purchase-orders`（新建 PO 头，含合同号/供应商/总交期）、`POST /api/purchase-orders/:id/items`（添加明细项，关联具体 fixture）、`GET /api/purchase-orders/:id`（PO 详情，含明细项）、`GET /api/purchase-orders`（列表）、`PUT /api/purchase-orders/:id`（编辑 PO 头，含 `version`）、`PATCH /api/purchase-orders/:id/cancel`（作废，写 `status='cancelled'`）
  - **⚠️ 计划日期推算不在本步**：flow §4.3 称"采购下单日 + LT 默认值自动推算各节点计划日期"，但 TASKS.md 将「计划日期推算与级联重算」列在 **Phase 5**。本步**仅存储** `order_date` / `total_lead_time_days` / `item_lead_time_days`，**不**计算 fixture 各节点计划日期——留 `TODO Phase 5` 钩子（见 Step 3-0-1 登记的开放问题 ③）
  - 权限矩阵：见 Step 3-0-1（采购相关 = `purchaser`）
  - **铁律落地**：核心表 `purchase_orders` **禁止 DELETE 路由**，作废走 `PATCH .../cancel`（§e.3）；`PUT` 字段更新用 `'key' in body`，**禁止** `body.get('key')`（§d Rule 5）；乐观锁手动校验 `version != body['version']` 抛 `ConflictError`、更新后 `version += 1`（§e.5）；一对多明细用扁平子资源 `POST /api/purchase-orders/:id/items`（api_spec §5.1）；`total_amount` / `unit_price` 成本字段**存储即可，查看权限控制留 Phase 5 成本模块**；JWT identity 强转 `int`；`POST`/`GET`-list 加尾部斜杠。

---

### 3.3 回厂与 IQC：标准路径 + 紧急上机路径（功能点 3）

#### Step 3-3-1：GoodsReceipt + IqcReport + EmergencyAuthRecord Models + Migration
- 涉及文件：`backend/app/models/goods_receipt.py`、`backend/app/models/iqc_report.py`、`backend/app/models/emergency_auth_record.py`（均新建）、`backend/app/models/__init__.py`、`backend/migrations/versions/<新>.py`
- 前置条件：Step 3-0-1 完成。本步建三张紧耦合的回厂/IQC 业务单据表。
- 模板类型：**T01**
- 关键参数：
  - 表 1：`goods_receipts` / 类 `GoodsReceipt` / `business_record`。字段（推导，核对 flow §4.4 到货签收）：`id`、`fixture_id BIGINT NOT NULL FK fixtures.id`、`actual_arrival_date DATE NOT NULL`、`received_qty INT NOT NULL`、`receipt_photo_path VARCHAR(512) NULL`、`received_by BIGINT NOT NULL FK users.id`、`created_at`。索引：`idx_fixture`
  - 表 2：`iqc_reports` / 类 `IqcReport` / `business_record`。字段：`id`、`fixture_id BIGINT NOT NULL FK fixtures.id`、`inspection_result VARCHAR(16) NOT NULL`（`pass`/`fail`）、`inspection_items TEXT NULL`（关键尺寸/材料/表面处理/外观/功能性结果）、`report_photo_path VARCHAR(512) NULL`、`conclusion_note TEXT NULL`、`inspected_by BIGINT NOT NULL FK users.id`、`created_at`。索引：`idx_fixture`、`idx_result`
  - 表 3：`emergency_auth_records` / 类 `EmergencyAuthRecord` / `business_record`。字段（紧急上机授权单）：`id`、`fixture_id BIGINT NOT NULL FK fixtures.id`、`risk_note TEXT NOT NULL`、`pm_id BIGINT NOT NULL FK users.id`、`iqc_id BIGINT NOT NULL FK users.id`、`authorized_at DATETIME NULL`、`created_at`
  - **铁律落地**：三表均 `business_record`——只增不改不删、无 `version`、无 `current_status`；照片字段存相对路径正斜杠（§e.2）；`__table_args__` 含 `utf8mb4`；import 用 `from extensions import db`；**严禁** `__mapper_args__`。

#### Step 3-3-2：receipt_service + iqc_service + emergency_auth_service + Blueprint
- 涉及文件：`backend/app/services/goods_receipt_service.py`、`backend/app/services/iqc_service.py`、`backend/app/services/emergency_auth_service.py`（均新建）、`backend/app/blueprints/iqc.py`（新建，聚合三类回厂/IQC 端点）、`backend/app/__init__.py`（注册）
- 前置条件：Step 3-3-1（三表已 `upgrade`）+ Step 3-0-2（上传基础设施）
- 模板类型：**T02**
- 关键参数：
  - 端点：`POST /api/goods-receipts`（multipart，到货签收+签收凭证照片）、`GET /api/goods-receipts?fixture_id=`；`POST /api/iqc-reports`（multipart，IQC 报告+检验照片，含 `inspection_result`）、`GET /api/iqc-reports?fixture_id=`；`POST /api/emergency-auth-records`（紧急上机授权单录入）、`GET /api/emergency-auth-records?fixture_id=`
  - **状态流转（解耦，前端另发 `PATCH /status`）**：标准路径 `pending_iqc→iqc_inspecting`（`normal`）、`iqc_inspecting→installing`（`iqc_pass`，IQC 合格）——这两条**无审批门控**，Phase 3 可正常用 Phase 2 的 `PATCH /status`
  - **审批-gated → 501 + TODO Phase 4**：IQC 不合格三方审批（决策 A 退厂返修 `return_repair` / 决策 B 让步接受 `concession_approved`）、紧急上机授权审批（`emergency_auth`）——本步**只落库** `iqc_reports`（`inspection_result='fail'`）与 `emergency_auth_records` 单据数据，三方/双人审批流引擎与 `return_repair`/`concession_approved`/`emergency_auth` 流转一律 `501 + TODO Phase 4`（CLAUDE.md §e.6）
  - 权限矩阵：见 Step 3-0-1（到货签收 = `warehouse`；IQC 报告 = `iqc`；紧急上机授权 = `pm + iqc`）
  - **铁律落地**：`business_record` 端点只 `POST` + `GET`，**无 DELETE、无任意 PUT**；扁平化资源（api_spec §3）；`fixture_id` 在 body；**本步不调 `transition()`、不改 `current_status`**——状态流转由前端在单据 POST 成功后另发 `PATCH /api/fixtures/:id/status`；审批-gated 流转 `501 + TODO Phase 4`，**严禁**在本步"顺手实现"审批流（§e.6）；文件走 3-0-2；`POST`/`GET`-list 加尾部斜杠。

---

### 3.4 安装调试记录（功能点 4）

#### Step 3-4-1：InstallRecord Model + Migration
- 涉及文件：`backend/app/models/install_record.py`（新建）、`backend/app/models/__init__.py`、`backend/migrations/versions/<新>.py`
- 前置条件：Step 3-0-1 完成
- 模板类型：**T01**
- 关键参数：
  - 表 `install_records` / 类 `InstallRecord` / `business_record`。字段（核对 flow §4.5 安装调试）：`id`、`fixture_id BIGINT NOT NULL FK fixtures.id`、`install_note TEXT NULL`、`debug_params TEXT NULL`（调机参数）、`install_photo_path VARCHAR(512) NULL`、`installed_by BIGINT NOT NULL FK users.id`（ME）、`created_at`。索引：`idx_fixture`
  - **铁律落地**：`business_record`——只增不改不删、无 version、无 status；照片字段存相对路径正斜杠；`__table_args__` 含 `utf8mb4`；import 用 `from extensions import db`；**严禁** `__mapper_args__`。

#### Step 3-4-2：install_service + Blueprint
- 涉及文件：`backend/app/services/install_service.py`（新建）、`backend/app/blueprints/install_records.py`（新建）、`backend/app/__init__.py`（注册）
- 前置条件：Step 3-4-1 + Step 3-0-2
- 模板类型：**T02**
- 关键参数：
  - 端点：`POST /api/install-records`（multipart，安装调试记录+照片）、`GET /api/install-records?fixture_id=`
  - 状态流转（解耦）：安装调试完成后 `installing→acceptance_testing`（`normal`）——无审批门控，前端在单据 POST 成功后另发 `PATCH /status`。flow §4.5 注：无独立预验收节点，ME 完成安装调试后**直接**触发试产验收
  - 权限矩阵：见 Step 3-0-1（安装记录 = `me`）
  - **铁律落地**：`business_record` 端点只 `POST` + `GET`，无 DELETE/任意 PUT；扁平化资源；`fixture_id` 在 body；**不调 `transition()`、不改 `current_status`**；文件走 3-0-2；`POST`/`GET`-list 加尾部斜杠；统一响应工具。

---

### 3.5 试产验收：合格 / 不合格分支（功能点 5）

#### Step 3-5-1：AcceptanceReport Model + Migration
- 涉及文件：`backend/app/models/acceptance_report.py`（新建）、`backend/app/models/__init__.py`、`backend/migrations/versions/<新>.py`
- 前置条件：Step 3-0-1 完成
- 模板类型：**T01**
- 关键参数：
  - 表 `acceptance_reports` / 类 `AcceptanceReport` / `business_record`。字段（核对 flow §4.5 正式试产验收）：`id`、`fixture_id BIGINT NOT NULL FK fixtures.id`、`acceptance_result VARCHAR(16) NOT NULL`（`pass`/`fail`）、`report_photo_path VARCHAR(512) NULL`、`conclusion_note TEXT NULL`、`accepted_by BIGINT NOT NULL FK users.id`（质量工程师）、`created_at`。索引：`idx_fixture`、`idx_result`
  - **铁律落地**：`business_record`——只增不改不删、无 version、无 status；照片字段相对路径正斜杠；`__table_args__` 含 `utf8mb4`；import 用 `from extensions import db`；**严禁** `__mapper_args__`。

#### Step 3-5-2：acceptance_service + Blueprint
- 涉及文件：`backend/app/services/acceptance_service.py`（新建）、`backend/app/blueprints/acceptance_reports.py`（新建）、`backend/app/__init__.py`（注册）
- 前置条件：Step 3-5-1 + Step 3-0-2
- 模板类型：**T02**
- 关键参数：
  - 端点：`POST /api/acceptance-reports`（multipart，验收报告+照片，含 `acceptance_result`）、`GET /api/acceptance-reports?fixture_id=`
  - **合格分支（解耦，无审批门控）**：`acceptance_result='pass'` → 前端另发 `PATCH /status` 走 `acceptance_pass`（`acceptance_testing→in_stock`）；紧急上机治具验收合格时补录 IQC 合格（业务规则，flow §4.5）
  - **不合格分支 → 501 + TODO Phase 4**：`acceptance_result='fail'` 触发三部门联合评审（开发+制技+质量），评审决策对应 `rework`（`acceptance_testing→installing`）或 `acceptance_fail_scrap`（`acceptance_testing→scrapped`）——本步**只落库** `acceptance_reports`（`fail`），三部门评审审批流与 `rework`/`acceptance_fail_scrap` 流转一律 `501 + TODO Phase 4`
  - 权限矩阵：见 Step 3-0-1
  - **铁律落地**：`business_record` 端点只 `POST` + `GET`；扁平化资源；`fixture_id` 在 body；**不调 `transition()`、不改 `current_status`**；不合格走审批流的部分 `501 + TODO Phase 4`，**严禁**顺手实现三部门评审（§e.6）；文件走 3-0-2；`POST`/`GET`-list 加尾部斜杠。

---

### 3.6 移交接收（功能点 6）

#### Step 3-6-1：HandoverRecord Model + Migration
- 涉及文件：`backend/app/models/handover_record.py`（新建）、`backend/app/models/__init__.py`、`backend/migrations/versions/<新>.py`
- 前置条件：Step 3-0-1 完成
- 模板类型：**T01**
- 关键参数：
  - 表 `handover_records` / 类 `HandoverRecord` / `business_record`。字段（核对 flow §4.6 模治具正式移交）：`id`、`fixture_id BIGINT NOT NULL FK fixtures.id`、`handover_photo_path VARCHAR(512) NULL`（移交确认单）、`shelf_location VARCHAR(64) NULL`（货架/库位绑定）、`warehouse_keeper_id BIGINT NOT NULL FK users.id`、`production_lead_id BIGINT NOT NULL FK users.id`、`handover_at DATETIME NULL`、`created_at`。索引：`idx_fixture`
  - ⚠️ `shelf_location` 暂存于本单据；若库位需作为 `fixtures` 表的活属性（领用/盘点会用），属 **Phase 5 仓储模块「货架绑定与库位管理」**——见 Step 3-0-1 登记的开放问题 ④
  - **铁律落地**：`business_record`——只增不改不删、无 version、无 status；照片字段相对路径正斜杠；`__table_args__` 含 `utf8mb4`；import 用 `from extensions import db`；**严禁** `__mapper_args__`。

#### Step 3-6-2：handover_service + Blueprint
- 涉及文件：`backend/app/services/handover_service.py`（新建）、`backend/app/blueprints/handover_records.py`（新建）、`backend/app/__init__.py`（注册）
- 前置条件：Step 3-6-1 + Step 3-0-2
- 模板类型：**T02**
- 关键参数：
  - 端点：`POST /api/handover-records`（multipart，移交确认单+照片+货架绑定）、`GET /api/handover-records?fixture_id=`
  - **⚠️ 状态语义说明**：§3.3 `TRANSITIONS` **无"移交"流转**，`acceptance_pass` 已在 3.5 直接 `acceptance_testing→in_stock`。本细化采用的解释：**移交确认仅作业务单据 + 货架绑定，不触发状态流转**（fixture 此时已是 `in_stock`）；Service 应校验 fixture 当前 `current_status == in_stock` 作为前置。是否需要"验收合格-待移交"中间态见 Step 3-0-1 登记的开放问题 ①，**待 Frank 裁决前不擅自新增状态**（§e.4：新增 status = 架构评审）
  - 权限矩阵：见 Step 3-0-1（移交 = `warehouse` + `production_lead`）
  - **铁律落地**：`business_record` 端点只 `POST` + `GET`；扁平化资源；`fixture_id` 在 body；**不调 `transition()`、不改 `current_status`**——本节点无状态流转；**严禁**自行新增"移交"trigger 或中间态（§e.4 / §g）；文件走 3-0-2；`POST`/`GET`-list 加尾部斜杠。

---

### 3.7 生产领用与归还（功能点 7）

#### Step 3-7-1：CheckoutRecord Model + fixtures.usage_count 字段补充 + Migration
- 涉及文件：`backend/app/models/checkout_record.py`（新建）、`backend/app/models/fixture.py`（**字段补充**：加 `usage_count`）、`backend/app/models/__init__.py`、`backend/migrations/versions/<新>.py`
- 前置条件：Step 3-0-1 完成。本步含对 Phase 2 已建 `fixtures` 表的字段补充（T01 支持字段变更）。
- 模板类型：**T01**
- 关键参数：
  - 表 `checkout_records` / 类 `CheckoutRecord` / `business_record`。字段（核对 flow §4.7 生产领用与使用）：`id`、`fixture_id BIGINT NOT NULL FK fixtures.id`、`checkout_by BIGINT NOT NULL FK users.id`（领用人）、`product_line VARCHAR(64) NULL`、`checkout_at DATETIME NOT NULL`、`return_at DATETIME NULL`、`returned_by BIGINT NULL FK users.id`、`created_at`。索引：`idx_fixture`
  - `fixtures` 表字段补充：`usage_count INT NOT NULL DEFAULT 0`（使用次数，归还时累加）——flow §4.7「使用后归还，使用次数自动累加」
  - **铁律落地**：`checkout_records` 是 `business_record`——只增不改不删（归还通过 `PATCH .../return` 仅回写 `return_at`/`returned_by`，不视为任意改）；`fixtures` 字段补充走 Migration，**审查迁移脚本时确认无意外 `drop`/类型缩窄**（T01 Step 5）；`__table_args__` 含 `utf8mb4`；import 用 `from extensions import db`；**严禁** `__mapper_args__`；`fixtures` 加字段时**不得**误加 `version_id_col`。

#### Step 3-7-2：checkout_service + Blueprint
- 涉及文件：`backend/app/services/checkout_service.py`（新建）、`backend/app/blueprints/checkout_records.py`（新建）、`backend/app/__init__.py`（注册）
- 前置条件：Step 3-7-1 + Step 3-0-2
- 模板类型：**T02**
- 关键参数：
  - 端点：`POST /api/checkout-records`（领用录入）、`PATCH /api/checkout-records/:id/return`（归还，回写 `return_at`/`returned_by` + `fixtures.usage_count += 1`）、`GET /api/checkout-records?fixture_id=`
  - 状态流转（解耦，无审批门控）：领用 `in_stock→in_use`（`checkout`）、归还 `in_use→in_stock`（`return`）——前端在单据 POST/PATCH 成功后另发 `PATCH /status`
  - **⚠️ 封存禁领用铁律**：§3.3.x / flow §4.1.4 规定封存治具**禁止领用**——`checkout_service` 创建领用记录前**必须校验** `fixture.is_sealed == False`，否则抛 `ForbiddenError`（403）或 `ValidationError`
  - 权限矩阵：见 Step 3-0-1（领用归还 = `production_lead`）
  - **铁律落地**：领用前校验 `is_sealed == False`（§3.3.x 封存禁领用）；`business_record` 端点无 DELETE/任意 PUT（归还走专用 `PATCH .../return`）；扁平化资源；`fixture_id` 在 body；**不调 `transition()`、不改 `current_status`**；`fixtures.usage_count` 累加在 Service 层（非状态机职责）；`POST`/`GET`-list 加尾部斜杠。

---

### 3.8 保养触发与记录（功能点 8）

#### Step 3-8-1：MaintenanceRecord Model + fixtures 保养阈值字段补充 + Migration
- 涉及文件：`backend/app/models/maintenance_record.py`（新建）、`backend/app/models/fixture.py`（**字段补充**：加保养阈值/计数字段）、`backend/app/models/__init__.py`、`backend/migrations/versions/<新>.py`
- 前置条件：Step 3-0-1 完成；建议在 Step 3-7-1 之后（同样改 `fixtures` 表，避免 Migration head 冲突）
- 模板类型：**T01**
- 关键参数：
  - 表 `maintenance_records` / 类 `MaintenanceRecord` / `business_record`。字段（核对 flow §4.7 点检与计划保养）：`id`、`fixture_id BIGINT NOT NULL FK fixtures.id`、`maintenance_items TEXT NULL`（清洁/润滑/磨损件更换/尺寸复检）、`next_threshold INT NULL`（更新后的下次保养阈值）、`maintenance_photo_path VARCHAR(512) NULL`、`maintained_by BIGINT NOT NULL FK users.id`（ME）、`created_at`。索引：`idx_fixture`
  - `fixtures` 表字段补充：`maintenance_threshold INT NULL`（使用次数保养阈值）——与 3-7-1 的 `usage_count` 配合，供保养自动触发判定
  - **铁律落地**：`maintenance_records` 是 `business_record`——只增不改不删、无 version、无 status；`fixtures` 字段补充走 Migration，审查脚本确认无意外 `drop`；照片字段相对路径正斜杠；`__table_args__` 含 `utf8mb4`；import 用 `from extensions import db`；**严禁** `__mapper_args__` / `version_id_col`。

#### Step 3-8-2：maintenance_service + Blueprint
- 涉及文件：`backend/app/services/maintenance_service.py`（新建）、`backend/app/blueprints/maintenance_records.py`（新建）、`backend/app/__init__.py`（注册）
- 前置条件：Step 3-8-1 + Step 3-0-2
- 模板类型：**T02**
- 关键参数：
  - 端点：`POST /api/maintenance-records`（multipart，保养记录+照片，写 `next_threshold`）、`GET /api/maintenance-records?fixture_id=`
  - 状态流转（解耦，无审批门控）：保养触发 `in_use→maintaining`（`maintenance_due`）、保养完成 `maintaining→in_stock`（`normal`）——前端另发 `PATCH /status`
  - **⚠️ 保养自动触发 + 邮件告警 → 501 + TODO Phase 6**：flow §4.7「系统根据使用次数阈值自动触发保养提醒，发送邮件至 ME 与生产部班长」——自动触发判定 + `send_alert_dedup` 邮件属 **Phase 6 告警模块**（TASKS.md Phase 6）。Phase 3 只实现**手动**录入保养记录 + 手动状态流转；自动触发与邮件 `501 + TODO Phase 6`
  - 权限矩阵：见 Step 3-0-1（保养执行 = `me`）
  - **铁律落地**：`business_record` 端点只 `POST` + `GET`，无 DELETE/任意 PUT；扁平化资源；`fixture_id` 在 body；**不调 `transition()`、不改 `current_status`**；**严禁**在本步实现 `send_alert_dedup` 或 APScheduler 自动触发任务（留 Phase 6，§e.9）；文件走 3-0-2；`POST`/`GET`-list 加尾部斜杠。

---

### 3.9 报修与维修（功能点 9）

#### Step 3-9-1：RepairRecord Model + Migration
- 涉及文件：`backend/app/models/repair_record.py`（新建）、`backend/app/models/__init__.py`、`backend/migrations/versions/<新>.py`
- 前置条件：Step 3-0-1 完成
- 模板类型：**T01**
- 关键参数：
  - 表 `repair_records` / 类 `RepairRecord` / `business_record`。字段（核对 flow §4.7 报修与修复——报修单 + 维修记录合并为一行，报修创建、维修完成回填）：`id`、`fixture_id BIGINT NOT NULL FK fixtures.id`、`fault_description TEXT NOT NULL`（故障现象）、`fault_photo_path VARCHAR(512) NULL`、`repair_method VARCHAR(16) NULL`（`internal`/`external`）、`repair_cost DECIMAL(12,2) NULL`（维修费用，查看权限敏感）、`repair_note TEXT NULL`、`reported_by BIGINT NOT NULL FK users.id`（生产部班长）、`repaired_by BIGINT NULL FK users.id`（ME）、`repaired_at DATETIME NULL`、`created_at`。索引：`idx_fixture`
  - **铁律落地**：`business_record`——只增不改不删（维修完成通过专用 `PATCH .../complete` 仅回填维修字段，不视为任意改）；照片字段相对路径正斜杠；`__table_args__` 含 `utf8mb4`；import 用 `from extensions import db`；**严禁** `__mapper_args__`。

#### Step 3-9-2：repair_service + Blueprint
- 涉及文件：`backend/app/services/repair_service.py`（新建）、`backend/app/blueprints/repair_records.py`（新建）、`backend/app/__init__.py`（注册）
- 前置条件：Step 3-9-1 + Step 3-0-2
- 模板类型：**T02**
- 关键参数：
  - 端点：`POST /api/repair-records`（multipart，报修单+故障照片）、`PATCH /api/repair-records/:id/complete`（维修完成回填 `repair_method`/`repair_cost`/`repaired_by`/`repaired_at`）、`GET /api/repair-records?fixture_id=`
  - 状态流转（解耦，无审批门控）：报修 `in_use→repairing`（`repair_request`）、维修完成 `repairing→in_stock`（`normal`）——前端另发 `PATCH /status`
  - 权限矩阵：见 Step 3-0-1（报修发起 = `production_lead`，维修执行 = `me`）
  - **铁律落地**：`business_record` 端点无 DELETE/任意 PUT（维修完成走专用 `PATCH .../complete`）；扁平化资源；`fixture_id` 在 body；**不调 `transition()`、不改 `current_status`**；`repair_cost` 成本字段存储即可、查看权限留 Phase 5；文件走 3-0-2；`POST`/`GET`-list 加尾部斜杠。

---

### 3.10 报废申请（功能点 10）

#### Step 3-10-1：ScrapRecord Model + Migration
- 涉及文件：`backend/app/models/scrap_record.py`（新建）、`backend/app/models/__init__.py`、`backend/migrations/versions/<新>.py`
- 前置条件：Step 3-0-1 完成
- 模板类型：**T01**
- 关键参数：
  - 表 `scrap_records` / 类 `ScrapRecord` / `business_record`。字段（核对 flow §4.8 报废申请）：`id`、`fixture_id BIGINT NOT NULL FK fixtures.id`、`scrap_reason VARCHAR(32) NOT NULL`（超寿命/损坏不可修/产品停产/技术迭代）、`condition_note TEXT NULL`（现状评估）、`scrap_photo_path VARCHAR(512) NULL`、`applied_by BIGINT NOT NULL FK users.id`（PM）、`created_at`。索引：`idx_fixture`
  - **铁律落地**：`business_record`——只增不改不删、无 version、无 status；照片字段相对路径正斜杠；`__table_args__` 含 `utf8mb4`；import 用 `from extensions import db`；**严禁** `__mapper_args__`。

#### Step 3-10-2：scrap_service + Blueprint
- 涉及文件：`backend/app/services/scrap_service.py`（新建）、`backend/app/blueprints/scrap_records.py`（新建）、`backend/app/__init__.py`（注册）
- 前置条件：Step 3-10-1 + Step 3-0-2
- 模板类型：**T02**
- 关键参数：
  - 端点：`POST /api/scrap-records`（multipart，报废申请单+照片）、`GET /api/scrap-records?fixture_id=`
  - **审批-gated → 501 + TODO Phase 4**：flow §4.8 报废需 PM + 生产部负责人 + 业务工程师**三方线上会签**（§e.6 审批流场景）。Phase 3 **只落库** `scrap_records`（报废申请单据）；三方会签审批流引擎 + 会签通过后的 `scrap` 流转（`in_stock→scrapped`）一律 `501 + TODO Phase 4`
  - 权限矩阵：见 Step 3-0-1（报废申请发起 = `pm`）
  - **铁律落地**：`business_record` 端点只 `POST` + `GET`，无 DELETE/任意 PUT；扁平化资源；`fixture_id` 在 body；**不调 `transition()`、不改 `current_status`**——`scrap` 流转受会签门控留 Phase 4；**严禁**在本步实现三方会签审批流（§e.6）；文件走 3-0-2；`POST`/`GET`-list 加尾部斜杠。

---

### 3.11 单元测试

#### Step 3-11-1：test 设计 / 采购 / IQC 阶段 services
- 涉及文件：`backend/tests/test_drawing_service.py`、`backend/tests/test_purchase_order_service.py`、`backend/tests/test_iqc_service.py`（均新建）、`backend/tests/conftest.py`（按需扩展 fixture）
- 前置条件：Step 3-1-2 + Step 3-2-2 + Step 3-3-2 烟测通过
- 模板类型：**T07**
- 关键参数：
  - 用例矩阵：图纸（合法上传 / `is_copied` 复制 / PM 确认仅写签核字段 / 缺权限 403）× 采购订单（PO 头创建 + items 添加 / `PUT` 乐观锁 version 正确/缺失/过期 / `cancel` 写 `status='cancelled'` / 缺权限 403）× IQC（到货签收 / IQC 报告 `pass`/`fail` 落库 / 紧急上机授权单录入 / 缺权限 403）
  - **审批-gated 用例**：断言 IQC 不合格三方审批 / 紧急上机审批相关端点返回 `501`（确认 Phase 4 占位到位，不被误实现）
  - **铁律落地**：测试代码**不修改被测代码**（T07 职责边界——发现 bug 转 T06）；`create_access_token` **必带** `additional_claims={'role_codes':[...]}`，否则 `@require_role` 静默 403（§h / T07 文档约束 #5）；conftest 用 connection-level transaction + nested savepoint 隔离用例；**禁止**引入 `factory_boy`/`faker`；multipart 上传测试 patch 文件存储或用临时目录，**不**真写 `UPLOAD_BASE`。

#### Step 3-11-2：test 安装 / 验收 / 移交 阶段 services
- 涉及文件：`backend/tests/test_install_service.py`、`backend/tests/test_acceptance_service.py`、`backend/tests/test_handover_service.py`（均新建）、`backend/tests/conftest.py`（按需扩展）
- 前置条件：Step 3-4-2 + Step 3-5-2 + Step 3-6-2 烟测通过
- 模板类型：**T07**
- 关键参数：
  - 用例矩阵：安装记录（合法录入 / 缺权限 403）× 验收报告（`pass` 落库 / `fail` 落库 / 缺权限 403）× 移交记录（合法录入 + 校验 fixture `current_status==in_stock` 前置 / `current_status` 非 `in_stock` 时拒绝 / 缺权限 403）
  - **审批-gated 用例**：断言验收不合格三部门评审相关端点返回 `501`
  - **边界用例**：断言 `handover_service` **不**触发任何 `transition()`（移交不改状态——见开放问题 ①）
  - **铁律落地**：同 3-11-1（不改被测代码 / `additional_claims` / nested savepoint / 不引入新库 / multipart 不真写磁盘）。

#### Step 3-11-3：test 领用归还 / 维保 / 维修 / 报废 阶段 services
- 涉及文件：`backend/tests/test_checkout_service.py`、`backend/tests/test_maintenance_service.py`、`backend/tests/test_repair_service.py`、`backend/tests/test_scrap_service.py`（均新建）、`backend/tests/conftest.py`（按需扩展）
- 前置条件：Step 3-7-2 + Step 3-8-2 + Step 3-9-2 + Step 3-10-2 烟测通过
- 模板类型：**T07**
- 关键参数：
  - 用例矩阵：领用归还（领用录入 / 归还回写 `return_at` + `usage_count += 1` / **封存治具领用被拒** `is_sealed==True` → 403 / 缺权限 403）× 保养（记录录入 + 写 `next_threshold` / 缺权限 403 / 断言自动触发邮件相关端点 `501`）× 维修（报修录入 / `complete` 回填维修字段 / 缺权限 403）× 报废（报废申请单落库 / 断言三方会签端点 `501` / 缺权限 403）
  - **必含铁律用例**：`test_checkout_sealed_fixture_forbidden`——封存治具（`is_sealed=True`）领用必须被拒（§3.3.x）
  - **铁律落地**：同 3-11-1（不改被测代码 / `additional_claims` / nested savepoint / 不引入新库 / multipart 不真写磁盘）。

---

### 3.12 前端流程节点

> **说明**：Phase 3 流程节点前端围绕"治具详情时间线 + 各节点操作对话框"组织，**不**为每个单据单独建独立页面。各节点单据 POST 成功后，前端**另发** `PATCH /api/fixtures/:id/status` 完成状态流转（与后端解耦设计一致）。

#### Step 3-12-1：FixtureDetail 治具详情/全生命周期时间线页
- 涉及文件：`frontend/src/views/fixture/FixtureDetail.vue`（新建）、`frontend/src/api/fixture.js`（追加 `getFixtureLifecycle` 等聚合查询）、`frontend/src/router/index.js`（追加/调整路由）
- 前置条件：Step 3-1-2 ~ Step 3-10-2 中至少设计/采购/IQC 阶段端点已通（建议全部 T02 完成后做）
- 模板类型：**T04（详情页变体——时间线/只读为主，无完全对应模板，参照 T04 detail 模式 + T03 列表渲染）**
- 关键参数：
  - 展示：治具基本信息（编码/型号/套号/当前版本/当前状态）+ 全生命周期时间线（聚合 `status_history` + 各 `*-records` 单据，按 `created_at` 排序）
  - 各单据卡片可下钻查看详情、附件走 `GET /api/files/<path>` 鉴权下载
  - 状态流转、版本升级、加开-复制等操作入口（Phase 2 已建的按钮）在本页聚合
  - **铁律落地**：前端 import 用**相对路径**，**禁止** `@/`（§d Rule 7）；状态/结果标签 `el-tag` 走 `utils/status.js`、`type` prop 兜底合法（`|| 'info'`，§d Rule 8）；所有时间字段走 `parseBackendTime`/`formatBackendTime`，**严禁**裸 `dayjs(str)`/`new Date(str)`（§e.10）；时间线 `v-for` 列表用稳定 key（单据 id），**禁用** index 作 key（§d Rule 10）；`ElMessage`/`ElMessageBox` 显式 import（§d Rule 11）。

#### Step 3-12-2：设计 / 采购 / IQC 阶段操作表单与对话框
- 涉及文件：`frontend/src/views/fixture/dialogs/`（新建：图纸DFM上传 / 采购申请单 / PO头+items / 到货签收 / IQC报告 / 紧急上机授权 等对话框组件）、`frontend/src/api/`（新建 `drawing.js` / `purchaseOrder.js` / `iqc.js` 等 API client）、`FixtureDetail.vue`（挂载对话框入口）
- 前置条件：Step 3-12-1 + 对应后端 T02（3-1-2 / 3-2-2 / 3-3-2）完成
- 模板类型：**T04**
- 关键参数：
  - 各对话框为表单 + 文件上传（`<el-upload>` 走 multipart，提交至对应 `POST /api/...`）
  - PO 为头+items 两段表单（先建头，再逐项加 item）
  - 单据 POST 成功后，按业务规则**另发** `PATCH /api/fixtures/:id/status`（如到货签收成功 → `normal`、IQC 合格 → `iqc_pass`）；审批-gated 的不合格/紧急路径前端仅提示"将进入审批流（Phase 4）"，**不**调用未实现端点
  - **铁律落地**：相对路径 import；`ElMessageBox.confirm` 二段 try/catch（用户取消静默退出，§d Rule 9）；`ElMessage`/`ElMessageBox` 显式 import；上传文件路径由后端返回、前端不拼接；提交携带必要的 `version`（如涉及 PO 编辑）；`parseBackendTime` 处理回显时间。

#### Step 3-12-3：安装 / 验收 / 移交 / 领用归还 / 维保 / 维修 / 报废 操作表单与对话框
- 涉及文件：`frontend/src/views/fixture/dialogs/`（新建：安装调试 / 验收报告 / 移交确认 / 领用归还 / 保养记录 / 报修维修 / 报废申请 等对话框组件）、`frontend/src/api/`（新建对应 API client）、`FixtureDetail.vue`（挂载对话框入口）
- 前置条件：Step 3-12-1 + 对应后端 T02（3-4-2 ~ 3-10-2）完成
- 模板类型：**T04**
- 关键参数：
  - 各对话框为表单 + 文件上传，提交至对应 `POST /api/...`-records；归还/维修完成走专用 `PATCH .../return` / `PATCH .../complete`
  - 单据 POST 成功后按规则另发 `PATCH /status`（安装完成 → `normal`、验收合格 → `acceptance_pass`、领用 → `checkout`、归还 → `return`、保养触发 → `maintenance_due`、报修 → `repair_request` 等）
  - **封存治具领用**：领用对话框打开前/提交前前端先判 `is_sealed`，封存治具置灰领用入口并提示（后端 3-7-2 已硬校验，前端做友好拦截）
  - 审批-gated 路径（验收不合格 / 报废会签）前端仅提示"将进入审批流（Phase 4）"，**不**调用未实现端点
  - **铁律落地**：相对路径 import；`ElMessageBox` 二段 try/catch；`ElMessage`/`ElMessageBox` 显式 import；按钮权限 `hasPermission` 控制；`parseBackendTime` 处理时间；上传文件路径由后端返回、前端不拼接。

---

### ⚠️ 范围边界提示（请 Frank 关注，已在 Step 3-0-1 登记为开放问题）

1. **移交确认与状态机的语义缺口**：§3.3 `TRANSITIONS` 中 `acceptance_pass` 直接 `ACCEPTANCE_TESTING→IN_STOCK`，**没有"移交"流转、也没有"验收合格-待移交"中间态**。本细化按"移交确认 = 纯业务单据 + 货架绑定，不改状态"实现（3-6-2）。若 Frank 认为需要中间态，属状态机变更（§e.4，须走架构评审 + T05），**不在 Phase 3 范围**。
2. **单据 POST 与状态流转的解耦 vs 内联**：本细化严格遵循 api_spec §3「解耦」——`*-records` 端点只落库，状态流转由前端另发 `PATCH /status`。若 Frank 希望单据 POST 内联状态流转（原子性更强），需在 3-0-1 决策并调整所有 T02 步骤；但内联会让 `*-records` 端点产生写状态机的副作用，与 §e.4「状态变更唯一入口」存在张力，**建议维持解耦**。
3. **计划日期推算的归属**：flow §4.3 称采购下单时自动推算各节点计划日期，但 TASKS.md 将「计划日期推算与级联重算」明确列在 **Phase 5**。本细化 3-2-2 仅存 `order_date`/LT，**不**算节点计划日期（留 `TODO Phase 5`）。
4. **货架/库位与使用次数作为 fixtures 活属性**：3-7-1 已为 `fixtures` 补 `usage_count`、3-8-1 补 `maintenance_threshold`（领用/保养判定刚需）；但 `shelf_location` 当前仅存于 `handover_records`。若库位需作为 `fixtures` 的可查询活属性（盘点/库位管理），属 **Phase 5 仓储模块「货架绑定与库位管理」**，本阶段不在 `fixtures` 上加该列。
5. **审批流全部留 Phase 4**：紧急上机授权 / IQC 不合格三方审批 / 让步接受 / 试产不合格三部门评审 / 报废三方会签 5 个场景，Phase 3 **只建业务单据表与录入端点**，审批流引擎 + 审批-gated 流转（`emergency_auth`/`concession_approved`/`return_repair`/`rework`/`acceptance_fail_scrap`/`scrap`）一律 `501 + TODO Phase 4`。**严禁** CLI 在 Phase 3「顺手实现」任何审批流代码（§e.6）。

---

**建议执行顺序**：3-0-1 → 3-0-2 → 3-1-1 → 3-1-2 → 3-2-1 → 3-2-2 → 3-3-1 → 3-3-2 → 3-11-1 → 3-4-1 → 3-4-2 → 3-5-1 → 3-5-2 → 3-6-1 → 3-6-2 → 3-11-2 → 3-7-1 → 3-7-2 → 3-8-1 → 3-8-2 → 3-9-1 → 3-9-2 → 3-10-1 → 3-10-2 → 3-11-3 → 3-12-1 → 3-12-2 → 3-12-3

### Phase 3 模板使用统计

| 模板 | 使用次数 | 使用 Step |
|------|---------|-----------|
| 手写提示词 | 2 | 3-0-1 / 3-0-2 |
| T01 | 10 | 3-1-1 / 3-2-1 / 3-3-1 / 3-4-1 / 3-5-1 / 3-6-1 / 3-7-1 / 3-8-1 / 3-9-1 / 3-10-1 |
| T02 | 10 | 3-1-2 / 3-2-2 / 3-3-2 / 3-4-2 / 3-5-2 / 3-6-2 / 3-7-2 / 3-8-2 / 3-9-2 / 3-10-2 |
| T03 | 0 | （Phase 3 无纯列表页；FixtureDetail 时间线归入 T04 变体） |
| T04 | 3 | 3-12-1 / 3-12-2 / 3-12-3 |
| T05 | 0 | （Phase 3 不修改状态机——§3.3 TRANSITIONS 已覆盖全部流转触发器） |
| T06 | 0 | （Bug 修复，按需触发） |
| T07 | 3 | 3-11-1 / 3-11-2 / 3-11-3 |
