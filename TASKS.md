# TASKS.md — 任务进度追踪

> **每次开发会话前请让 AI 读取本文件以了解当前进度。**
>
> 任务清单基于《DBU_System_Architecture_Design_V1.4.md》第 5.1 节"模块开发顺序"。
> 使用 `- [ ]` / `- [x]` 标记，每完成一项及时勾选并填写完成日期 & 完成人备注。

---

## 当前阶段

✅ **Phase 0 — 基建（已完成 2026-05-10）**

🟢 **Phase 1 — 项目与批次模块（进行中）**

预计完成时间：Phase 0 完成 + 约 2 周
当前状态：进行中

---

## Phase 0 — 基建（约 1 周）

### 0.1 开发机环境（ThinkPad Windows 11）

- [x] 安装 Python 3.12 并加入 PATH — 2026-05-10
- [x] 安装 Docker Desktop（用于 MySQL 容器） — 2026-04-29
- [x] 启动 Docker MySQL 8.4 容器（含 utf8mb4 + `+08:00` 时区） — 2026-04-29
  ```bash
  docker run -d --name dbu-mysql-dev \
    -e MYSQL_ROOT_PASSWORD=devpassword \
    -e MYSQL_DATABASE=dbu_fixture \
    -p 3306:3306 -v dbu_mysql_data:/var/lib/mysql \
    mysql:8.4 \
    --character-set-server=utf8mb4 \
    --collation-server=utf8mb4_unicode_ci \
    --default-time-zone='+08:00'
  ```
- [x] 安装 Node.js LTS + 启用 pnpm（`corepack enable`） — 2026-05-10
- [x] 安装 Git — 2026-05-10
- [x] 准备 .env.development 模板 — 2026-05-10
- [x] 验证 Docker MySQL 可连接（`mysql -h 127.0.0.1 -uroot -p`） — 2026-05-10

### 0.2 生产机预演（公司 Windows Server）

- [x] 与 IT 沟通申请 Windows Server 资源 / 固定内网 IP — 2026-05-10
- [x] 安装 Python 3.12（C:\Python312\） — 2026-05-10
- [x] 安装 MySQL 8.4 LTS（utf8mb4 + Windows 服务自动启动） — 2026-05-10
- [x] 安装 NSSM（C:\Windows\System32\nssm.exe） — 2026-05-10
- [x] 创建目录结构：`C:\dbu\backend`、`C:\dbu\frontend`、`D:\dbu\uploads`、`D:\dbu\logs`、`D:\dbu\backup`、`D:\dbu\reports`、`D:\dbu\scripts` — 2026-05-10
- [x] 申请 SMTP 邮箱账号（告警发送用） — 2026-05-10
- [x] 申请 5000 端口内网防火墙开放 — 2026-05-10
- [x] 杀软白名单（Python venv + NSSM） — 2026-05-10
- [x] 系统更新策略调整（避免业务时段自动重启） — 2026-05-10

### 0.3 后端代码框架

- [x] 项目结构创建（`backend/app/__init__.py`、`config.py`、`extensions.py`、`models/`、`services/`、`blueprints/`、`utils/`） — 2026-04-30
- [x] Flask app factory 实现（`create_app(config_name=None)`） — 2026-04-30
- [x] python-dotenv 三套环境配置加载（`.env.development` / `.env.production` / `.env.example`） — 2026-04-30
- [x] **★ Config 含 `pool_pre_ping=True` + `pool_recycle=3600`** — 2026-04-30
- [x] **★ TimedRotatingFileHandler 配置**（按天切割，backupCount=30） — 2026-04-30
- [x] SQLAlchemy + Flask-Migrate 初始化 — 2026-04-30
- [x] 确认空库已创建（`SHOW DATABASES` 验证 `dbu_fixture` 存在） — 2026-04-30
- [x] `flask db init`（初始化 `migrations/` 目录） — 2026-04-30
- [x] 编写初始 Migration（`users` / `roles` / `system_dicts` 三张基础表） — 2026-04-30
- [x] `flask db migrate -m "init schema"` — 2026-04-30
- [x] `flask db upgrade`（执行建表到 Docker MySQL） — 2026-04-30
- [x] 验证：`SHOW TABLES` 确认三张表已创建 — 2026-04-30
- [x] User / Role 模型（含 `is_active` 软删字段 + `user_roles` 关联表） — 2026-04-30
- [x] JWT 登录接口（`POST /api/auth/login` / `refresh` / `logout` / `me`） — 2026-04-30
- [x] 通用响应工具（`success_response` / `error_response`） — 2026-04-30
- [x] 通用异常类（`ConflictError`、`ForbiddenError`、`ValidationError`、`NotFoundError`） — 2026-04-30
- [x] 装饰器（`@require_role`，从 JWT claims 读 role_codes，避免查 DB） — 2026-04-30
- [x] 全局 errorhandler：`StaleDataError`→409、`ConflictError`→409、`ValidationError`→400、`ForbiddenError`→403、`NotFoundError`→404 + JWT 错误回调 — 2026-04-30
- [x] **★ 各 Model 不写 `__mapper_args__ = {'version_id_col': version}`**（仅手动校验乐观锁） — 2026-04-30
- [x] APScheduler 集成（含守卫 `if not app.debug or WERKZEUG_RUN_MAIN == 'true'`，timezone=Asia/Shanghai） — 2026-04-30
- [ ] **JWT logout 服务端撤销（token blocklist 表）** — 留 Phase 1 补；当前仅客户端删 Token，`docs/04_api_spec.md` 已注明

