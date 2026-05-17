# API 规约

> 摘自 V1.3 架构文档第 3.2 节(原文标注"同 V1.2,无变更",端点清单从 V1.2 完整继承)。
>
> **本文件以 V1.3 列出的端点清单为权威**。实际开发以代码为准。
>
> 接口风格:RESTful JSON over HTTP,统一前缀 `/api`,认证使用 JWT (Flask-JWT-Extended)。

---

## 通用响应格式

**成功响应**:
```json
{ "code": 200, "message": "success", "data": { ... } }
```

**错误响应**:
```json
{ "code": 400, "message": "Validation error: field is required", "data": null }
```

**乐观锁冲突 (409)**:
```json
{
  "code": 409,
  "message": "Conflict: modified by another user. Please refresh.",
  "data": { "server_version": 5, "your_version": 3 }
}
```

---

## 通用约束(摘自 V1.3 + CLAUDE_reference)

1. **核心表禁止 HTTP DELETE**:`projects` / `batches` / `fixtures` / `purchase_orders` 等核心表的"作废"走 `PATCH .../cancel` 改 `status='cancelled'`;真·删除仅 `scripts/reset_db.py` 提供。
2. **配置型表用 PATCH 启停**:用户、供应商、模板等走 `PATCH .../deactivate`、`PATCH .../activate`,不提供 DELETE。
3. **乐观锁字段必传**:所有写操作请求体含 `version` 字段,Service 层手动比对失败抛 409。
4. **业务单据扁平化资源**:IQC、验收、安装、维保、维修、报废等业务单据用扁平化路径(`POST /api/iqc-reports`),通过 body 中的 `fixture_id` 关联,而非嵌套在 `fixtures/:id/` 之下。
5. **状态流转统一入口**:所有状态变更走 `PATCH /api/fixtures/:id/status`,用 `trigger` 字段区分 normal / iqc_pass / checkout / return / maintenance_due 等场景;严格走 TRANSITIONS。
6. **JWT identity 强转 int**:`user_id = int(get_jwt_identity())`。
7. **Blueprint 注册不重复前缀**:定义不带 `url_prefix`,注册时统一加 `/api/<module>`。
8. **PUT/PATCH 字段更新**:用 `'key' in body` 而非 `body.get()`,避免 0/null 静默丢弃。

---

## 1. 项目与批次

### 1.1 项目（无 DELETE）

---

#### GET /api/projects

**说明**：项目列表，支持多条件过滤与分页
**Auth**：Bearer access token（任意已登录用户）

**Query Params**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `product_type` | string | 否 | 枚举：`SUS_VC` / `CU_VC` / `HP` |
| `status` | string | 否 | 枚举：`active` / `closed` / `cancelled` |
| `owner_id` | int | 否 | 按项目负责人 ID 过滤 |
| `keyword` | string | 否 | 模糊匹配 `project_code` 或 `project_name` |
| `page` | int | 否 | 默认 1 |
| `per_page` | int | 否 | 默认 20，上限 100 |

**响应 200**
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "items": [
      {
        "id": 1,
        "project_code": "SUS01",
        "project_name": "SUS VC 2026 Q1",
        "product_type": "SUS_VC",
        "project_owner_id": 3,
        "owner_name": "张三",
        "status": "active",
        "created_at": "2026-05-11T09:00:00+08:00",
        "updated_at": "2026-05-11T09:00:00+08:00",
        "version": 0
      }
    ],
    "total": 50,
    "page": 1,
    "per_page": 20
  }
}
```

---

#### POST /api/projects

**说明**：新建项目（`project_code` 由用户指定，后端做格式与唯一性校验）
**Auth**：Bearer access token（`@require_role: super_admin, pm`）

**请求体**
```json
{
  "project_code": "SUS01",
  "project_name": "SUS VC 2026 Q1",
  "product_type": "SUS_VC",
  "project_owner_id": 3
}
```

| 字段 | 类型 | 必填 | 约束 |
|------|------|------|------|
| `project_code` | string | 是 | 格式 `^[A-Z]{2,6}$`，系统全局唯一 |
| `project_name` | string | 是 | maxLength=100 |
| `product_type` | string | 是 | 枚举：`SUS_VC` / `CU_VC` / `HP` |
| `project_owner_id` | int | 是 | 必须是存在且 `is_active=TRUE` 的用户 |

**响应 201**
```json
{
  "code": 201,
  "message": "success",
  "data": {
    "id": 1,
    "project_code": "SUS01",
    "project_name": "SUS VC 2026 Q1",
    "product_type": "SUS_VC",
    "project_owner_id": 3,
    "owner_name": "张三",
    "status": "active",
    "cancelled_reason": null,
    "cancelled_at": null,
    "cancelled_by": null,
    "created_by": 1,
    "created_at": "2026-05-11T09:00:00+08:00",
    "updated_at": "2026-05-11T09:00:00+08:00",
    "version": 0
  }
}
```

**错误响应**

| HTTP | message |
|------|---------|
| 400 | project_code 格式不合规（须匹配 `^[A-Z]{2,6}$`） |
| 400 | project_name 不得为空 |
| 400 | product_type 非法值 |
| 404 | project_owner_id 对应用户不存在或已停用 |
| 409 | project_code 已存在 |

---

#### GET /api/projects/:id

**说明**：项目详情，含挂载批次摘要
**Auth**：Bearer access token（任意已登录用户）

**响应 200**
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "id": 1,
    "project_code": "SUS01",
    "project_name": "SUS VC 2026 Q1",
    "product_type": "SUS_VC",
    "project_owner_id": 3,
    "owner_name": "张三",
    "status": "active",
    "cancelled_reason": null,
    "cancelled_at": null,
    "cancelled_by": null,
    "created_by": 1,
    "created_at": "2026-05-11T09:00:00+08:00",
    "updated_at": "2026-05-11T09:00:00+08:00",
    "version": 2,
    "batches": [
      {
        "id": 10,
        "batch_no": "B001",
        "batch_type": "manual_init",
        "status": "active",
        "created_at": "2026-05-11T10:00:00+08:00"
      }
    ]
  }
}
```

**错误响应**

| HTTP | message |
|------|---------|
| 404 | 项目不存在 |

---

#### PUT /api/projects/:id

**说明**：编辑项目信息（字段更新用 `'key' in body` 判断，见 CLAUDE.md §d Rule 5）
**Auth**：Bearer access token（`@require_role: super_admin, pm`）

**请求体**（所有业务字段可选，`version` 必填）
```json
{
  "project_name": "SUS VC 2026 Q2",
  "product_type": "SUS_VC",
  "project_owner_id": 5,
  "version": 2
}
```

| 字段 | 类型 | 必填 | 约束 |
|------|------|------|------|
| `project_name` | string | 否 | maxLength=100，不得为空字符串 |
| `product_type` | string | 否 | 枚举：`SUS_VC` / `CU_VC` / `HP` |
| `project_owner_id` | int | 否 | 必须是存在且 `is_active=TRUE` 的用户 |
| `version` | int | **是** | 乐观锁版本号 |

