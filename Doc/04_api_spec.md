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

### 1.1 项目(无 DELETE)

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/projects` | 项目列表(支持按产品类型/状态/负责人过滤) |
| POST | `/api/projects` | 新建项目(系统分配 project_code) |
| GET | `/api/projects/:id` | 项目详情(含挂载批次) |
| PUT | `/api/projects/:id` | 编辑项目(含 version 字段) |
| PATCH | `/api/projects/:id/cancel` | ★ 作废项目(status=cancelled,需填 reason) |
| PUT | `/api/projects/:id/owner` | 转移项目负责人 |
| GET | `/api/projects/:id/gantt?batch_id=` | 项目甘特图数据(可按 batch_id 过滤) |
| POST | `/api/projects/:id/sync-templates` | 追加同步模板快照(仅补缺,不覆盖) |
| GET | `/api/projects/export?ids=&format=xlsx` | ★ 项目列表导出 |

### 1.2 批次(无 DELETE)

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/batches` | 新建需求批次(挂载于项目下,含批次类型) |
| GET | `/api/batches/:id` | 批次详情 |
| PUT | `/api/batches/:id` | 编辑批次 |
| PATCH | `/api/batches/:id/cancel` | ★ 作废批次 |
| GET | `/api/batches/:id/fixtures` | 该批次下所有治具清单 |
| GET | `/api/batches/:id/gantt` | 批次甘特图数据 |

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

## 3. 流程节点 — 业务单据(扁平化资源,无 DELETE)

业务单据均为扁平化资源,通过 body 中的 `fixture_id` 关联治具。

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/iqc-reports` | IQC 检验报告(含合格/不合格、是否紧急上机授权) |
| POST | `/api/acceptance-reports` | 试产验收报告(合格/不合格) |
| POST | `/api/install-records` | ME 安装调试记录 |
| POST | `/api/maintenance-records` | 保养记录(由保养触发后录入) |
| POST | `/api/repair-records` | 维修记录(由报修单后录入,含费用) |
| POST | `/api/scrap-records` | 报废记录 |

> **说明**:领用 / 归还 / 报修 / 保养触发等"状态变更"动作走 `PATCH /api/fixtures/:id/status`,这里的 `*-records` 是流程产出的**单据数据**(报告内容、附件、责任人),与状态变更解耦。

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

### 5.1 采购订单(无 DELETE,一对多结构:PO 头 + items)

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/purchase-orders` | 新建 PO(含合同号、供应商、总交期) |
| POST | `/api/purchase-orders/:id/items` | 添加 PO 明细项(关联具体 fixture) |
| GET | `/api/purchase-orders/:id` | PO 详情(含明细项) |

### 5.2 仓储

> V1.3 未定义独立的仓储管理端点。**领用 / 归还 / 货架绑定等动作通过 `PATCH /api/fixtures/:id/status` + 关联字段实现**。如需独立的库位管理 / 货架绑定 / 领用历史等接口,需另行设计并经架构评审。

---

## 6. 附件与统计

> V1.3 未定义独立的附件上传端点(`/api/uploads`)。文件上传按业务单据接入(IQC、验收、安装、维保、维修等接口接受 multipart/form-data 含附件字段),具体实现见 [docs/03_architecture_v1.4.md](./03_architecture_v1.4.md) 第 3.5 节。

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