### 0.4 scripts/seed_data.py 完整化

- [x] 超管账号（密码从 `.env` 读取） — 2026-05-02
- [x] 角色字典（10 角色：pm / design_engineer / me / purchaser / iqc / warehouse / production_lead / business_engineer / management / super_admin） — 2026-05-02
- [x] 状态字典（12 状态：pending_iqc / iqc_inspecting / emergency_pending / concession_accepted / installing / acceptance_testing / in_stock / in_use / maintaining / repairing / sealed / scrapped） — 2026-05-02
- [x] 设备代号字典（YN / DZ2X / DZ2S / LRJ / ZDY / YY） — 2026-05-02
- [x] 11 项默认供应商（KFS / HR / HS / BT / HX / JC / XW / FBW / DR / XDX / XD） — 2026-05-02
- [x] SUS VC 治具模板（含 BOTH 共 34 项：CY-GC、CY-LX、DW-M、FB-YN 等） — 2026-05-02
- [x] Cu VC 治具模板（8 项：SK、CC-YY、SJ、TH、DJ、QH、YTJ 等），合计 42 项模板 — 2026-05-02
- [x] `flask seed` CLI 命令封装，支持反复执行（幂等）与 `--reset` 重置，外键冲突由 `FOREIGN_KEY_CHECKS=0/1` 处理 — 2026-05-02

### 0.5 Doc/09_dev_rules.md 落位

- [x] 后端禁律 11 条 — 2026-05-10
- [x] 前端禁律 8 条 — 2026-05-10
- [x] 命名约定 — 2026-05-10
- [x] Code Review Checklist — 2026-05-10
- [x] 在 CLAUDE.md 中引用 — 2026-05-10

### 0.6 前端 Vue 项目初始化

- [x] `pnpm create vite` 创建 Vue 3 项目 — 2026-05-10
- [x] 安装核心依赖：Vue Router 4 / Pinia / Element Plus / Axios / dayjs / nanoid / xlsx — 2026-05-10
- [x] `vite.config.js` API 代理配置（`/api` → `localhost:5000`） — 2026-05-10
- [x] 目录结构（`api/` / `router/` / `stores/` / `views/` / `components/` / `utils/`） — 2026-05-10
- [x] **★ `utils/datetime.js` 实现**（`parseBackendTime` / `formatBackendTime` 工具） — 2026-05-10
- [x] **★ `main.js` 顶层 `import './utils/datetime'`**（副作用导入） — 2026-05-10
- [x] **★ Axios 拦截器**（401 → 跳登录、409 → 弹窗刷新） — 2026-05-10
- [x] `stores/auth.js`（含 fetchMe + 防循环依赖） — 2026-05-10
- [x] 路由守卫（刷新时先 fetchMe） — 2026-05-10
- [x] 登录页 + 主框架页（侧边导航 + 顶部用户信息） — 2026-05-10
- [x] eslint 规则配置（含 `no-restricted-syntax` 拦截裸 `dayjs(str)` / `new Date(str)`） — 2026-05-10

### 0.7 Phase 0 收尾

- [x] 后端 + 前端能联调登录流程 — 2026-05-10
- [x] CI 跑通基础测试（如有） — 2026-05-10
- [x] CLAUDE.md / TASKS.md 更新进度 — 2026-05-10
- [x] 团队 review 后正式进入 Phase 1 — 2026-05-10