**响应 200**
```json
{
  "code": 200,
  "message": "success",
  "data": { "（ProjectDetail 全字段，version 已递增）": "..." }
}
```

**错误响应**

| HTTP | message |
|------|---------|
| 400 | version 为必填项 |
| 400 | project_name 不得为空字符串 |
| 404 | 项目不存在 |
| 409 | 数据已被其他请求修改，请刷新后重试（data: { server_version, your_version }） |

---

#### PATCH /api/projects/:id/cancel

**说明**：作废项目（status → cancelled，不可逆，无 DELETE 端点）
**Auth**：Bearer access token（`@require_role: super_admin, pm`）

**请求体**
```json
{ "reason": "项目终止，产品停产", "version": 2 }
```

| 字段 | 类型 | 必填 | 约束 |
|------|------|------|------|
| `reason` | string | 是 | 作废理由，不得为空 |
| `version` | int | 是 | 乐观锁版本号 |

**响应 200**
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "id": 1,
    "status": "cancelled",
    "cancelled_reason": "项目终止，产品停产",
    "cancelled_at": "2026-05-11T14:00:00+08:00",
    "cancelled_by": 1,
    "version": 3
  }
}
```

**错误响应**

| HTTP | message |
|------|---------|
| 400 | reason 不得为空 |
| 400 | version 为必填项 |
| 404 | 项目不存在 |
| 409 | 数据已被其他请求修改，请刷新后重试 |
| 422 | 项目已处于 cancelled 状态 |

---

#### PUT /api/projects/:id/owner

**说明**：转移项目负责人（高权操作，仅超管可执行）
**Auth**：Bearer access token（`@require_role: super_admin`）

**请求体**
```json
{ "new_owner_id": 5, "version": 2 }
```

| 字段 | 类型 | 必填 | 约束 |
|------|------|------|------|
| `new_owner_id` | int | 是 | 必须是存在且 `is_active=TRUE` 的用户 |
| `version` | int | 是 | 乐观锁版本号 |

**响应 200**
```json
{
  "code": 200,
  "message": "success",
  "data": { "id": 1, "project_owner_id": 5, "owner_name": "李四", "version": 3 }
}
```

**错误响应**

| HTTP | message |
|------|---------|
| 400 | new_owner_id 为必填项 |
| 404 | new_owner_id 对应用户不存在或已停用 |
| 404 | 项目不存在 |
| 409 | 数据已被其他请求修改，请刷新后重试 |

---

#### GET /api/projects/:id/gantt

**说明**：项目甘特图数据，可按 batch_id 下钻
**Auth**：Bearer access token（任意已登录用户）

**Query Params**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `batch_id` | int | 否 | 按批次 ID 下钻过滤 |

**响应 200**
```json
{
  "code": 200,
  "message": "success",
  "data": { "project_id": 1, "batches": [] }
}
```

**错误响应**

| HTTP | message |
|------|---------|
| 404 | 项目不存在 |

> ⚠️ Phase 1 仅返回占位数据结构（`batches: []`），完整甘特图数据依赖 Phase 2 治具节点，实现待 Phase 2。

---

#### POST /api/projects/:id/sync-templates

**说明**：对比当前模板库与项目快照，仅追加新增模板（不覆盖、不删除已有快照）；操作写审计日志
**Auth**：Bearer access token（`@require_role: super_admin`）

**请求体**：无

**响应 200**
```json
{
  "code": 200,
  "message": "success",
  "data": { "synced_count": 3, "message": "已追加 3 条新模板快照" }
}
```

**错误响应**

| HTTP | message |
|------|---------|
| 404 | 项目不存在 |

> ⚠️ Phase 1 仅写 spec 草案，实现在 Step 1-2-2。

---

#### GET /api/projects/export

**说明**：项目列表导出（xlsx 格式）
**Auth**：Bearer access token（任意已登录用户）

> ⚠️ Flask 路由注册时须将此端点置于 `GET /api/projects/<int:id>` **之前**，避免字符串 "export" 被误作整数 ID 匹配。

**Query Params**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `ids` | string | 否 | 逗号分隔的 project id 列表 |
| `product_type` | string | 否 | 同列表过滤参数 |
| `status` | string | 否 | 同列表过滤参数 |
| `format` | string | 否 | 固定为 `xlsx` |

**响应**：流式 xlsx 文件
- `Content-Type: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`
- `Content-Disposition: attachment; filename="projects_export.xlsx"`

**错误响应**

| HTTP | message |
|------|---------|
| 400 | format 仅支持 xlsx |

> ⚠️ 按 Doc/07_export_guideline.md 三档策略：行数 < 1000 时前端 SheetJS 自行生成，本端点仅服务多表关联或 > 1000 行场景，实现待 Phase 6。

---

### 1.2 批次（无 DELETE）

#### batch_type 枚举

| 枚举值 | 含义 |
|--------|------|
| `manual_init` | 手工版初版批次（最初开模需求） |
| `mass_prod` | 量产转产批次（正式量产立项） |
| `addon_quantity` | 加开-加量批次（套数补充，复制图纸） |
| `addon_optimize` | 加开-优化批次（改版优化，复制结构） |

---

#### GET /api/batches

**说明**：批次列表，支持按项目 / 批次类型 / 状态过滤与分页
**Auth**：Bearer access token（任意已登录用户）

**Query Params**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `project_id` | int | 否 | 按项目 ID 过滤 |
| `batch_type` | string | 否 | 枚举：见 batch_type 枚举表 |
| `status` | string | 否 | 枚举：`draft` / `active` / `sealed` / `cancelled` |
| `page` | int | 否 | 默认 1 |
| `per_page` | int | 否 | 默认 20，上限 100 |

**响应 200**
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "items": [
      {
        "id": 10,
        "project_id": 1,
        "batch_no": "SUS01-M0-1",
        "batch_type": "manual_init",
        "flow_path": "full",
        "status": "draft",
        "expected_date": "2026-12-31",
        "remark": "首批开模",
        "created_by": 1,
        "created_at": "2026-05-14T09:00:00+08:00",
        "updated_at": "2026-05-14T09:00:00+08:00",
        "version": 0
      }
    ],
    "total": 5,
    "page": 1,
    "per_page": 20
  }
}
```

---

#### POST /api/batches

**说明**：在项目下新建需求批次
**Auth**：Bearer access token（`@require_role: super_admin, pm`）

**请求体**
```json
{
  "project_id": 1,
  "batch_type": "manual_init",
  "expected_date": "2026-12-31",
  "remark": "首批开模"
}
```

