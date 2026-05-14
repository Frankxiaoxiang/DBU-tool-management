# 开发铁律 / 开发规范

> 摘自 V1.4 架构文档第 5.3 节（CLAUDE.md 专属规则）和第 5.4 节（风险点缓解措施）。
>
> **本文件为后端 11 条 + 前端 8 条铁律的权威来源**。Code Review 必须逐项核对。

---

## 一、后端 11 条铁律

### 后端 #1：配置与环境

- **必须**：使用 `python-dotenv` 加载 `.env.development` / `.env.production` / `.env.example` 三套配置；`config.py` 不硬编码任何密码或密钥。
- **必须**：`load_dotenv()` 在 `app/__init__.py` **模块顶层**执行，且**早于** `from config import CONFIG_MAP`（Config 类体在 import 阶段已读取 `os.environ`，延迟到 `create_app()` 内部会让 Config 永远拿到 `None` 且无报错日志，极难调试）。
- **禁止**：将 `.env.*` 提交到 git；在代码里直接 `os.environ['DATABASE_URL']` 之外的方式硬编码连接串。
- **禁止**：在 `create_app()` 函数内部首次调用 `load_dotenv()`。

### 后端 #2：禁止物理删除核心表

- **必须**：`projects` / `batches` / `fixtures` / `purchase_orders` 等核心表的"作废"走 `status='cancelled'`；配置型表（users / suppliers / fixture_templates）走 `is_active=FALSE`。
- **禁止**：在 Blueprint 中定义 `methods=['DELETE']` 路由删除核心表数据；真·删除仅 `scripts/reset_db.py` 提供。

### 后端 #3：状态机三函数职责清晰

- **必须**：状态变更走 `services/state_machine.py` 提供的 `transition()` / `reject()` / `force_transition()` 三个函数；`force_transition()` 必填 reason 并自动写审计日志。
- **禁止**：`transition()` 函数签名包含 `force` / `bypass` 参数；任何代码直接 `fixture.current_status = ...`；改流程时漏改 5 处（state_machine.py / status_history 表 / 前端 status.js / i18n / 文档）。

### 后端 #4：编码与版本

- **必须**：编码由后端 `services/code_generator.py` 生成，遵循《编码规则 V1.0》；版本升级（A1→A2 等）只改图纸版本字段，不新建 fixture；加开-加量复制时 `current_version_code` 继承源治具。
- **禁止**：在前端拼接编码；版本升级时新建一条 fixture 记录。

### 后端 #5：审批流双模式

- **必须**：所有审批流（IQC不合格/让步接受/紧急上机/试产不合格/报废/解封）共用一套引擎，通过 `flow_type + sequential_or_parallel` 区分；`approved` 与 `rejected` 都透传 `decision_type` 字段。
- **禁止**：为每种业务场景写独立审批流代码；审批通知用非邮件方式（MVP 阶段）。

### 后端 #6：快照机制

- **必须**：项目创建时锁定模板快照写入 `project_template_snapshots`；模板库后续修改时通过 `sync_missing_templates()` 仅追加同步（不覆盖已有）；同步操作必须写审计日志。
- **禁止**：模板修改时反向更新已有项目的快照；快照与模板库使用同一张表。

### 后端 #7：乐观锁仅手动校验

- **必须**：所有写操作请求体含 `version` 字段；Service 层手动比对 `record.version != request_version` 失败抛 `ConflictError(409)`；提交前手动 `record.version += 1`；全局 `@errorhandler(StaleDataError)` 兜底返回 409。
- **必须**：`StaleDataError` 导入路径为 `from sqlalchemy.orm.exc import StaleDataError`（SQLAlchemy 2.x）。
- **禁止**：在任何 Model 上加 `__mapper_args__ = {'version_id_col': version}`（V1.1/V1.2/V1.3 错误设计已纠偏）；用 `body.get('version')` 静默接受 None。
- **禁止**：写成 `from sqlalchemy.exc import StaleDataError`（2.x 已移除该路径，会 `ImportError`，errorhandler 注册失败，乐观锁冲突变成 500 且无报错日志）。