---

## Phase 1 — 项目与批次模块

🟢 进行中 | 详细参数见 [TASKS_Phase1_detail.md](./TASKS_Phase1_detail.md)（共 19 个 Step，5 个子模块）

> **建议执行顺序**：1-0-1 → 1-1-1 → 1-1-2 → 1-1-3 → 1-2-1 → 1-2-2 → 1-2-3 → 1-1-4 → 1-1-5 → 1-2-4 → 1-3-1 → 1-3-2 → 1-3-3 → 1-3-4 → 1-3-5 → 1-4-1 →（决策点）→ 1-4-2 → 1-5-1 → 1-5-2
> **当前进行到**：Step 1-1-1（未开始）

### 1.0 准备（1 步）

- [x] **1-0-1** API spec & 权限矩阵补全（04_api_spec.md §1.1 9端点 + §1.2 6端点+2草案；05_permissions.md §五 17行）— 2026-05-11

### 1.1 项目模块（5 步）

- [ ] **1-1-1** Project Model + Migration（T01）
- [ ] **1-1-2** project_service + Blueprint（T02）含 code_generator.generate_project_code()
- [ ] **1-1-3** project_service 单元测试（T07）
- [ ] **1-1-4** ProjectList 前端列表页（T03）含 utils/status.js 初建
- [ ] **1-1-5** ProjectForm 前端表单页，create/edit/detail 三合一（T04）

### 1.2 模板快照机制（4 步）

- [ ] **1-2-1** FixtureTemplateSnapshot Model + Migration（T01）
- [ ] **1-2-2** snapshot_service + 集成 project_service.create_project + /sync-templates 端点（T02）
- [ ] **1-2-3** snapshot_service 单元测试（T07）
- [ ] **1-2-4** ProjectForm/Detail "追加同步模板"按钮（T04 扩展）

### 1.3 批次模块（5 步）

- [ ] **1-3-1** Batch Model + Migration（T01）含 4 种批次类型字段
- [ ] **1-3-2** batch_service + Blueprint（T02）含批次类型业务规则 + batch_no 自动生成
- [ ] **1-3-3** batch_service 单元测试（T07）含 4 种类型规则违反用例
- [ ] **1-3-4** BatchList 前端列表页（T03）
- [ ] **1-3-5** BatchForm 前端表单页（T04）含批次类型联动校验

### 1.4 手动版封存 / 解封（2 步，第 2 步可选）

- [ ] **1-4-1** 封存/解封 API spec & 业务规则文档化 + 3 条 open questions（手写提示词）
- [ ] **1-4-2** ⚠️ 可选（Frank 决策后）：seal/unseal 接口骨架（T02）

### 1.5 Phase 1 收尾（2 步）

- [ ] **1-5-1** 项目—批次链路端到端联调，5 条冒烟脚本（手写提示词）
- [ ] **1-5-2** TASKS.md / CLAUDE.md 进度同步（手写提示词）

---

## Phase 2 — 模治具核心模块

- [ ] 治具 CRUD
- [ ] 编码自动生成（services/code_generator.py）
- [ ] 图纸版本管理（A1 → A2 → A3 → B1 → ...）
- [ ] 加开-复制图纸（parent_fixture_id 溯源）
- [ ] 状态机三函数（transition / reject / force_transition）
- [ ] 状态历史表写入
- [ ] 单元测试覆盖（含 test_no_back_door_in_transition）

---

## Phase 3 — 流程节点模块

- [ ] 设计阶段：图纸/DFM 上传、采购申请单
- [ ] 采购阶段：PO 头 + items 一对多
- [ ] IQC 标准路径与紧急上机路径
- [ ] 安装调试记录
- [ ] 试产验收（合格/不合格分支）
- [ ] 移交确认
- [ ] 生产领用与归还
- [ ] 保养触发与记录
- [ ] 报修与维修
- [ ] 报废申请

---

## Phase 4 — 审批流模块

- [ ] 审批流引擎（顺序/并行双模式）
- [ ] 审批通知（统一邮件）
- [ ] 6 种业务场景接入：IQC不合格 / 让步接受 / 紧急上机 / 试产不合格 / 报废 / 解封
- [ ] approved / rejected 决策记录
- [ ] 单元测试覆盖

---

## Phase 5 — 仓储 / 维保 / 成本 / 甘特图