| 字段 | 类型 | 必填 | 约束 |
|------|------|------|------|
| `project_id` | int | 是 | 对应存在的项目 |
| `batch_type` | string | 是 | 枚举，见上表 |
| `parent_batch_id` | int | 条件必填 | addon 类型必填，manual_init / mass_prod 不允许传 |
| `flow_path` | string | 否 | `full`（默认）或 `simplified`；manual_init / mass_prod 强制为 `full` |
| `expected_date` | string | 否 | 格式 `YYYY-MM-DD` |
| `remark` | string | 否 | 备注 |

> ⚠️ `batch_no` 由后端自动生成（格式 `{project_code}-{batch_type_short}-{seq}`），**不允许**请求体传入。

**响应 201**
```json
{
  "code": 201,
  "message": "success",
  "data": {
    "id": 10,
    "project_id": 1,
    "project_code": "SUS01",
    "batch_no": "SUS01-M0-1",
    "batch_type": "manual_init",
    "parent_batch_id": null,
    "flow_path": "full",
    "status": "draft",
    "expected_date": "2026-12-31",
    "cancelled_reason": null,
    "cancelled_at": null,
    "cancelled_by": null,
    "remark": "首批开模",
    "created_by": 1,
    "created_at": "2026-05-14T09:00:00+08:00",
    "updated_at": "2026-05-14T09:00:00+08:00",
    "version": 0,
    "fixture_count": 0
  }
}
```

> ⚠️ `mass_prod` 批次创建成功后，响应体额外包含 `"urgency_flag": true`（Phase 6 邮件告警接入前仅返回字段，不发邮件）。

**错误响应**

| HTTP | message |
|------|---------|
| 400 | project_id 为必填项 |
| 400 | batch_type 非法值 |
| 404 | project_id 对应项目不存在 |
| 409 | 同项目下 batch_no 已存在 |
| 422 | 项目已处于 cancelled 状态，不可新建批次 |

---

#### GET /api/batches/:id

**说明**：批次详情
**Auth**：Bearer access token（任意已登录用户）

**响应 200**
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "id": 10,
    "project_id": 1,
    "project_code": "SUS01",
    "batch_no": "SUS01-M0-1",
    "batch_type": "manual_init",
    "parent_batch_id": null,
    "flow_path": "full",
    "status": "draft",
    "expected_date": "2026-12-31",
    "cancelled_reason": null,
    "cancelled_at": null,
    "cancelled_by": null,
    "remark": "首批开模",
    "created_by": 1,
    "created_at": "2026-05-14T09:00:00+08:00",
    "updated_at": "2026-05-14T09:00:00+08:00",
    "version": 2,
    "fixture_count": 0
  }
}
```

> ⚠️ `fixture_count` 在 Phase 1 固定返回 0，实际治具数量待 Phase 2 实现。

**错误响应**

| HTTP | message |
|------|---------|
| 404 | 批次不存在 |

---

#### PUT /api/batches/:id

**说明**：编辑批次信息（字段更新用 `'key' in body` 判断）
**Auth**：Bearer access token（`@require_role: super_admin, pm`）

**请求体**（所有业务字段可选，`version` 必填）
```json
{
  "expected_date": "2026-09-30",
  "flow_path": "simplified",
  "remark": "更新备注",
  "version": 2
}
```

| 字段 | 类型 | 必填 | 约束 |
|------|------|------|------|
| `expected_date` | string | 否 | 格式 `YYYY-MM-DD` |
| `flow_path` | string | 否 | `full` 或 `simplified` |
| `remark` | string | 否 | 备注 |
| `version` | int | **是** | 乐观锁版本号 |

> ⚠️ `batch_no` 和 `batch_type` 创建后不可修改（auto-generated）。

**响应 200**
```json
{
  "code": 200,
  "message": "success",
  "data": { "（BatchDetail 全字段，version 已递增）": "..." }
}
```

**错误响应**

| HTTP | message |
|------|---------|
| 400 | version 为必填项 |
| 404 | 批次不存在 |
| 409 | 数据已被其他请求修改，请刷新后重试 |
| 422 | 已封存的批次不可编辑 |
| 422 | 已 cancelled 的批次不可编辑 |

---

#### PATCH /api/batches/:id/cancel

**说明**：作废批次（status → cancelled，不可逆，无 DELETE 端点）
**Auth**：Bearer access token（`@require_role: super_admin, pm`）

**请求体**
```json
{ "reason": "需求变更，批次作废", "version": 2 }
```

| 字段 | 类型 | 必填 | 约束 |
|------|------|------|------|
| `reason` | string | 是 | 作废理由，不得为空 |
| `version` | int | 是 | 乐观锁版本号 |

**响应 200**
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "id": 10,
    "status": "cancelled",
    "cancelled_reason": "需求变更，批次作废",
    "cancelled_at": "2026-05-11T14:00:00+08:00",
    "cancelled_by": 1,
    "version": 3
  }
}
```

**错误响应**

| HTTP | message |
|------|---------|
| 400 | reason 不得为空 |
| 400 | version 为必填项 |
| 404 | 批次不存在 |
| 409 | 数据已被其他请求修改，请刷新后重试 |
| 422 | 批次已处于 cancelled 状态 |

---

#### GET /api/batches/:id/fixtures

**说明**：批次下的治具清单（分页）
**Auth**：Bearer access token（任意已登录用户）

**Query Params**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `page` | int | 否 | 默认 1 |
| `per_page` | int | 否 | 默认 20 |

**响应 200**
```json
{
  "code": 200,
  "message": "success",
  "data": { "items": [], "total": 0, "page": 1, "per_page": 20 }
}
```

**错误响应**

| HTTP | message |
|------|---------|
| 404 | 批次不存在 |

> ⚠️ Phase 1 固定返回空列表，实际治具数据待 Phase 2。

---

#### GET /api/batches/:id/gantt

**说明**：批次甘特图数据
**Auth**：Bearer access token（任意已登录用户）

**响应 200**
```json
{
  "code": 200,
  "message": "success",
  "data": { "batch_id": 10, "fixtures": [] }
}
```

**错误响应**

| HTTP | message |
|------|---------|
| 404 | 批次不存在 |

> ⚠️ Phase 1 仅返回占位结构，完整实现待 Phase 2。

---

#### PATCH /api/batches/:id/seal（草案）

**说明**：封存批次（量产投产后将手工版批次封存）
**Auth**：Bearer access token（`@require_role: super_admin, warehouse`）

**请求体**
```json
{ "version": 2 }
```

| 字段 | 类型 | 必填 | 约束 |
|------|------|------|------|
| `version` | int | 是 | 乐观锁版本号 |