### 后端 #8：邮件告警事务隔离

- **必须**：所有告警发送走 `services/alert_service.py:send_alert_dedup()`；该函数必须 `try/except` 包裹完整逻辑，失败时 `db.session.rollback()` + `logger.error()`，**不抛出**；循环调用场景下单封邮件失败不株连后续。
- **禁止**：在 `check_all_alerts` 等循环任务中让异常向上传播；用 `mail.send` 之外的方式发邮件而绕过去重表。

### 后端 #9：报表导出限制

- **必须**：按 V1.3 三档分类(第一档前端 SheetJS / 第二档后端 `openpyxl(write_only=True)` 流式 / 第三档 APScheduler 月度预生成);第二档及以上必须用 `openpyxl` 的 **`Workbook(write_only=True)`** 模式 + 数据库游标分批查询。详见 [Doc/07_export_guideline.md](./07_export_guideline.md)。
- **禁止**：使用 `pandas.DataFrame.to_excel()`；使用 `openpyxl` 默认（非 write_only）模式；`query.all()` 一次性加载万行数据；任何"用户触发异步导出 + 邮件下载链接 / 状态轮询"工作流。

### 后端 #10：日志切割

- **必须**：`create_app()` 中配置 `TimedRotatingFileHandler`，按天切割，`backupCount=30`；NSSM 的 stdout/stderr 仅作为兜底（配 10MB 切割）。
- **禁止**：依赖 NSSM 单一文件做长期日志记录；用 `print` 代替 logger。

### 后端 #11：连接池参数与 ORM API

- **必须**：`SQLALCHEMY_ENGINE_OPTIONS` 配 `pool_pre_ping=True`、`pool_recycle=3600`、`pool_size=10`、`max_overflow=20`；连接串含 `?charset=utf8mb4`；`init_command="SET time_zone='+08:00'"`。
- **必须**：多对多关联表 `db.Table('xxx', ...)` 显式传 `mysql_charset='utf8mb4'` + `mysql_collate='utf8mb4_unicode_ci'`（关联表不走 Model 的 `__table_args__`，生产 MySQL server 默认非 utf8mb4 时会建出错误 charset 的表）。
- **必须**：主键查询用 SQLAlchemy 2.x 新 API `db.session.get(Model, pk)`，**禁止**使用废弃写法 `Model.query.get(pk)`（产生 `LegacyAPIWarning`，SQLAlchemy 3.x 将彻底移除）。
```python
# ✅ SQLAlchemy 2.x 正确写法
project = db.session.get(Project, project_id)
owner   = db.session.get(User, owner_id)

# ❌ 废弃 API — 触发 LegacyAPIWarning
project = Project.query.get(project_id)
```
- **禁止**：使用默认连接池配置（MySQL `wait_timeout=28800` 后连接假死）；忽略 charset 设置（中文乱码）。

---

## 二、前端 8 条铁律

### 前端 #1：时间处理统一走 parseBackendTime

- **必须**：处理后端返回的 datetime 字符串一律通过 `utils/datetime.js` 的 `parseBackendTime(str)` / `formatBackendTime(str, fmt)`；`main.js` 顶层 `import './utils/datetime'` 副作用导入确保 `setDefault('Asia/Shanghai')` 生效。
- **禁止**：裸调用 `dayjs(str)` 或 `new Date(str)`（浏览器按本地时区解析，海外/异地访问会出现时间偏差）。

### 前端 #2：禁止前端直接 DELETE 核心表

- **必须**：核心表的"作废"通过 `POST /api/.../cancel` 或 `PUT /api/...` 改 `status` 字段实现；用 `ElMessageBox.confirm` 二次确认。
- **禁止**：前端调用 `axios.delete('/api/projects/:id')` 等核心表 DELETE 接口（接口本身也不应存在）。

### 前端 #3：409 统一拦截

- **必须**：`api/request.js` 的 axios response 拦截器统一捕获 409，弹 `ElMessageBox.alert` 提示"数据已被他人修改"，确认后 `window.location.reload()`。
- **禁止**：在每个组件内独立处理 409；让 409 错误进入业务 catch 与其他错误混淆。

