# 待确认业务问题清单

> 此处记录开发过程中产生的待确认业务问题。
>
> 每条问题需注明：发起日期、问题描述、责任确认方、确认结果与日期。
> 已确认的问题应同步回写到对应需求文档（如 docs/01_requirement_v2.1.md），并将本文件中的条目标记为 ✅ 已关闭。

---

## 当前未关闭问题

### Q-001：401 是否自动尝试 refresh_token？

- **提出日期**：2026-05-10
- **背景**：当前 MVP 实现：401 直接清除本地 token 并跳转 `/login`，不自动 refresh。
- **影响范围**：`src/api/request.js` 响应拦截器；`src/api/auth.js` 的 `refresh()` 函数目前仅供手动调用。
- **可选方案**：
  - A. 保持现状：401 一刀切跳登录。优点：简单、无并发问题；缺点：access token 过期时用户被强制重新登录。
  - B. Phase 1+ 升级：401 → 尝试用 refresh token 换新 access token → 成功则重放原请求 → 失败才跳登录。
- **责任确认方**：Frank
- **状态**：🟡 待确认
- **确认结果**：
- **关闭日期**：

---

### Q-002：localStorage key 命名约定

- **提出日期**：2026-05-10
- **背景**：当前新系统使用 `access_token` / `refresh_token` 作为 localStorage key。vc-cost-system 既有项目使用单一 `'token'` key（CLAUDE.md Rule 12 引用）。
- **影响范围**：`src/utils/storage.js`（TOKEN_KEY / REFRESH_KEY 常量）；若修改需同步清理所有 localStorage 操作点。
- **可选方案**：
  - A. 保持 `access_token` / `refresh_token`：语义更准确，与 refresh 机制对称。
  - B. 改回 `token`（单一 key）：减少认知负担，与 vc-cost-system 保持一致；但 refresh token 存放位置需另议。
- **责任确认方**：Frank
- **状态**：🟡 待确认
- **确认结果**：
- **关闭日期**：

---

### Q-003：batches 表是否需要 sealed_fixture_count 汇总字段

- **提出日期**：2026-05-14
- **背景**：封存操作执行后，前端批次列表/详情页可能需要展示"已封存治具数量"。若不加汇总字段，每次查询需 JOIN fixtures 表计算 COUNT(is_sealed=True)，在批次治具数量较多时有性能压力。
- **影响范围**：`batches` 表 Schema（需新增字段 + Migration）、`batch_service.seal_batch()`（写入时维护计数）、BatchList.vue / BatchForm.vue（展示字段）
- **可选方案**：
  - A. 在 `batches` 表加 `sealed_fixture_count INT DEFAULT 0`，seal 时同步更新（读性能好，写逻辑略复杂）
  - B. 不加字段，每次查询时 COUNT JOIN（写逻辑简单，读性能略差；治具数量一般 < 100，影响有限）
- **责任确认方**：Frank（架构决策）
- **状态**：🟡 待确认
- **确认结果**：
- **关闭日期**：

---

### Q-004：manual_init 批次封存后 batches.status 是否新增 sealed 子状态

- **提出日期**：2026-05-14
- **背景**：当前 `batches.status` 枚举为 `draft / in_progress / completed / cancelled`。手动版批次封存后，业务语义上与"完成"不同（封存是物理锁定，completed 是流程结束）。若不区分，前端无法通过批次状态判断是否已封存；若区分，状态机需新增路径。
- **影响范围**：`batches` 表 `status` 字段枚举值、`batch_service._safe_transition()`、前端 `utils/status.js` 批次状态映射、`Doc/03_architecture_v1.4.md` §3.3 状态机 TRANSITIONS
- **可选方案**：
  - A. 新增 `sealed` 状态值（语义清晰，但状态机路径增加；`manual_init` 批次专属）
  - B. 保持现有枚举不变，封存状态仅由 `fixtures.is_sealed` 聚合反映（更简单，但 batches 层面无直接状态字段）
- **责任确认方**：Frank（架构决策）
- **状态**：🟡 待确认
- **确认结果**：
- **关闭日期**：

---

### Q-005：解封会签是否复用 §3.4 的 sequential/parallel 审批流引擎