**响应 200**
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "id": 10,
    "status": "sealed",
    "sealed_at": "2026-05-11T14:00:00+08:00",
    "sealed_by": 1,
    "version": 3
  }
}
```

**错误响应**

| HTTP | message |
|------|---------|
| 400 | version 为必填项 |
| 404 | 批次不存在 |
| 409 | 数据已被其他请求修改，请刷新后重试 |
| 422 | 批次已处于封存状态 |
| 422 | 批次已处于 cancelled 状态 |

> ⚠️ Phase 1 spec 草案；seal 核心逻辑（批量更新 fixtures.is_sealed）待 **Phase 2** 实现（fixtures 表建立后）。封存业务规则与状态字段设计详见 `Doc/03_architecture_v1.4.md` §3.3.x。

---

#### PATCH /api/batches/:id/unseal（草案）

**说明**：解封批次（Phase 1 暂仅 super_admin 可操作；Phase 4 扩展为 PM + 生产主管会签审批流）
**Auth**：Bearer access token（`@require_role: super_admin`）

**请求体**
```json
{ "reason": "生产需求临时解封", "version": 3 }
```

| 字段 | 类型 | 必填 | 约束 |
|------|------|------|------|
| `reason` | string | 是 | 解封理由，不得为空 |
| `version` | int | 是 | 乐观锁版本号 |

**响应 200**
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "id": 10,
    "status": "active",
    "sealed_at": null,
    "sealed_by": null,
    "version": 4
  }
}
```

**错误响应**

| HTTP | message |
|------|---------|
| 400 | reason 不得为空 |
| 400 | version 为必填项 |
| 404 | 批次不存在 |
| 409 | 数据已被其他请求修改，请刷新后重试 |
| 422 | 批次未处于封存状态 |

> ⚠️ Phase 1 spec 草案；Phase 4 扩展为 PM + 生产主管会签审批流（复用 §3.4 sequential 引擎），届时更新本条目。详见 `Doc/03_architecture_v1.4.md` §3.3.x。

---

## 2. 模治具核心

> 作废走状态机 SCRAPPED,无 DELETE。

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/fixtures` | 新建治具(在批次下创建,系统按编码规则生成 fixture_code) |
| GET | `/api/fixtures` | 治具列表(支持按项目/批次/状态/编码模糊搜索) |
| GET | `/api/fixtures/:id` | 治具详情 |
| PUT | `/api/fixtures/:id` | 编辑治具基本信息(含 version 字段) |
| PATCH | `/api/fixtures/:id/status` | 状态流转(走严格 TRANSITIONS,通过 trigger 字段区分场景) |
| POST | `/api/fixtures/:id/version-bump` | 图纸版本升级(A1→A2、A3→B1 等,不新建 fixture) |
| POST | `/api/fixtures/:id/copy-to-batch` | 加开-复制图纸(生成新 fixture,parent_fixture_id 溯源,套号递增) |
| POST | `/api/fixtures/batch-seal` | 批量封存(量产投产后将同项目手动版批次治具批量更新) |
| POST | `/api/fixtures/:id/release-seal` | 解封(经 PM+生产主管审批) |
| POST | `/api/fixtures/:id/force-status` | 超管强制跳转(必填 reason,自动审计) |
| POST | `/api/fixtures/:id/recalc-dates` | 重算后续节点计划日期 |
| GET | `/api/fixtures/export?...&format=xlsx` | ★ 治具列表导出 |

### `PATCH /api/fixtures/:id/status` 的 trigger 取值参考

涵盖所有合法状态流转触发器(详见 [docs/03_architecture_v1.4.md](./03_architecture_v1.4.md) 第 3.3 节 TRANSITIONS):

| trigger | 含义 |
|---------|------|
| `normal` | 标准流转(如 EMERGENCY_PENDING → INSTALLING、INSTALLING → ACCEPTANCE_TESTING) |
| `emergency_auth` | IQC 紧急上机授权 |
| `iqc_pass` | IQC 检验合格 |
| `concession_approved` | 让步接受三方审批通过 |
| `return_repair` | 退厂返修 / 审批驳回回退 |
| `acceptance_pass` | 试产验收合格 |
| `rework` | 试产不合格回退到安装阶段 |
| `acceptance_fail_scrap` | 试产不合格直接报废 |
| `checkout` / `return` | 生产领用 / 归还 |
| `seal` / `release_seal` | 封存 / 解封 |
| `maintenance_due` | 触发保养 |
| `repair_request` | 报修 |
| `scrap` | 报废 |

---

## 3. 流程节点 — 业务单据（扁平化资源，无 DELETE）

> 所有业务单据均为扁平化资源，通过 body 中的 `fixture_id` 关联治具。状态变更与单据 POST 解耦，业务层按顺序分别调用 `PATCH /api/fixtures/:id/status`（见 §2）。是否维持解耦见 Q-011。

---

### POST /api/drawings

**说明**：设计工程师提交图纸或 DFM 报告（multipart/form-data）。每次上传建一条记录，`drawing_type` 区分类型。
**Auth**：`@require_role: super_admin, design_engineer`

**请求体字段（multipart/form-data）**

| 字段 | 类型 | 必填 | 约束 |
|------|------|------|------|
| `fixture_id` | int | 是 | 关联治具 ID |
| `version_code` | string | 是 | 图纸版本号，如 "A1"，与 fixture.current_version_code 一致 |
| `drawing_type` | string | 是 | 枚举：`design_drawing` / `dfm_report` |
| `file` | file | 是 | multipart，后端落盘 uploads/drawings/，存相对路径 |
| `acceptance_standard` | string | 否 | 关键尺寸 / 验收标准（主要用于 design_drawing） |
| `bom_info` | string | 否 | BOM 信息（主要用于 design_drawing） |
| `is_copied` | boolean | 否 | 是否复制既有图纸（默认 false） |
| `source_drawing_id` | int | 否 | 复制来源图纸 ID（is_copied=true 时填写） |

**响应 201**
```json
{
  "code": 201,
  "message": "success",
  "data": {
    "id": 1,
    "fixture_id": 10,
    "version_code": "A1",
    "drawing_type": "design_drawing",
    "file_path": "drawings/2026/05/xxx.pdf",
    "acceptance_standard": null,
    "bom_info": null,
    "is_copied": false,
    "source_drawing_id": null,
    "uploaded_by": 3,
    "confirmed_by": null,
    "confirmed_at": null,
    "created_at": "2026-05-17T09:00:00+08:00"
  }
}
```

**错误响应**

| HTTP | message |
|------|---------|
| 400 | fixture_id / version_code / drawing_type / file 均为必填项 |
| 400 | drawing_type 枚举值非法（允许值：design_drawing / dfm_report） |
| 404 | 治具不存在 |

---

### GET /api/drawings

**说明**：查询治具的图纸/DFM 列表
**Auth**：`@require_role: super_admin, design_engineer, pm, me, iqc`

**查询参数**：`fixture_id` (int, 必填)

**响应 200**
```json
{
  "code": 200,
  "message": "success",
  "data": [
    {
      "id": 1,
      "fixture_id": 10,
      "version_code": "A1",
      "drawing_type": "design_drawing",
      "file_path": "drawings/2026/05/xxx.pdf",
      "acceptance_standard": null,
      "bom_info": null,
      "is_copied": false,
      "source_drawing_id": null,
      "uploaded_by": 3,
      "confirmed_by": null,
      "confirmed_at": null,
      "created_at": "2026-05-17T09:00:00+08:00"
    }
  ]
}
```

---

### PATCH /api/drawings/:id/confirm

**说明**：PM 确认图纸（仅写 confirmed_by / confirmed_at，不改其他字段）
**Auth**：`@require_role: super_admin, pm`

**请求体**：无（由 JWT identity 自动取 confirmed_by）

**响应 200**
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "id": 1,
    "confirmed_by": 2,
    "confirmed_at": "2026-05-17T10:00:00+08:00"
  }
}
```