### 前端 #4：甘特图自动降级

- **必须**：使用 Frappe Gantt；当条目数 > 100 时自动降级为简化表格视图（带"展开为甘特图"按钮）。
- **禁止**：100+ 条目仍渲染完整 SVG 甘特图（卡顿）；引入更重的甘特图库（如 dhtmlx-gantt 商业版）。

### 前端 #5：状态颜色集中维护

- **必须**：12 种治具状态的颜色映射定义在 `utils/status.js` 中作为单一来源，组件通过 import 引用；`el-tag` 的 `:color` 属性统一从该映射读取。
- **禁止**：在多个组件分别定义状态颜色；使用 Element Plus `el-tag` 的 `type` 内置类型（颜色不够 12 种区分）。

### 前端 #6：权限按钮派生自 permissions.js

- **必须**：所有页面/按钮的可见性通过 `stores/auth.js` 的 `hasPermission(action)` 判断；`permissions.js` 派生自 [Doc/05_permissions.md](./05_permissions.md) 的权限矩阵。
- **禁止**：在每个组件内硬编码角色判断（如 `if (role === 'pm')`）；前端权限作为唯一防线（必须后端独立校验）。

### 前端 #7：eslint 规则建议

建议在 `.eslintrc` 中加入以下自定义规则（拦截常见违规）：

```javascript
rules: {
  // 禁止裸 dayjs(str) / new Date(str)
  'no-restricted-syntax': [
    'error',
    {
      selector: "CallExpression[callee.name='dayjs'][arguments.0.type='Identifier']",
      message: '请使用 utils/datetime 的 parseBackendTime 处理后端时间字符串'
    },
    {
      selector: "NewExpression[callee.name='Date'][arguments.0.type='Identifier']",
      message: '请使用 utils/datetime 的 parseBackendTime 处理后端时间字符串'
    }
  ],
  // 禁止使用 @/ 路径别名（vite 未配置）
  'no-restricted-imports': [
    'error',
    { patterns: ['@/*'] }
  ],
}
```

### 前端 #8：报表导出严格对齐 V1.3 三档

- **必须**：单表列表 < 1000 条用前端 `xlsx` (SheetJS) 库直接生成；多表关联或 > 1000 条调后端流式接口（`GET /api/projects/export`、`GET /api/fixtures/export`）；月度大报表通过 APScheduler 每月 1 日 02:30 预生成，用户去附件中心下载。
- **禁止**：前端 `xlsx` 库导出 1000 行以上（浏览器卡崩）；前端通过 `JSON.stringify` 拼接巨型 CSV 触发下载；**任何"用户触发的异步导出 + 邮件下载链接 / 状态轮询"工作流**（V1.3 明确不采用此模式）。详见 [Doc/07_export_guideline.md](./07_export_guideline.md)。

---

## 三、命名约定（继承自 vc-cost-system）

| 类型 | 规范 | 示例 |
|------|------|------|
| Python 文件 | snake_case | `fixture_service.py` |
| Python 类 | PascalCase | `FixtureTemplate` |
| Python 函数 / 变量 | snake_case | `get_fixture_by_code` |
| 数据库表名 | snake_case 复数 | `fixture_templates` |
| 数据库字段 | snake_case | `project_owner_id` |
| API 路由 | kebab-case | `/api/fixture-templates` |
| Vue 组件 | PascalCase | `FixtureStatusTag.vue` |
| CSS 类 | kebab-case | `status-badge` |
| 代码注释 | 英文 | `# Calculate planned arrival date` |
| 业务术语注释 | 中文 | `# 治具入库后绑定库位` |
| 自定义异常类 | PascalCase + `Error` 后缀，**不与 Python 内置异常名冲突** | ✅ `ConflictError` / `ForbiddenError` / `ValidationError` / `NotFoundError`；❌ `PermissionError` / `ValueError` / `TypeError` / `NotImplementedError` |

---

## 四、Code Review Checklist

提交 PR / Code Review 时逐项核对：

### 通用

- [ ] 改动是否更新到 Doc/ 下的对应文档？
- [ ] 改动是否需要更新 CLAUDE.md 或 TASKS.md？
- [ ] 单元测试是否覆盖关键路径？

