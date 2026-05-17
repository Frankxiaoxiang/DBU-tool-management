# 权限矩阵

> 摘自《DBU模治具全流程管控文件 V2.1》第 6 节 RACI 责任矩阵与第 7 节系统用户角色与权限矩阵。
>
> **当前为占位框架文档。** 待从《DBU模治具全流程管控文件 V2.1》的 RACI 矩阵和权限矩阵中提取生成完整内容。当前先以 9 个角色（PM / 设计工程师 / ME 维护工程师 / 采购专员 / IQC 检验员 / 仓库管理员 / 生产班长 / 业务工程师 / 管理层 / 超级管理员）和关键操作项构建框架表格，后续补充。

> **设计原则**：宽视图、窄操作 — 所有角色（除成本模块外）均可查看全部项目数据，但只有对应责任角色才能在自己负责的节点执行操作。
>
> **铁律**：本文件是前后端权限的**单一真实来源**。前端 `permissions.js` 与后端 `@require_role()` 装饰器都派生自本文件，避免前后端偏移。

---

## 一、角色清单（9 个业务角色 + 1 个系统角色）

| 角色代号 | 角色全称 | 所属部门 | 核心职责（一句话） |
|----------|----------|----------|--------------------|
| `pm` | 项目工程师（PM） | 开发部 | 需求发起与项目追踪，对整体交期负责 |
| `design_engineer` | 模治具设计工程师 | 制造技术部 | 图纸设计、DFM 报告、采购申请单 |
| `me` | 维护工程师（ME） | 制造技术部 | 模治具安装调试与维护保养 |
| `purchaser` | 采购专员 | 采购部 | 询价下单、供应商管理、价格录入 |
| `iqc` | IQC 检验员 | 质量部 | 来料质量控制、紧急上机授权 |
| `warehouse` | 仓库管理员 | 生产部 | 到货签收、移交确认、货架绑定、封存执行 |
| `production_lead` | 生产线班长 | 生产部 | 生产领用、报修发起、保养触发 |
| `business_engineer` | 业务工程师 | 业务部 | 报废三方会签代表业务部审批 |
| `management` | 管理层（只读） | — | 跨项目数据查看，含全部成本 |
| `super_admin` | 超级管理员 | 系统 | 用户管理、模板库维护、强制状态跳转 |

---

## 二、操作权限矩阵（示例，待全量补充）

> ✅ = 可执行；👁 = 仅可查看；— = 无权限
>
> 完整版需对照《DBU模治具全流程管控文件 V2.1》第 7 节逐行迁移。

### 2.1 项目管理模块（示例）

| 操作 | super_admin | pm | design | me | purchaser | iqc | warehouse | production | business | management |
|------|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| 新建项目 | ✅ | ✅ | — | — | — | — | — | — | — | 👁 |
| 新建需求批次 | ✅ | ✅ | — | — | — | — | — | — | — | 👁 |
| 编辑需求单 | ✅ | ✅ | — | — | — | — | — | — | — | — |
| 查看所有项目 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |

### 2.2 设计模块（示例）

| 操作 | super_admin | pm | design | me | purchaser | iqc | warehouse | production | business | management |
|------|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| 上传图纸 / DFM | ✅ | — | ✅ | — | — | — | — | — | — | 👁 |
| 出具采购申请单 | ✅ | ✅ | ✅ | — | — | — | — | — | — | 👁 |

### 2.3 IQC / 验收模块（示例）

| 操作 | super_admin | pm | design | me | purchaser | iqc | warehouse | production | business | management |
|------|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| 到货签收 | ✅ | — | — | — | — | — | ✅ | — | — | 👁 |
| 录入 IQC 检验结果 | ✅ | — | — | — | — | ✅ | — | — | — | 👁 |
| 紧急上机授权 | ✅ | ✅ | — | — | — | ✅ | — | — | — | 👁 |
| IQC 不合格三方审批 | ✅ | ✅ | ✅ | ✅ | — | — | — | — | — | 👁 |
| 录入试产验收结果 | ✅ | — | ✅ | ✅ | — | ✅ | — | — | — | 👁 |

### 2.4 仓储模块（示例）

| 操作 | super_admin | pm | design | me | purchaser | iqc | warehouse | production | business | management |
|------|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| 货架绑定 / 库位管理 | ✅ | — | — | — | — | — | ✅ | — | — | 👁 |
| 领用 / 归还操作 | ✅ | — | — | — | — | — | — | ✅ | — | 👁 |

### 2.5 维保模块（示例）