- **提出日期**：2026-05-14
- **背景**：解封需要 PM + 生产主管（`production_lead`）双人会签，属于 2 人顺序审批（sequential 模式）。§3.4 设计的审批流引擎支持 sequential/parallel 双模式，理论上可以复用。但解封场景较特殊（涉及 fixtures 批量状态回写），可能需要单独处理 post-approval 回调。
- **影响范围**：Phase 4 审批流实现范围、`approval_records` 表设计、`batch_service.unseal_batch()` 的 post-approval hook
- **可选方案**：
  - A. 完全复用 §3.4 引擎（`flow_type='unseal'`，`sequential_or_parallel='sequential'`），在引擎的 approved 回调里触发 fixtures 解封逻辑
  - B. 解封走独立审批路径（代码简单，但违反 CLAUDE.md §e.6"禁止为每种场景写独立审批流代码"铁律）——**此方案违规，不推荐**
- **责任确认方**：Frank（架构决策；Phase 4 开始前需关闭）
- **状态**：🟡 待确认
- **确认结果**：
- **关闭日期**：

---

### Q-009：`seal_batch` 时 `fixture.current_status` 是否同步改为 `sealed`

- **提出日期**：2026-05-15
- **背景**：`seal_batch()` 向 `fixture_status_history` 写入一条辅助事件记录。§3.3.x 的代码示例写的是 `to_status='sealed'`，但同节文本又说"封存状态当前仅由 `fixtures.is_sealed` 字段反映，`current_status` 不变"。两者存在轻微张力。
- **影响范围**：`batch_service.seal_batch()` 的 `FixtureStatusHistory` 写入逻辑（Step 2-7-1）；若 `current_status` 变为 `sealed`，则需在状态机 `TRANSITIONS` 中对 `sealed` 增加出口路径（影响 `state_machine.py` + 前端 `status.js` + i18n）
- **可选方案**：
  - A. `to_status = fixture.current_status`（历史记录中 from_status == to_status，语义为"辅助事件"，不影响工艺流程状态；与 `version_bump` 同模式，**推荐**）
  - B. `to_status = 'sealed'`（严格照搬 §3.3.x 代码示例；需同步评估是否修改 `TRANSITIONS` 增加 sealed 出口）
- **责任确认方**：Frank（Step 2-7-1 执行前必须关闭）
- **状态**：🟡 待确认
- **确认结果**：
- **关闭日期**：

---

### Q-010：移交确认（handover-records）与状态机的关系

- **提出日期**：2026-05-17
- **背景**：§3.3 `TRANSITIONS` 中 `acceptance_pass` trigger 直接将状态从 `ACCEPTANCE_TESTING` 流转到 `IN_STOCK`，未定义"待移交"中间态。移交确认单（`handover-records`）当前 spec 暂定为"仅作业务单据，不触发状态变更"。
- **影响范围**：`Doc/04_api_spec.md` §3 `handover-records` 端点说明；`state_machine.py` TRANSITIONS 是否需要新增 `ACCEPTANCE_TESTING → AWAITING_HANDOVER → IN_STOCK` 两跳路径；前端流程节点页面展示逻辑
- **可选方案**：
  - A. 保持现状：移交确认仅作业务单据（记录移交动作），状态机维持 `acceptance_pass` 直接 `→ IN_STOCK`（简单，无中间态，**推荐**）
  - B. 新增"验收合格-待移交"中间态（`AWAITING_HANDOVER`），移交确认后才流转 `→ IN_STOCK`（语义更严谨，但状态机复杂度增加，需同步改 5 处）
- **责任确认方**：Frank（Phase 3 Step 3-1 开始前必须关闭）
- **状态**：🟡 待确认
- **确认结果**：
- **关闭日期**：

---

### Q-011：单据 POST 与状态流转是否维持解耦

- **提出日期**：2026-05-17
- **背景**：当前 `Doc/04_api_spec.md` §3 设计原则为：业务单据 POST（如 `iqc-reports`、`checkout-records`）与状态流转（`PATCH /api/fixtures/:id/status`）解耦，由前端/业务层按顺序调用两个接口。此设计遵循 §e.4「状态变更唯一入口」铁律。但存在原子性风险：单据 POST 成功后状态变更失败，数据不一致。
- **影响范围**：所有 Phase 3 业务单据 Blueprint 实现方式；是否需要数据库事务包裹"单据插入 + 状态变更"两步
- **可选方案**：
  - A. 维持解耦（现方案）：单据 POST 和状态 PATCH 各自独立，前端顺序调用；实现简单，符合 §e.4（**推荐**）
  - B. 单据 POST 内联调用状态机（原子性强）：在 Service 层一个事务内同时写单据 + 调用 `transition()`；需明确哪些单据强依赖状态流转（到货签收→pending_iqc、领用→in_use 等）