### 后端

- [ ] 数据库 Schema 变更是否走 Flask-Migrate（无手动 ALTER TABLE）？
- [ ] 写操作是否有 `version` 字段比对（手动乐观锁）？
- [ ] Model 中是否**没有** `__mapper_args__ = {'version_id_col': version}`？
- [ ] 状态变更是否走三函数（`transition` / `reject` / `force_transition`），无 `force=True` 后门？
- [ ] 核心表是否未引入 `methods=['DELETE']` 路由？
- [ ] 邮件告警是否走 `send_alert_dedup` 且包 try/except 不抛出？
- [ ] 报表导出是否未用 `pandas.to_excel` 与 `openpyxl` 默认模式？
- [ ] 文件路径是否用 `pathlib.Path` 跨平台处理？
- [ ] Blueprint 是否未在定义和注册时双重设置 prefix？
- [ ] JWT identity 是否强转 int？
- [ ] PUT/PATCH 是否用 `'key' in body` 判断而非 `body.get()`？
- [ ] `app/__init__.py` 顶层是否已 `load_dotenv(...)` 且**早于** `from config import CONFIG_MAP`？
- [ ] 多对多关联表 `db.Table(...)` 是否显式传 `mysql_charset='utf8mb4'` + `mysql_collate='utf8mb4_unicode_ci'`？
- [ ] `StaleDataError` 导入路径是否为 `from sqlalchemy.orm.exc`（而非 `sqlalchemy.exc`）？
- [ ] 自定义异常类是否避开 Python 内置异常名（`grep -RIn "class PermissionError\|class ValueError\|class TypeError\|class NotImplementedError"` 应无匹配）？
- [ ] 主键查询是否用 `db.session.get(Model, pk)` 而非废弃的 `Model.query.get(pk)`（`grep -RIn "\.query\.get(" app/services/` 应无匹配）？

### 前端

- [ ] 时间显示是否走 `parseBackendTime` / `formatBackendTime`？
- [ ] 是否未使用 `@/` 路径别名（用相对路径）？
- [ ] `el-tag` 等 type prop 是否有合法兜底（`|| 'info'` 而非 `|| ''`）？
- [ ] `ElMessageBox.confirm` 是否用二段 try/catch（用户取消静默退出）？
- [ ] `v-for` 可编辑表格是否用 `_temp_id` 而非 index 作 key？
- [ ] JWT token 是否过滤 `'undefined'` / `'null'` 字符串？
- [ ] 元素是否未直接 `axios.delete` 核心表？
- [ ] 按钮可见性是否通过 `hasPermission()` 控制？

---

## 五、引用关系

- **乐观锁原则** → [架构文档第 2.9 节](./03_architecture_v1.4.md)
- **状态机实现** → [架构文档第 3.3 节](./03_architecture_v1.4.md)
- **告警去重** → [架构文档第 3.6 节](./03_architecture_v1.4.md)
- **导出三档** → [Doc/07_export_guideline.md](./07_export_guideline.md)
- **权限矩阵** → [Doc/05_permissions.md](./05_permissions.md)
- **API 规约** → [Doc/04_api_spec.md](./04_api_spec.md)

---

## 六、修订记录

| 日期 | 内容 | 操作人 |
|------|------|--------|
| 2026-05-10 | Phase 0.5 落位：① 路径修正（全文 `docs/` 显示文本统一为 `Doc/` 共 7 处）；② 内容对齐 CLAUDE.md 2026-04-29 修订——后端 #1 补 dotenv 顺序、#7 补 `StaleDataError` 2.x 路径、#11 补 `db.Table()` 关联表 charset、命名约定表新增"自定义异常类"行、Checklist 后端段新增 4 项核对 | Claude |
| 2026-05-13 | Phase 1 Step 1-1-3 实战补入：后端 #11 标题扩为"连接池参数与 ORM API"，新增 `db.session.get(Model, pk)` 替代废弃 `Model.query.get(pk)` 规则（附代码示例）；Checklist 后端段新增 1 项核对 | Claude |