- [ ] 货架绑定与库位管理
- [ ] 领用归还历史
- [ ] 维保模块（保养 + 维修）
- [ ] 成本字段录入与查看权限
- [ ] 甘特图（Frappe Gantt + 100+ 自动降级）
- [ ] 计划日期推算与级联重算

---

## Phase 6 — 告警 / 报表导出 / 系统管理

- [ ] 邮件告警（send_alert_dedup + 事务隔离）
- [ ] 告警去重表 + 紧急阈值 3 天
- [ ] 报表导出三档策略(第一档前端 / 第二档后端流式 / 第三档 APScheduler 月度预生成)
- [ ] APScheduler 月度大报表定时任务(每月 1 日 02:30)+ 结果存 attachments
- [ ] 用户管理 / 角色字典
- [ ] 治具模板库管理
- [ ] 供应商库管理
- [ ] LT 默认值维护
- [ ] 审计日志查询

---

## Phase 7 — 部署与上线

- [ ] 生产机完整空跑（至少 1 次）
- [ ] 数据库迁移到生产
- [ ] 种子数据写入
- [ ] NSSM 注册服务
- [ ] 备份任务计划配置
- [ ] 防火墙规则配置
- [ ] 完整还原演练（备份 → 还原 → 校验）
- [ ] 业务冒烟测试
- [ ] 用户培训
- [ ] 正式上线

---

## 总工期估算

**13 ~ 17 周**（基于 V1.4 第 5.1 节）

---

## 修订记录

| 日期 | 内容 | 操作人 |
|------|------|--------|
| YYYY-MM-DD | 初始化任务清单（基于 V1.4 第 5.1 节） | — |
| 2026-04-29 | 补充 Migration 建表步骤；标记 Docker MySQL 已完成 | Frank |
| 2026-04-30 | Phase 0.3 前 12 条完成：项目骨架 + create_app + 三套配置 + 日志 + Migration 建表验收 | Claude |
| 2026-04-30 | Phase 0.3 全部完成：JWT 登录四端点 + 异常类 + 响应工具 + @require_role + errorhandler + APScheduler + user_roles Migration | Claude |
| 2026-04-30 | 修复三项：user_roles 补 utf8mb4 charset（Migration d3b83cd57489）；auth_service.py 移至 app/services/；TASKS.md 补 JWT blocklist 未完成项 | Claude |
| 2026-04-29 | CLAUDE.md §d / §e / §h 同步补入 4 条 Phase 0.3 实战教训（dotenv 顺序 / 关联表 charset / StaleDataError 路径 / 异常命名） | Frank |
| 2026-05-02 | Phase 0.4 完成：Supplier + FixtureTemplate 两个 Model + Migration 24fbd93c72dc + seed_data.py（10 角色 / 12 状态 / 6 设备代号 / 11 供应商 / 42 治具模板）三步验收通过（首跑 / 幂等 / --reset） | Claude |
| 2026-05-10 | Phase 0.5 完成：Doc/09_dev_rules.md 内容对齐 CLAUDE.md 2026-04-29 修订记录的 4 条 Phase 0.3 实战教训（后端 #1/#7/#11 子条 + 命名约定表"自定义异常类"行）+ Checklist 4 项 + 文末新增"六、修订记录"；路径修正 7 处显示文本 `docs/` → `Doc/`；CLAUDE.md §j 同步登记 | Claude |
| 2026-05-10 | Phase 0.1 全部完成：Python 3.12 / Node.js LTS + pnpm / Git / .env.development 模板 / Docker MySQL 连接验证 | Frank |
| 2026-05-10 | Phase 0.6 完成：Vue 3 + ElementPlus + Pinia + Router 项目初始化、utils/storage.js token 封装、parseBackendTime 工具、axios 401/409 拦截器、登录/主框架/Home/NotFound 视图、eslint 拦截规则（dayjs 裸调 + @/ 路径）；pnpm build 编译通过；eslint 拦截验证通过；联调登录冒烟测试通过 | Claude |
| 2026-05-10 | Phase 0.7 进行中：联调登录通过；TASKS.md / CLAUDE.md 更新进度同步 | Claude |
| 2026-05-10 | Phase 0 全部完成：0.2 生产机预演 9 项 + 0.7 CI(.github/workflows/ci.yml) + 团队 review 全部勾选；当前阶段切换至 Phase 1 | Frank |