- **责任确认方**：Frank（Phase 3 Step 3-1 开始前必须关闭）
- **状态**：🟡 待确认
- **确认结果**：
- **关闭日期**：

---

### Q-012：PO 下单时是否自动推算各节点计划日期

- **提出日期**：2026-05-17
- **背景**：`Doc/03_architecture_v1.4.md` §4.3 描述"采购下单时自动推算各节点计划日期"（基于 LT 默认值）。但 `TASKS.md` 将"计划日期推算与级联重算"明确列在 Phase 5。Phase 3 PO 步骤是否需要触发推算逻辑，还是仅存采购下单日，计划日期字段暂为 null？
- **影响范围**：`purchase_order_service.create()` 是否调用 `recalc_dates()`；Phase 5 的计划日期推算模块实现时序
- **可选方案**：
  - A. Phase 3 PO 仅存采购下单日，计划日期推算完全留 Phase 5（**推荐**，与 TASKS.md 一致，避免 Phase 3 引入 LT 计算复杂度）
  - B. Phase 3 PO 下单时触发简化版推算（只算交期，不做级联）；Phase 5 再完善级联重算
- **责任确认方**：Frank（Phase 3 Step 3-2 开始前必须关闭）
- **状态**：🟡 待确认
- **确认结果**：
- **关闭日期**：

---

### Q-013：货架/库位是否作为 fixtures 表的活属性字段

- **提出日期**：2026-05-17
- **背景**：移交确认（`handover-records`）和领用归还（`checkout-records`）都涉及货架/库位信息。当前 `fixtures` 表 DDL（见 `Doc/03_architecture_v1.4.md` §2.3）未包含 `shelf_location` 字段。保养记录需要知道治具当前存放位置。
- **影响范围**：`fixtures` 表是否新增 `shelf_location` / `current_location` 字段（需新增 Migration）；Phase 5 仓储管理模块设计
- **可选方案**：
  - A. 将 `shelf_location` 作为 `fixtures` 表的活属性字段，每次入库/移交时更新（读性能好，位置始终可查；需 Migration）
  - B. 库位仅记录在 `handover-records` / `checkout-records` 业务单据中，不写回 fixtures 表（写逻辑简单，但查治具当前位置需 JOIN 单据表取最新记录）
- **责任确认方**：Frank（Phase 3 Step 3-5 仓储相关 Step 开始前必须关闭）
- **状态**：🟡 待确认
- **确认结果**：
- **关闭日期**：

---

## 已关闭问题（归档）

| # | 提出日期 | 问题描述 | 确认方 | 确认结果 | 关闭日期 |
|---|----------|----------|--------|----------|----------|
| Q-006 | 2026-05-15 | `fixtures` 表是否保留独立的 `status`（行政作废）字段，与 `current_status`（12状态机）并存 | Frank | ✅ 保留 `fixtures.status`（active/cancelled），与 `current_status` 两个正交维度，同 projects/batches 一致（§e.3/§e.12） | 2026-05-15 |
| Q-007 | 2026-05-15 | 图纸版本升级是否需要独立的 `fixture_version_history` 表 | Frank | ❌ 不新建；复用 `fixture_status_history`，`version_bump()` 写 `trigger_type='version_bump'` + `from_status==to_status==current_status` + `reason` 记录版本变化 | 2026-05-15 |
| Q-008 | 2026-05-15 | `POST /api/fixtures/batch-seal` 批量封存是否纳入 Phase 2 | Frank | ✅ 纳入 Phase 2（Step 2-7-1）；`unseal` 解封审批流（PM + 生产主管会签）仍留 Phase 4 | 2026-05-15 |

---

## 模板（新增问题时复制本块）

### Q-XXX：[问题简述]

- **提出日期**：YYYY-MM-DD
- **背景**：
- **影响范围**：
- **可选方案**：
  - A.
  - B.
- **责任确认方**：
- **状态**：🟡 待确认 / ✅ 已关闭
- **确认结果**：
- **关闭日期**：