**错误响应**

| HTTP | message |
|------|---------|
| 404 | 图纸记录不存在 |
| 409 | 图纸已被确认 |

---

### POST /api/purchase-requisitions

**说明**：设计工程师或 PM 提交采购申请单（需求侧），供应商由采购部门在 PO 阶段选定。
**Auth**：`@require_role: super_admin, design_engineer, pm`

**请求体字段**

| 字段 | 类型 | 必填 | 约束 |
|------|------|------|------|
| `fixture_id` | int | 是 | 关联治具 ID |
| `drawing_id` | int | 否 | 关联图纸 ID（选填） |
| `quantity` | int | 是 | 申请数量，≥ 1 |
| `spec_note` | string | 否 | 规格说明 / 技术要求 |
| `required_date` | string | 否 | 要求到货日期（ISO 8601 日期） |

**响应 201**
```json
{
  "code": 201,
  "message": "success",
  "data": {
    "id": 1,
    "fixture_id": 10,
    "requisition_no": "PR-20260517-0001",
    "drawing_id": null,
    "quantity": 2,
    "spec_note": null,
    "required_date": "2026-06-15",
    "confirm_status": "pending",
    "created_by": 3,
    "confirmed_by": null,
    "confirmed_at": null,
    "created_at": "2026-05-17T09:00:00+08:00"
  }
}
```

**错误响应**

| HTTP | message |
|------|---------|
| 400 | fixture_id / quantity 均为必填项 |
| 400 | quantity 须 ≥ 1 |
| 404 | 治具不存在 / 图纸不存在 |

---

### GET /api/purchase-requisitions

**说明**：查询治具的采购申请单列表
**Auth**：`@require_role: super_admin, design_engineer, pm, purchaser`

**查询参数**：`fixture_id` (int, 必填)

**响应 200**
```json
{
  "code": 200,
  "message": "success",
  "data": [
    {
      "id": 1,
      "fixture_id": 10,
      "requisition_no": "PR-20260517-0001",
      "drawing_id": null,
      "quantity": 2,
      "spec_note": null,
      "required_date": "2026-06-15",
      "confirm_status": "pending",
      "created_by": 3,
      "confirmed_by": null,
      "confirmed_at": null,
      "created_at": "2026-05-17T09:00:00+08:00"
    }
  ]
}
```

---

### PATCH /api/purchase-requisitions/:id/confirm

**说明**：PM 确认采购申请单（写 confirm_status='confirmed' + confirmed_by/at）
**Auth**：`@require_role: super_admin, pm`

**请求体**：无