| 操作 | super_admin | pm | design | me | purchaser | iqc | warehouse | production | business | management |
|------|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| 触发保养申请 | ✅ | — | — | — | — | — | — | ✅ | — | 👁 |
| 执行保养 / 维修 | ✅ | — | — | ✅ | — | — | — | — | — | 👁 |
| 发起报修 | ✅ | — | — | — | — | — | — | ✅ | — | 👁 |

### 2.6 成本模块（示例 — 唯一受限的"窄视图"模块）

| 操作 | super_admin | pm | design | me | purchaser | iqc | warehouse | production | business | management |
|------|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| 录入采购价格 / 维修费用 | ✅ | — | — | — | ✅ | — | — | — | — | — |
| 查看成本（自己项目） | ✅ | ✅ | — | — | — | — | — | — | — | — |
| 查看成本（所有项目） | ✅ | — | — | — | — | — | — | — | — | ✅ |

### 2.7 报废模块（示例）

| 操作 | super_admin | pm | design | me | purchaser | iqc | warehouse | production | business | management |
|------|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| 发起报废申请 | ✅ | ✅ | — | — | — | — | — | — | — | — |
| 报废三方线上会签 | ✅ | ✅ | — | — | — | — | — | ✅ | ✅ | — |

### 2.8 系统管理模块（示例）

| 操作 | super_admin | pm | design | me | purchaser | iqc | warehouse | production | business | management |
|------|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| 用户账号管理 | ✅ | — | — | — | — | — | — | — | — | — |
| 治具模板库维护 | ✅ | — | — | — | — | — | — | — | — | — |
| 供应商库维护 | ✅ | — | — | — | ✅ | — | — | — | — | — |
| LT 默认值维护 | ✅ | — | — | — | — | — | — | — | — | — |
| 强制状态跳转 | ✅ | — | — | — | — | — | — | — | — | — |

---

## 三、待补充清单

- [ ] 从《DBU模治具全流程管控文件 V2.1》第 6 节 RACI 矩阵补充每个流程节点的 R/A/C/I 标注
- [ ] 从该文件第 7 节迁移所有模块（项目 / 设计 / 采购 / IQC / 仓储 / 维保 / 成本 / 报废 / 系统管理）的完整操作行
- [ ] 与开发团队对齐"按钮级权限"的最小粒度
- [ ] 为每个"超管专属"操作单独建立审计日志触发点
- [ ] 派生前端 `permissions.js` 与后端 `@require_role()` 校验装饰器

---

## 四、/api/auth 端点权限（Phase 0 已实现）

| 端点 | 方法 | 允许角色 | 备注 |
|------|------|---------|------|
| `/api/auth/login` | POST | 无需认证 | 任何人可登录 |
| `/api/auth/refresh` | POST | 任意已登录用户 | 持有有效 refresh token 即可 |
| `/api/auth/logout` | POST | 任意已登录用户 | 持有有效 access token 即可 |
| `/api/auth/me` | GET | 任意已登录用户 | 持有有效 access token 即可 |

---

## 五、Phase 1 项目与批次模块端点权限（@require_role 映射）

> **说明**：本节是后端 `@require_role()` 装饰器的单一真实来源，前端 `permissions.js` 按钮级权限派生自此表。凡实现端点必须严格对照本节标注。

| 端点 | 方法 | @require_role（允许角色） | 备注 |
|------|------|--------------------------|------|
| `/api/projects` | GET | 任意已登录用户 | 宽视图原则，所有角色均可查看 |
| `/api/projects` | POST | `super_admin`, `pm` | 需求发起责任方 |
| `/api/projects/:id` | GET | 任意已登录用户 | 同上 |
| `/api/projects/:id` | PUT | `super_admin`, `pm` | 项目信息编辑 |
| `/api/projects/:id/cancel` | PATCH | `super_admin`, `pm` | 作废项目 |
| `/api/projects/:id/owner` | PUT | `super_admin` | 负责人转移属高权操作，仅超管 |
| `/api/projects/:id/gantt` | GET | 任意已登录用户 | 只读甘特图 |
| `/api/projects/:id/sync-templates` | POST | `super_admin` | 模板库变更追加快照，仅超管 |
| `/api/projects/export` | GET | 任意已登录用户 | 导出列表属只读操作 |
| `/api/batches` | GET | 任意已登录用户 | 宽视图，全员可查 |
| `/api/batches` | POST | `super_admin`, `pm` | 新建需求批次 |
| `/api/batches/:id` | GET | 任意已登录用户 | 宽视图 |
| `/api/batches/:id` | PUT | `super_admin`, `pm` | 编辑批次 |
| `/api/batches/:id/cancel` | PATCH | `super_admin`, `pm` | 作废批次 |
| `/api/batches/:id/fixtures` | GET | 任意已登录用户 | 只读 |
| `/api/batches/:id/gantt` | GET | 任意已登录用户 | 只读 |
| `/api/batches/:id/seal` | PATCH | `super_admin`, `warehouse` | 封存操作（草案，实现待 Phase 3） |
| `/api/batches/:id/unseal` | PATCH | `super_admin` | Phase 1 暂仅超管；Phase 4 扩展为 PM + 生产主管会签 |