**响应 200**
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "id": 1,
    "confirm_status": "confirmed",
    "confirmed_by": 2,
    "confirmed_at": "2026-05-17T10:00:00+08:00"
  }
}
```

**错误响应**

| HTTP | message |
|------|---------|
| 404 | 采购申请单不存在 |
| 409 | 申请单已被确认 |

---

### POST /api/goods-receipts

**说明**：仓库管理员到货签收
**Auth**：`@require_role: super_admin, warehouse`

**请求体字段**

| 字段 | 类型 | 必填 | 约束 |
|------|------|------|------|
| `fixture_id` | int | 是 | 关联治具 ID |
| `purchase_order_id` | int | 否 | 关联 PO ID |
| `actual_arrival_date` | string | 是 | ISO 8601 日期时间 |
| `received_by` | int | 是 | 签收人 user_id（一般为当前用户） |
| `remark` | string | 否 | |

**响应 201**
```json
{
  "code": 201,
  "message": "success",
  "data": {
    "id": 1,
    "fixture_id": 10,
    "actual_arrival_date": "2026-05-17T14:00:00+08:00",
    "received_by": 6,
    "created_at": "2026-05-17T14:05:00+08:00"
  }
}
```

**错误响应**

| HTTP | message |
|------|---------|
| 400 | fixture_id / actual_arrival_date / received_by 均为必填项 |
| 404 | 治具不存在 |

> 注：到货签收动作同步驱动 `PATCH /api/fixtures/:id/status`（trigger=`normal`，状态 → `pending_iqc`），二者解耦，业务层按顺序调用。

---

### POST /api/iqc-reports

**说明**：IQC 检验员录入检验结果
**Auth**：`@require_role: super_admin, iqc`

**请求体字段（multipart/form-data）**

| 字段 | 类型 | 必填 | 约束 |
|------|------|------|------|
| `fixture_id` | int | 是 | 关联治具 ID |
| `result` | string | 是 | 枚举：`pass` / `fail` / `concession` |
| `inspector_id` | int | 是 | 检验员 user_id |
| `inspection_date` | string | 是 | ISO 8601 日期时间 |
| `defect_description` | string | 否 | result=fail 时建议填写 |
| `file` | file | 否 | multipart，检验报告附件 |
| `remark` | string | 否 | |

**响应 201**
```json
{
  "code": 201,
  "message": "success",
  "data": {
    "id": 1,
    "fixture_id": 10,
    "result": "pass",
    "inspector_id": 5,
    "inspection_date": "2026-05-17T10:00:00+08:00",
    "file_path": "iqc/2026/05/xxx.pdf",
    "created_at": "2026-05-17T10:05:00+08:00"
  }
}
```

**错误响应**

| HTTP | message |
|------|---------|
| 400 | fixture_id / result / inspector_id / inspection_date 均为必填项 |
| 400 | result 枚举值非法（允许值：pass / fail / concession） |
| 404 | 治具不存在 |

---

### POST /api/emergency-auth-records

**说明**：紧急上机授权单（IQC 不合格但经 PM + IQC 双方授权上机）
**Auth**：`@require_role: super_admin, pm, iqc`

**请求体字段**

| 字段 | 类型 | 必填 | 约束 |
|------|------|------|------|
| `fixture_id` | int | 是 | 关联治具 ID |
| `iqc_report_id` | int | 是 | 关联 IQC 报告 ID |
| `authorized_by_pm` | int | 是 | PM user_id |
| `authorized_by_iqc` | int | 是 | IQC user_id |
| `authorization_date` | string | 是 | ISO 8601 日期时间 |
| `risk_description` | string | 是 | 风险说明，不得为空 |
| `remark` | string | 否 | |

**响应 201**
```json
{
  "code": 201,
  "message": "success",
  "data": {
    "id": 1,
    "fixture_id": 10,
    "iqc_report_id": 3,
    "authorized_by_pm": 1,
    "authorized_by_iqc": 5,
    "authorization_date": "2026-05-17T11:00:00+08:00",
    "created_at": "2026-05-17T11:05:00+08:00"
  }
}
```

**错误响应**

| HTTP | message |
|------|---------|
| 400 | 所有必填字段缺失 |
| 400 | risk_description 不得为空 |
| 404 | 治具 / IQC 报告不存在 |

---

### POST /api/install-records

**说明**：ME 工程师录入安装调试记录
**Auth**：`@require_role: super_admin, me`

**请求体字段（multipart/form-data）**

| 字段 | 类型 | 必填 | 约束 |
|------|------|------|------|
| `fixture_id` | int | 是 | 关联治具 ID |
| `installer_id` | int | 是 | 安装者 user_id |
| `install_date` | string | 是 | ISO 8601 日期时间 |
| `equipment_code` | string | 否 | 对应设备代号（YN/DZ2X 等） |
| `install_note` | string | 否 | 安装要点 |
| `file` | file | 否 | multipart，安装记录附件 |

**响应 201**
```json
{
  "code": 201,
  "message": "success",
  "data": {
    "id": 1,
    "fixture_id": 10,
    "installer_id": 4,
    "install_date": "2026-05-17T13:00:00+08:00",
    "equipment_code": "YN",
    "created_at": "2026-05-17T13:05:00+08:00"
  }
}
```

**错误响应**

| HTTP | message |
|------|---------|
| 400 | fixture_id / installer_id / install_date 均为必填项 |
| 404 | 治具不存在 |

---

### POST /api/acceptance-reports

**说明**：IQC/ME/设计工程师录入试产验收结果
**Auth**：`@require_role: super_admin, iqc, me, design_engineer`

**请求体字段（multipart/form-data）**

| 字段 | 类型 | 必填 | 约束 |
|------|------|------|------|
| `fixture_id` | int | 是 | 关联治具 ID |
| `result` | string | 是 | 枚举：`pass` / `fail_rework` / `fail_scrap` |
| `inspector_id` | int | 是 | 验收人 user_id |
| `acceptance_date` | string | 是 | ISO 8601 日期时间 |
| `defect_description` | string | 否 | result 非 pass 时建议填写 |
| `file` | file | 否 | multipart，验收报告 |
| `remark` | string | 否 | |

**响应 201**
```json
{
  "code": 201,
  "message": "success",
  "data": {
    "id": 1,
    "fixture_id": 10,
    "result": "pass",
    "inspector_id": 5,
    "acceptance_date": "2026-05-17T15:00:00+08:00",
    "created_at": "2026-05-17T15:05:00+08:00"
  }
}
```

**错误响应**

| HTTP | message |
|------|---------|
| 400 | fixture_id / result / inspector_id / acceptance_date 均为必填项 |
| 400 | result 枚举值非法（允许值：pass / fail_rework / fail_scrap） |
| 404 | 治具不存在 |

---

### POST /api/handover-records

**说明**：仓库管理员移交确认（验收合格后治具移交入库）
**Auth**：`@require_role: super_admin, warehouse`

**请求体字段**

| 字段 | 类型 | 必填 | 约束 |
|------|------|------|------|
| `fixture_id` | int | 是 | 关联治具 ID |
| `handover_from` | int | 是 | 移交方 user_id（通常为 ME） |
| `handover_to` | int | 是 | 接收方 user_id（通常为仓库） |
| `handover_date` | string | 是 | ISO 8601 日期时间 |
| `shelf_location` | string | 否 | 货架/库位编号（Q-013 待确认是否必填） |
| `remark` | string | 否 | |

**响应 201**
```json
{
  "code": 201,
  "message": "success",
  "data": {
    "id": 1,
    "fixture_id": 10,
    "handover_from": 4,
    "handover_to": 6,
    "handover_date": "2026-05-17T16:00:00+08:00",
    "shelf_location": "A-03-02",
    "created_at": "2026-05-17T16:05:00+08:00"
  }
}
```

**错误响应**

| HTTP | message |
|------|---------|
| 400 | fixture_id / handover_from / handover_to / handover_date 均为必填项 |
| 404 | 治具不存在 |

> ⚠️ 移交确认是否同步触发状态机流转，见 Q-010（待确认）。本 spec 暂定：移交确认仅作业务单据，状态流转（`acceptance_pass` trigger）由前端/业务层单独调用 `PATCH /api/fixtures/:id/status`。

---

### POST /api/checkout-records

**说明**：生产班长发起领用 / 归还记录
**Auth**：`@require_role: super_admin, production_lead`

**请求体字段**

| 字段 | 类型 | 必填 | 约束 |
|------|------|------|------|
| `fixture_id` | int | 是 | 关联治具 ID |
| `action` | string | 是 | 枚举：`checkout` / `return` |
| `operator_id` | int | 是 | 操作者 user_id |
| `action_date` | string | 是 | ISO 8601 日期时间 |
| `production_line` | string | 否 | 领用目标产线 |
| `remark` | string | 否 | |

**响应 201**
```json
{
  "code": 201,
  "message": "success",
  "data": {
    "id": 1,
    "fixture_id": 10,
    "action": "checkout",
    "operator_id": 7,
    "action_date": "2026-05-17T08:00:00+08:00",
    "created_at": "2026-05-17T08:01:00+08:00"
  }
}
```

**错误响应**

| HTTP | message |
|------|---------|
| 400 | fixture_id / action / operator_id / action_date 均为必填项 |
| 400 | action 枚举值非法（允许值：checkout / return） |
| 404 | 治具不存在 |

> 注：领用/归还动作同步驱动 `PATCH /api/fixtures/:id/status`（trigger=`checkout`/`return`），二者解耦，业务层按顺序调用。

---

### POST /api/maintenance-records

**说明**：ME 工程师录入保养执行记录
**Auth**：`@require_role: super_admin, me`

**请求体字段（multipart/form-data）**

| 字段 | 类型 | 必填 | 约束 |
|------|------|------|------|
| `fixture_id` | int | 是 | 关联治具 ID |
| `maintainer_id` | int | 是 | 保养执行者 user_id |
| `maintenance_date` | string | 是 | ISO 8601 日期时间 |
| `maintenance_type` | string | 是 | 枚举：`routine` / `corrective` |
| `maintenance_note` | string | 否 | 保养内容描述 |
| `next_maintenance_date` | string | 否 | 下次保养计划日期 |
| `file` | file | 否 | multipart，保养记录附件 |

**响应 201**
```json
{
  "code": 201,
  "message": "success",
  "data": {
    "id": 1,
    "fixture_id": 10,
    "maintainer_id": 4,
    "maintenance_date": "2026-05-17T09:00:00+08:00",
    "maintenance_type": "routine",
    "created_at": "2026-05-17T09:05:00+08:00"
  }
}
```

**错误响应**

| HTTP | message |
|------|---------|
| 400 | fixture_id / maintainer_id / maintenance_date / maintenance_type 均为必填项 |
| 400 | maintenance_type 枚举值非法（允许值：routine / corrective） |
| 404 | 治具不存在 |

---

### POST /api/repair-records

**说明**：ME 工程师录入维修记录（含费用）
**Auth**：`@require_role: super_admin, me`

**请求体字段（multipart/form-data）**

| 字段 | 类型 | 必填 | 约束 |
|------|------|------|------|
| `fixture_id` | int | 是 | 关联治具 ID |
| `repairer_id` | int | 是 | 维修执行者 user_id |
| `repair_date` | string | 是 | ISO 8601 日期时间 |
| `repair_cause` | string | 是 | 维修原因描述 |
| `repair_cost` | decimal | 否 | 维修费用（元），权限见成本模块 |
| `file` | file | 否 | multipart，维修记录附件 |
| `remark` | string | 否 | |

**响应 201**
```json
{
  "code": 201,
  "message": "success",
  "data": {
    "id": 1,
    "fixture_id": 10,
    "repairer_id": 4,
    "repair_date": "2026-05-17T10:00:00+08:00",
    "repair_cause": "模具导柱磨损",
    "repair_cost": "350.00",
    "created_at": "2026-05-17T10:05:00+08:00"
  }
}
```

**错误响应**

| HTTP | message |
|------|---------|
| 400 | fixture_id / repairer_id / repair_date / repair_cause 均为必填项 |
| 404 | 治具不存在 |

---

### POST /api/scrap-records

**说明**：PM 发起报废申请
**Auth**：`@require_role: super_admin, pm`

**请求体字段（multipart/form-data）**

| 字段 | 类型 | 必填 | 约束 |
|------|------|------|------|
| `fixture_id` | int | 是 | 关联治具 ID |
| `applicant_id` | int | 是 | 申请人 user_id |
| `scrap_reason` | string | 是 | 报废原因，不得为空 |
| `scrap_date` | string | 是 | ISO 8601 日期 |
| `estimated_salvage_value` | decimal | 否 | 残值估计（元） |
| `file` | file | 否 | multipart，报废申请附件 |

**响应 201**
```json
{
  "code": 201,
  "message": "success",
  "data": {
    "id": 1,
    "fixture_id": 10,
    "applicant_id": 1,
    "scrap_reason": "模具寿命到期无法修复",
    "scrap_date": "2026-05-17",
    "created_at": "2026-05-17T11:00:00+08:00"
  }
}
```

**错误响应**

| HTTP | message |
|------|---------|
| 400 | fixture_id / applicant_id / scrap_reason / scrap_date 均为必填项 |
| 400 | scrap_reason 不得为空 |
| 404 | 治具不存在 |

---

## 4. 审批流

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/approvals` | 发起审批流(含 flow_type、sequential_or_parallel、相关业务单据 ID) |
| GET | `/api/approvals/my-pending` | 待我审批列表 |
| PUT | `/api/approval-steps/:id` | 提交单步审批决策(approved/rejected + 意见 + decision_type) |

**支持的审批场景**(通过 `flow_type` 区分,共用一套引擎):

- IQC 不合格三方审批(PM + 设计 + ME,顺序或并行)
- 让步接受三方审批
- 紧急上机授权(PM + IQC)
- 试产不合格三部门联合评审(开发 + 制技 + 质量)
- 报废三方线上会签(PM + 生产部负责人 + 业务工程师)
- 手动版解封审批(PM + 生产主管)

---

## 5. 仓储与采购

### 5.1 采购订单（无 DELETE，一对多结构：PO 头 + items）

---

#### POST /api/purchase-orders

**说明**：采购专员新建 PO 头
**Auth**：`@require_role: super_admin, purchaser`

**请求体字段**

| 字段 | 类型 | 必填 | 约束 |
|------|------|------|------|
| `fixture_id` | int | 是 | 关联治具 ID（Phase 3：一 PO 一治具） |
| `supplier_id` | int | 是 | 供应商 ID |
| `contract_no` | string | 否 | 合同号 |
| `order_date` | string | 是 | 下单日期 ISO 8601 |
| `planned_delivery_date` | string | 是 | 约定交期 ISO 8601 |
| `total_amount` | decimal | 否 | 合同总金额（元），留空待 items 汇总 |
| `remark` | string | 否 | |

**响应 201**
```json
{
  "code": 201,
  "message": "success",
  "data": {
    "id": 1,
    "fixture_id": 10,
    "supplier_id": 2,
    "contract_no": "PO-2026-001",
    "order_date": "2026-05-17",
    "planned_delivery_date": "2026-06-30",
    "status": "open",
    "created_by": 8,
    "version": 0,
    "created_at": "2026-05-17T09:00:00+08:00"
  }
}
```

**错误响应**

| HTTP | message |
|------|---------|
| 400 | fixture_id / supplier_id / order_date / planned_delivery_date 均为必填项 |
| 404 | 治具不存在 / 供应商不存在 |

> ⚠️ 计划日期推算归属见 Q-012（待确认）。Phase 3 暂只存采购下单日，不自动推算后续节点计划日期。

---

#### POST /api/purchase-orders/:id/items

**说明**：在 PO 下新增明细项
**Auth**：`@require_role: super_admin, purchaser`

**请求体字段**

| 字段 | 类型 | 必填 | 约束 |
|------|------|------|------|
| `item_name` | string | 是 | 明细项描述 |
| `quantity` | int | 是 | 数量，≥ 1 |
| `unit_price` | decimal | 是 | 单价（元） |
| `unit` | string | 否 | 单位，默认"套" |
| `remark` | string | 否 | |

**响应 201**
```json
{
  "code": 201,
  "message": "success",
  "data": {
    "id": 1,
    "purchase_order_id": 1,
    "item_name": "SUS VC 压合治具主体",
    "quantity": 1,
    "unit_price": "8500.00",
    "unit": "套",
    "line_total": "8500.00",
    "created_at": "2026-05-17T09:10:00+08:00"
  }
}
```

**错误响应**

| HTTP | message |
|------|---------|
| 400 | item_name / quantity / unit_price 均为必填项 |
| 400 | quantity 必须 ≥ 1 |
| 404 | 采购订单不存在 |

---

#### GET /api/purchase-orders/:id

**说明**：PO 详情（含明细项列表）
**Auth**：任意已登录用户（宽视图原则）