**前端 `permissions.js` 派生规则（供 Phase 1 前端 Step 参考）：**
```javascript
const PROJECT_PERMISSIONS = {
  'project.create':         ['super_admin', 'pm'],
  'project.edit':           ['super_admin', 'pm'],
  'project.cancel':         ['super_admin', 'pm'],
  'project.transfer_owner': ['super_admin'],
  'project.sync_templates': ['super_admin'],
  'batch.create':           ['super_admin', 'pm'],
  'batch.edit':             ['super_admin', 'pm'],
  'batch.cancel':           ['super_admin', 'pm'],
  'batch.seal':             ['super_admin', 'warehouse'],
  'batch.unseal':           ['super_admin'],
}
```

---

## 六、Phase 2 模治具端点权限（@require_role 映射）

> **说明**：本节是后端 `@require_role()` 装饰器的单一真实来源，前端 `permissions.js` 按钮级权限派生自此表。凡实现端点必须严格对照本节标注。

| 端点 | 方法 | @require_role（允许角色） | 备注 |
|------|------|--------------------------|------|
| `/api/fixtures` | GET | 任意已登录用户 | 宽视图原则，所有角色均可查看 |
| `/api/fixtures` | POST | `super_admin`, `pm`, `me` | 治具新建（待 Frank 最终确认角色范围） |
| `/api/fixtures/:id` | GET | 任意已登录用户 | 宽视图 |
| `/api/fixtures/:id` | PUT | `super_admin`, `pm`, `me` | 治具基本信息编辑（同新建） |
| `/api/fixtures/:id/status` | PATCH（trigger=IQC 相关：`iqc_pass` / `concession_approved` / `emergency_auth` / `return_repair`） | `super_admin`, `iqc` | IQC 流程节点 |
| `/api/fixtures/:id/status` | PATCH（trigger=安装/验收相关：`normal`(INSTALLING→ACCEPTANCE_TESTING) / `acceptance_pass` / `rework` / `acceptance_fail_scrap`） | `super_admin`, `me` | ME 工程师节点 |
| `/api/fixtures/:id/status` | PATCH（trigger=领用归还：`checkout` / `return` / `maintenance_due` / `repair_request`） | `super_admin`, `production_lead`, `warehouse` | 仓储与生产节点 |
| `/api/fixtures/:id/status` | PATCH（trigger=报废：`scrap`） | `super_admin`, `pm` | 报废发起 |
| `/api/fixtures/:id/force-status` | POST | `super_admin` | 强制跳转，唯一超管专属 |
| `/api/fixtures/:id/version-bump` | POST | `super_admin`, `pm`, `design_engineer` | 图纸版本升级 |
| `/api/fixtures/:id/copy-to-batch` | POST | `super_admin`, `pm`, `design_engineer` | 加开-复制图纸 |
| `/api/fixtures/batch-seal` | POST | `super_admin`, `warehouse` | 批量封存（§3.3.x 业务规则） |
| `/api/fixtures/:id/release-seal` | POST | `super_admin` | 解封（Phase 4 扩展为 PM+生产主管会签，当前仅超管） |
| `/api/fixtures/:id/recalc-dates` | POST | `super_admin`, `pm` | 计划日期重算（Phase 5 实现；Phase 2 先定权限） |
| `/api/fixtures/export` | GET | 任意已登录用户 | 导出属只读操作 |

> **`PATCH /api/fixtures/:id/status` 说明**：单一端点按 `trigger` 字段分场景管控权限，后端实现时在 Blueprint 内解析 `trigger` 后再校验角色；表中分行列出是为了便于后端实现者对照，`@require_role` 装饰器层面以"所有可能操作角色的并集"做粗粒度拦截，Service 层做精细 trigger × role 校验。

**前端 `permissions.js` 派生规则（供 Phase 2 前端 Step 参考）：**
```javascript
const FIXTURE_PERMISSIONS = {
  'fixture.create':        ['super_admin', 'pm', 'me'],
  'fixture.edit':          ['super_admin', 'pm', 'me'],
  'fixture.status.iqc':    ['super_admin', 'iqc'],
  'fixture.status.me':     ['super_admin', 'me'],
  'fixture.status.wh':     ['super_admin', 'production_lead', 'warehouse'],
  'fixture.status.scrap':  ['super_admin', 'pm'],
  'fixture.force_status':  ['super_admin'],
  'fixture.version_bump':  ['super_admin', 'pm', 'design_engineer'],
  'fixture.copy_to_batch': ['super_admin', 'pm', 'design_engineer'],
  'fixture.batch_seal':    ['super_admin', 'warehouse'],
  'fixture.release_seal':  ['super_admin'],
  'fixture.recalc_dates':  ['super_admin', 'pm'],
}
```

---

## 七、Phase 3 流程节点端点权限（@require_role 映射）

> **说明**：本节是后端 `@require_role()` 装饰器的单一真实来源，前端 `permissions.js` 按钮级权限派生自此表。凡实现端点必须严格对照本节标注。

| 端点 | 方法 | @require_role（允许角色） | 备注 |
|------|------|--------------------------|------|
| `/api/drawings` | POST | `super_admin`, `design_engineer` | 图纸/DFM 上传 |
| `/api/drawings/:id` | GET | 任意已登录用户 | 宽视图 |
| `/api/purchase-requisitions` | POST | `super_admin`, `design_engineer`, `pm` | 采购申请单（PM 可确认发起） |
| `/api/purchase-requisitions/:id` | GET | 任意已登录用户 | 宽视图 |
| `/api/purchase-orders` | POST | `super_admin`, `purchaser` | 采购下单 |
| `/api/purchase-orders/:id` | GET | 任意已登录用户 | 宽视图（含明细项） |
| `/api/purchase-orders/:id/items` | POST | `super_admin`, `purchaser` | 录入 PO 明细 |
| `/api/goods-receipts` | POST | `super_admin`, `warehouse` | 到货签收 |
| `/api/goods-receipts/:id` | GET | 任意已登录用户 | 宽视图 |
| `/api/iqc-reports` | POST | `super_admin`, `iqc` | IQC 检验结果录入 |
| `/api/iqc-reports/:id` | GET | 任意已登录用户 | 宽视图 |
| `/api/emergency-auth-records` | POST | `super_admin`, `pm`, `iqc` | 紧急上机授权单（PM + IQC 双方授权） |
| `/api/emergency-auth-records/:id` | GET | 任意已登录用户 | 宽视图 |
| `/api/install-records` | POST | `super_admin`, `me` | ME 安装调试记录 |
| `/api/install-records/:id` | GET | 任意已登录用户 | 宽视图 |
| `/api/acceptance-reports` | POST | `super_admin`, `iqc`, `me`, `design_engineer` | 试产验收报告（IQC/ME/设计工程师联合录入） |
| `/api/acceptance-reports/:id` | GET | 任意已登录用户 | 宽视图 |
| `/api/handover-records` | POST | `super_admin`, `warehouse` | 移交确认 |
| `/api/handover-records/:id` | GET | 任意已登录用户 | 宽视图 |
| `/api/checkout-records` | POST | `super_admin`, `production_lead` | 领用 / 归还操作 |
| `/api/checkout-records/:id` | GET | 任意已登录用户 | 宽视图 |
| `/api/maintenance-records` | POST | `super_admin`, `me` | 保养执行记录 |
| `/api/maintenance-records/:id` | GET | 任意已登录用户 | 宽视图 |
| `/api/repair-records` | POST | `super_admin`, `me` | 维修记录（含费用字段） |
| `/api/repair-records/:id` | GET | 任意已登录用户 | 宽视图 |
| `/api/scrap-records` | POST | `super_admin`, `pm` | 报废申请发起 |
| `/api/scrap-records/:id` | GET | 任意已登录用户 | 宽视图 |
| `/api/attachments` | POST | 任意已登录用户 | 补充附件上传，操作权限由业务层保障 |

**前端 `permissions.js` 派生规则（供 Phase 3 前端 Step 参考）：**
```javascript
const FLOW_PERMISSIONS = {
  'drawing.upload':             ['super_admin', 'design_engineer'],
  'purchase_req.create':        ['super_admin', 'design_engineer', 'pm'],
  'purchase_order.create':      ['super_admin', 'purchaser'],
  'purchase_order.add_item':    ['super_admin', 'purchaser'],
  'goods_receipt.create':       ['super_admin', 'warehouse'],
  'iqc_report.create':          ['super_admin', 'iqc'],
  'emergency_auth.create':      ['super_admin', 'pm', 'iqc'],
  'install_record.create':      ['super_admin', 'me'],
  'acceptance_report.create':   ['super_admin', 'iqc', 'me', 'design_engineer'],
  'handover_record.create':     ['super_admin', 'warehouse'],
  'checkout_record.create':     ['super_admin', 'production_lead'],
  'maintenance_record.create':  ['super_admin', 'me'],
  'repair_record.create':       ['super_admin', 'me'],
  'scrap_record.create':        ['super_admin', 'pm'],
}
```