**响应 200**
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "id": 1,
    "fixture_id": 10,
    "supplier_id": 2,
    "supplier_name": "KFS",
    "contract_no": "PO-2026-001",
    "order_date": "2026-05-17",
    "planned_delivery_date": "2026-06-30",
    "status": "open",
    "total_amount": "8500.00",
    "created_by": 8,
    "version": 0,
    "items": [
      {
        "id": 1,
        "item_name": "SUS VC 压合治具主体",
        "quantity": 1,
        "unit_price": "8500.00",
        "unit": "套",
        "line_total": "8500.00"
      }
    ],
    "created_at": "2026-05-17T09:00:00+08:00"
  }
}
```

**错误响应**

| HTTP | message |
|------|---------|
| 404 | 采购订单不存在 |

### 5.2 仓储

> V1.3 未定义独立的仓储管理端点。**领用 / 归还 / 货架绑定等动作通过 `PATCH /api/fixtures/:id/status` + 关联字段实现**。如需独立的库位管理 / 货架绑定 / 领用历史等接口,需另行设计并经架构评审。

---

## 6. 附件与统计

> V1.4 Phase 3 新增独立附件上传端点 `POST /api/attachments`，用于业务单据提交后的补充附件上传（如审批中的补充材料、IQC 补充报告等）。各业务单据接口本身支持 multipart/form-data 随正文上传附件；此独立端点为补充上传场景提供支持。详见 `Doc/03_architecture_v1.4.md` 第 3.5 节。

---

### POST /api/attachments

**说明**：补充上传附件（关联已存在的业务单据）
**Auth**：任意已登录用户（上传后与 related_table/related_id 关联，具体操作权限由业务层保障）
**Content-Type**：multipart/form-data

**请求体字段**

| 字段 | 类型 | 必填 | 约束 |
|------|------|------|------|
| `file` | file | 是 | 文件实体 |
| `related_table` | string | 是 | 关联业务表名，如 `iqc_reports` / `acceptance_reports` / `repair_records` 等 |
| `related_id` | int | 是 | 关联记录 ID |
| `attachment_type` | string | 否 | 枚举：`report` / `photo` / `certificate` / `other`，默认 `other` |
| `remark` | string | 否 | |

**响应 201**
```json
{
  "code": 201,
  "message": "success",
  "data": {
    "id": 1,
    "file_path": "attachments/2026/05/xxx.pdf",
    "original_filename": "IQC补充报告.pdf",
    "file_size_kb": 128,
    "related_table": "iqc_reports",
    "related_id": 3,
    "uploaded_by": 5,
    "created_at": "2026-05-17T10:30:00+08:00"
  }
}
```

**错误响应**

| HTTP | message |
|------|---------|
| 400 | file / related_table / related_id 均为必填项 |
| 400 | attachment_type 枚举值非法（允许值：report / photo / certificate / other） |
| 413 | 文件大小超出限制（业务层建议单文件 ≤ 50MB） |

---

### 6.1 甘特图

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/projects/:id/gantt?batch_id=` | 项目甘特图(每行一个批次,可下钻 batch_id 过滤) |
| GET | `/api/batches/:id/gantt` | 批次甘特图(每行一个治具,显示计划 vs 实际) |

### 6.2 报表导出

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/projects/export?ids=&format=xlsx` | 项目列表导出 |
| GET | `/api/fixtures/export?...&format=xlsx` | 治具列表导出 |

> **导出策略说明**:
> - 单表 < 1000 条:**前端 xlsx 库直接生成**,不走后端导出接口
> - 多表关联或 > 1000 条:走上述后端接口,服务端用 `openpyxl(write_only=True)` + 游标分批流式响应
> - 月度大报表:**APScheduler 每月 1 日 02:30 自动生成**,结果存 `attachments` 表,用户去附件中心下载,**不提供用户触发的异步导出 API**
>
> 详见 [docs/07_export_guideline.md](./07_export_guideline.md)。

---

## 7. 系统管理

> 用户允许 PATCH 禁用,**不允许 DELETE**。

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/admin/users` | 用户列表 |
| POST | `/api/admin/users` | 新建用户 |
| PUT | `/api/admin/users/:id` | 编辑用户(角色/邮箱) |
| PATCH | `/api/admin/users/:id/deactivate` | ★ 禁用账号(is_active=FALSE) |
| PATCH | `/api/admin/users/:id/activate` | ★ 恢复账号 |

> ✗ **`DELETE /api/admin/users/:id` 不提供**

### 其他系统管理端点

V1.3 未明确列出治具模板库、供应商库、LT 默认值、设备代号字典、审计日志查询等系统管理端点。这些功能存在于业务需求中(详见《DBU模治具全流程管控文件 V2.1》第 7 节系统管理模块),但具体 API 设计需在 Phase 6 进入系统管理阶段时另行规约,届时同步更新本文档。

---

## 附:V1.2 / V1.3 对 V1.1 的演进重点

| 端点 | V1.1 → V1.2/V1.3 |
|------|--------------------|
| `PATCH /api/projects/:id/cancel` | V1.2 新增,替代物理删除 |
| `PATCH /api/batches/:id/cancel` | V1.2 新增 |
| `GET /api/projects/export` | V1.2 新增 |
| `GET /api/fixtures/export` | V1.2 新增 |
| `PATCH /api/admin/users/:id/deactivate` | V1.2 新增 |
| `PATCH /api/admin/users/:id/activate` | V1.2 新增 |
| 月度大报表 | V1.3:scheduler 容器 → APScheduler 内嵌 |

---

## 0. 认证模块（/api/auth）— Phase 0 已实现

> 全系统通用响应结构：`{ "code": <int>, "message": <str>, "data": <any> }`
> 时间字段均为 ISO 8601 字符串，时区 Asia/Shanghai（+08:00）。

### POST /api/auth/login

**说明**：用户名密码登录，返回 access token + refresh token
**Auth**：无需认证

**请求体**
```json
{ "username": "string", "password": "string" }
```

**响应 200**
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "access_token": "string",
    "refresh_token": "string",
    "user": {
      "id": 1,
      "username": "string",
      "full_name": "string | null",
      "role_code": "string | null"
    }
  }
}
```

**错误响应**
| HTTP | message |
|------|---------|
| 400 | username 和 password 为必填项 |
| 400 | 用户名或密码错误 |

---

### POST /api/auth/refresh

**说明**：用 refresh token 换取新 access token（access token 过期时调用）
**Auth**：Bearer **refresh** token

**请求体**：无

**响应 200**
```json
{ "code": 200, "message": "success", "data": { "access_token": "string" } }
```

---

### POST /api/auth/logout

**说明**：登出
**Auth**：Bearer access token

**请求体**：无

**响应 200**
```json
{ "code": 200, "message": "已登出", "data": null }
```

> ⚠️ 服务端不维护 token 吊销列表；客户端负责清除本地 token（localStorage/cookie）。
> 将来如需升级为服务端吊销，在此备注处更新实现方式。

---

### GET /api/auth/me

**说明**：获取当前登录用户 profile；前端刷新页面时调用 fetchMe
**Auth**：Bearer access token

**响应 200**
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "id": 1,
    "username": "string",
    "full_name": "string | null",
    "email": "string | null",
    "role_code": "string | null"
  }
}
```

**错误响应**
| HTTP | message |
|------|---------|
| 404 | 用户不存在或已停用 |
