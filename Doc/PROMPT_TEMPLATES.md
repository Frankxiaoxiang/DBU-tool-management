# PROMPT_TEMPLATES.md — DBU 模治具管理系统 CLI 提示词模板库

> 本文件是 Frank 与 CLI AI（Claude Code / Cursor / Copilot 等)协作的**提示词模板库**。
>
> **使用规则**:
> 1. 选模板 → 替换 `[变量]` → 粘贴给 CLI AI。
> 2. 所有模板均假设 CLI AI 已加载 `CLAUDE.md`、`Doc/09_dev_rules.md`、`Doc/04_api_spec.md`、`Doc/03_architecture_v1.4.md`、`TASKS.md` 至工作上下文(亦可使用 **T00 — 会话启动与上下文同步** 强制完成)。
> 3. 模板中的"⛔ 动作纪律"标记是**强制断点**——禁止 CLI AI 跨越,必须等 Frank 回复 `go` 才能继续。
> 4. 模板内引用的 `CLAUDE.md` / `09_dev_rules.md` 章节号以这两份文档当前版本为准,改版时同步刷新本库。
> 5. **环境要求**:验收防线中的 `grep` 命令优先由 **CLI AI 内置检索工具**(`grep` / `Grep` / `ripgrep` 等)执行;Frank 在本地手动复核时,需在 **Git Bash / WSL / Cmder** 等 POSIX 兼容 shell 中运行,**Windows 原生 PowerShell** 会因语法不兼容失败(如 `\(` 转义、单引号双引号嵌套规则不同)。
>
> **职责边界**:
> - **T01**:仅 Model + Migration,**不写** Service / API。
> - **T02**:仅 Service + Blueprint,**不动** Model 定义、**不建** 新表。
> - **T03 / T04**:仅前端,**不改** 后端接口。
> - **T05**:状态机专项,涉及前后端 + 文档 5 处联动。
> - **T06**:Bug 修复,以"先根因后动手"为铁律。
> - **T07**:单元测试,**不修改**被测代码。

---

## 模板总览

| 编号 | 名称 | 适用阶段 |
|------|------|----------|
| **T00** | **会话启动与上下文同步** | **每次新 CLI 会话第一条** |
| T01 | 新建后端 Model + Migration | Phase 1+ 每个新业务表 / 字段变更 |
| T02 | 新建后端 Service + Blueprint API 端点 | Phase 1+ 每个新业务模块 |
| T03 | 新建 Vue 列表页(含搜索栏 + 分页) | Phase 1+ 每个新业务模块 |
| T04 | 新建 Vue 表单页(新增/编辑/详情) | Phase 1+ 每个新业务模块 |
| T05 | 状态机相关开发(transition / reject / force_transition) | Phase 2 / Phase 3 流程节点 |
| T06 | Bug 修复分析与执行 | 任何阶段 |
| T07 | 单元测试生成 | Phase 1+ 每个 Service / 状态机变更 |

---

## T00 - 会话启动与上下文同步

### 适用场景

**每次新开一个 CLI 会话(或经过一段长时间后重新接续)的第一条提示词**。强制 CLI AI 在动手任何编码任务前完成 5 件事:加载权威文档 → 复述铁律 → 对齐当前阶段 → 报告环境状态 → 等待 Frank 拍板下一步。

> **这不是"客套话"模板**:CLI AI 上下文窗口刷新后会忘记 CLAUDE.md;新开会话不跑 T00 → 高概率违反铁律,需返工。**T00 是开发会话的"开机自检"**。

### 需准备的参数清单

| 变量 | 含义 | 示例 |
|------|------|------|
| `[Phase_Number]` | 当前推进的 Phase | `1` |
| `[今日任务意图]` | 一句话描述本次会话准备做什么(可留空,T00 跑完再决定) | `推进项目 CRUD 后端` |

### 提示词正文

```text
# 任务:会话启动与上下文同步(T00)

## 上下文
- 当前阶段:Phase [Phase_Number]
- 今日任务意图(待 T00 完成后确认):[今日任务意图]
- 本任务范围:加载权威文档 + 复述铁律 + 报告环境状态;**不写任何代码**

## 【开发动作】

**Step 1 — 加载权威文档**(逐个 view,贴出文件路径 + 修订记录最后一行):
   1. `CLAUDE.md` — §a~§j 全文,重点 §d / §e / §h
   2. `Doc/09_dev_rules.md` — 后端 11 条 + 前端 8 条 + 命名约定 + Checklist
   3. `Doc/04_api_spec.md` — 通用响应 / 通用约束 8 条 / 端点清单
   4. `Doc/03_architecture_v1.4.md` — 第 2 章数据模型 + 第 3.3 节状态机
   5. `TASKS.md` — 当前阶段勾选状态 + 最近 3 条修订记录
   6. `Doc/PROMPT_TEMPLATES.md` — 模板总览(本文件)

**Step 2 — 铁律复述**(用自己的话,**不许照抄**;每条不超过 30 字):
   按以下清单逐条 1 句话复述(§d + §e 共 26 条;09_dev_rules.md 后端 11 + 前端 8 = 19 条由各模板验收防线 grep 逐项覆盖,此处不重复):
   - CLAUDE.md §d Rule 1~14(继承自 vc-cost-system 的 14 条 critical rules)
   - CLAUDE.md §e.1~e.12(V1.4 专属 12 条)

   若发现任何一条**与最近代码现状冲突**(如代码里发现违反铁律的遗留),**红色标注**并停下来等 Frank 确认是否纳入今日修复范围。

**Step 3 — 当前阶段对齐**:
   读 TASKS.md,告诉我:
   - 当前 Phase 是哪个?完成度多少?(✅ / 🟢 / ⬜)
   - **未勾选**项中,哪 1-3 项是逻辑上的"下一步"?(说明依赖关系)
   - 是否有跨 Phase 的遗留项(如 Phase 0 的 "JWT logout 服务端撤销" 留到 Phase 1)?

**Step 4 — 环境与代码现状速查**(执行并贴输出):

   ```bash
   # 后端
   cd backend
   flask db current        # 当前 Migration head
   flask db heads          # 所有 head(应只有 1 个;多个 head 是状态污染信号)
   git status --short      # 工作区脏文件
   git log -1 --oneline    # 最近一次提交

   # 前端
   cd ../frontend
   git status --short
   ls -la src/utils/       # 确认 datetime.js / status.js(若已建)/ request.js 等基础设施
   ```

   附加自查 grep(快速验证铁律未被破坏):
   ```bash
   # 严重违规速查(任何一条非 0 都是阻塞)
   grep -RIn "version_id_col" backend/app/models/                                    # 期望 0
   grep -RIn "from sqlalchemy.exc import StaleDataError" backend/app/                # 期望 0
   grep -RIn "class \(PermissionError\|ValueError\|TypeError\|NotImplementedError\)" backend/app/  # 期望 0
   grep -RIn "from ['\"]@/" frontend/src/                                            # 期望 0
   grep -RIn "methods=\['DELETE'\]" backend/app/blueprints/                          # 期望 0(或限非核心表)
   ```

**Step 5 — 任务建议**:
   基于以上 Step 1~4,给我一份**结构化报告**:

   ```markdown
   ## T00 会话启动报告 — YYYY-MM-DD

   ### 1. 文档加载
   - ✅ CLAUDE.md(最后修订:2026-05-10)
   - ✅ 09_dev_rules.md(最后修订:2026-05-10)
   - ✅ 04_api_spec.md
   - ✅ 03_architecture_v1.4.md
   - ✅ TASKS.md(当前 Phase 1 进行中)
   - ✅ PROMPT_TEMPLATES.md

   ### 2. 铁律复述(共 26 条，§d + §e)
   [按 §d Rule 1 → §e.12 顺序,每条 1 句]

   ### 3. 当前阶段对齐
   - 当前阶段:Phase 1(进行中)
   - 已完成:[列出 TASKS.md 已勾选项]
   - 逻辑下一步建议(前 3):
     1. ???(依赖:???,推荐模板:T01)
     2. ???
     3. ???
   - 跨 Phase 遗留:[列出]

   ### 4. 环境与代码现状
   - Migration head:[xxx](单 head ✅)
   - Git 状态:[clean / 有未提交改动:列出]
   - 严重违规速查 5 条 grep:[全部 0 ✅ / 有违规:列出]

   ### 5. 风险提示
   [若任何 grep 非 0、有 Migration 多 head、铁律与现状冲突,在此红色标注]

   ### 6. 等待指令
   今日任务意图:[今日任务意图]
   建议接下来跑哪个模板?(T01 / T02 / ... / T07)
   或先处理风险提示?
   ```

## 【⛔ 动作纪律 — 在此处打断点】

**禁止**未经我回复 `go-<模板编号>`(如 `go-T01`)就动手写代码、改 Model、生成 Migration、跑 pnpm dev、动 git commit。
**禁止**自行选定"今日任务意图"并直接进入实现——必须等我看完 T00 报告后明确指派。
**禁止**在 T00 报告中跳过任何一项("文档加载"的 6 项、铁律复述、grep 5 条都必须全跑全贴)。

## 【验收防线】

T00 不产出代码,验收即"报告 6 段完整 + 5 条 grep 输出 = 0 违规"。
若 grep 任意一项非 0,**视为发现既有 bug**,需走 T06 修复,然后才能进入"今日任务意图"。
```

### 使用示例(填充 Phase 1 第一次接续会话)

```text
# 任务:会话启动与上下文同步(T00)

## 上下文
- 当前阶段:Phase 1
- 今日任务意图:推进项目 CRUD 后端(T01 + T02 + T07)
- 本任务范围:加载权威文档 + 复述铁律 + 报告环境状态;不写任何代码

## 【开发动作】
[同正文 Step 1~5]

## 【⛔ 动作纪律 — 打断点】[同正文]

跑完 T00 给我报告后,我会回:
- `go-T01` → 进入新建 Project Model + Migration
- 或 `先修 grep` → 走 T06 修复
- 或 `调整意图` → 重新对齐
```

---

## T01 - 新建后端 Model + Migration

### 适用场景

当 Phase 1+ 需要**新增一张业务表**或**修改现有表的字段结构**(加字段 / 改类型 / 加索引 / 加约束 / 改 默认值)时使用。**仅**覆盖 ORM Model 定义、Alembic 迁移生成与执行,**不**包含 Service、Blueprint、单元测试、前端(分别走 T02 / T07 / T03 / T04)。

> **特别注意**:若本次是删字段 / 改字段类型导致数据丢失风险(如 VARCHAR(128) → VARCHAR(64)),**必须**在 Step 5 审查报告中标红,并附数据迁移策略。涉及数据迁移的 Migration **禁止**在 dev 库以外的环境直接 upgrade,需先经 Frank 评审。

### 需准备的参数清单

| 变量 | 含义 | 示例 |
|------|------|------|
| `[Entity_Name]` | 实体类名(PascalCase) | `Project` / `Batch` / `Fixture` |
| `[table_name]` | 物理表名(snake_case 复数) | `projects` / `batches` / `fixtures` |
| `[entity_filename]` | Model 文件名(snake_case 单数) | `project` / `batch` / `fixture` |
| `[字段清单]` | 字段:名 / 类型 / 可空 / 默认值 / 外键 / 索引 | 见下方使用示例 |
| `[table_kind]` | `core`(核心表) / `config`(配置表) / `business_record`(业务单据) | `core` |
| `[Phase_Number]` | 当前 Phase | `1` |
| `[arch_doc_section]` | 架构文档对应章节号 | `2.3 项目与批次模型` |

### 提示词正文

```text
# 任务:新建 Model + Migration — [Entity_Name]

## 上下文
- 当前阶段:Phase [Phase_Number]
- 本任务范围:Model 定义 + Alembic 迁移生成 + 人工审查 + flask db upgrade
- 不在本任务范围:Service / Blueprint / 单元测试 / 前端(分别走 T02 / T07 / T03 / T04)
- 表归类:[table_kind]

## 【文档约束】开工前必须复述以下条款,缺一不可

请逐条用一句话点头确认你已读懂,**不许跳过**:

1. **CLAUDE.md §d Rule 1 + 09_dev_rules.md 后端 #11**:utf8mb4 强制
   - Model 必须 `__table_args__ = {'mysql_charset': 'utf8mb4', 'mysql_collate': 'utf8mb4_unicode_ci'}`
   - 多对多关联表 `db.Table(...)` **必须显式**传 `mysql_charset='utf8mb4'` + `mysql_collate='utf8mb4_unicode_ci'`(关联表不走 Model 的 __table_args__,生产 MySQL server 默认非 utf8mb4 时会建出错误 charset 的表)

2. **CLAUDE.md §d Rule 2**:Schema-First
   - `flask db migrate` 生成的脚本必须**人工审查**才能 upgrade
   - 严禁手动 ALTER TABLE

3. **CLAUDE.md §e.3 + §e.12 + 09_dev_rules.md 后端 #2**:删除策略
   - `core` 表必须有 `status` 字段,作废走 `status='cancelled'`,**禁止**建 DELETE 路由
   - `config` 表必须有 `is_active` 布尔字段
   - `business_record` 表(IQC/验收/维修记录等)只增不改不删

4. **CLAUDE.md §e.5 + 09_dev_rules.md 后端 #7**:乐观锁仅手动校验
   - 凡是有 PUT/PATCH 接口的表,Model 必须含 `version INT NOT NULL DEFAULT 1`
   - **严禁**在 Model 上加 `__mapper_args__ = {'version_id_col': version}`(ORM 自动版会与手动版冲突)

5. **09_dev_rules.md 命名约定**:
   - Python 类 PascalCase;表名 snake_case **复数**;字段 snake_case
   - 业务术语注释用中文,代码逻辑注释用英文
   - 自定义异常类不得撞 Python 内置(`PermissionError` / `ValueError` / `TypeError` / `NotImplementedError`)

6. **CLAUDE.md §h 风险点**:写代码前 `grep -RIn "version_id_col" backend/app/models/` 必须无匹配

## 【开发动作】

**Step 1 — 字段对齐**:
   阅读 Doc/03_architecture_v1.4.md 第 [arch_doc_section] 节中 [Entity_Name] 的字段定义,
   与下方字段清单逐字段对照,**差异**列在对话里等我确认,**不准擅自决断**。

   字段清单:
   [字段清单]

**Step 2 — 编写/修改 Model**:
   在 `backend/app/models/[entity_filename].py` **创建**(新表)或**修改**(已有表):
   - 字段清单:[字段清单]
   - **新建表**额外要求(按 [table_kind]):
     - 核心表:`id`(BigInteger PK)/ `created_at` / `updated_at` / `created_by`(FK users.id) / `status` / `version`
     - 配置表:`id` / `created_at` / `updated_at` / `is_active`(BOOLEAN default=TRUE)
     - 业务单据表:`id` / `created_at` / `created_by`(只增不改不删,不要 version)
   - **修改字段**额外要求:
     - 若给已有表加 PUT/PATCH 写接口,必须确认 Model 已含 `version` 字段;若无,本次顺带加上
     - 改字段类型若有数据丢失风险(缩窄长度 / 类型变更),需提供数据迁移策略
   - 加 `__table_args__` utf8mb4
   - 若涉及多对多关联表,用 `db.Table()` **显式**传 charset + collate

**Step 3 — 导出 Model**:
   在 `backend/app/models/__init__.py` 中 `from .[entity_filename] import [Entity_Name]`

**Step 4 — 生成迁移**:
   `flask db migrate -m "Phase [Phase_Number]: add [table_name] table"`

**Step 5 — 迁移脚本审查报告**(必须以下方格式给我):
   - 文件名:migrations/versions/xxx_add_[table_name].py
   - down_revision 是否对得上当前 head?(`flask db current` 输出)
   - upgrade() 操作是否**完全符合本次变更预期**?**特别警示**:
     * 是否有意外的 `drop_table` / `drop_column`?(任何 drop 都要红色标注 + 等我确认)
     * 是否有类型缩窄(VARCHAR 长度变小 / INT → SMALLINT 等)?(需附数据兼容评估)
     * 若本次是改字段:新增的 `alter_column` / `add_column` 是否与字段清单 100% 一致?
     * 若本次是新建表:`create_table` 内列定义是否与字段清单 100% 一致?
   - 索引是否齐全?(外键列应自动建索引;高频查询列加显式 Index)
   - utf8mb4 是否生效?(`create_table` 调用应含 `mysql_charset='utf8mb4'` 参数,**或**通过 Model `__table_args__` 间接传递,需在 Step 7 用 `SHOW CREATE TABLE` 二次确认)

## 【⛔ 动作纪律 — 在此处打断点】

**禁止**未经我回复 `go` 就执行 `flask db upgrade`。
**禁止**自行修改既有 Migration 文件(只能在本次新生成的脚本里调整)。
等我回复 `go` 后再继续 Step 6。

## 【开发动作 续】

**Step 6 — 执行迁移**:
   `flask db upgrade`(贴出完整 stdout)

**Step 7 — 落地校验**:
   - `SHOW CREATE TABLE [table_name];` 贴输出,确认 `DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci`
   - `DESCRIBE [table_name];` 贴输出,逐字段核对类型与可空
   - 如有关联表:`SHOW CREATE TABLE <关联表名>;` 同样确认 charset

## 【验收防线】完工后必须执行以下 grep 并贴出输出

```bash
# 1. 严禁自动版乐观锁
grep -RIn "version_id_col" backend/app/models/
# 期望:无匹配

# 2. 关联表必须显式 charset(若本次新增关联表)
grep -A 4 "db.Table(" backend/app/models/[entity_filename].py
# 期望:每个 db.Table() 之后 4 行内必须有 mysql_charset='utf8mb4'

# 3. 自定义异常类不撞 Python 内置(本任务若顺手加了异常类)
grep -RIn "class \(PermissionError\|ValueError\|TypeError\|NotImplementedError\)" backend/app/
# 期望:无匹配

# 4. 核心表不得在 Blueprint 中提前出现 DELETE(防止上下文污染,本任务不应触发)
grep -RIn "methods=\['DELETE'\]" backend/app/blueprints/
# 期望:无匹配
```

## 【完工汇报】格式

- 新增 Model 文件:[路径]
- 新增 Migration 文件:[路径](down_revision = ???)
- upgrade 结果:✅ / ❌(失败原因)
- SHOW CREATE TABLE 输出:[贴]
- DESCRIBE 输出:[贴]
- 验收防线 4 条 grep 输出:[贴]
- 与架构文档的差异(若有):[逐项说明]
```

### 使用示例(填充 Phase 1 — 新建 `Project` Model)

```text
# 任务:新建 Model + Migration — Project

## 上下文
- 当前阶段:Phase 1
- 本任务范围:Project Model 定义 + Alembic 迁移生成 + 人工审查 + flask db upgrade
- 不在本任务范围:Service / Blueprint / 单元测试 / 前端
- 表归类:core

## 【文档约束】开工前必须复述以下条款,缺一不可

[同正文 6 条]

## 【开发动作】

Step 1 — 字段对齐:
   阅读 Doc/03_architecture_v1.4.md 第 2.3 节中 Project 的字段定义,
   与下方字段清单逐字段对照,差异列在对话里等我确认。

   字段清单:
     * id                BIGINT PK AUTO_INCREMENT
     * project_code      VARCHAR(32) UNIQUE NOT NULL  -- 系统按编码规则生成,不可前端拼接
     * project_name      VARCHAR(128) NOT NULL
     * product_type      VARCHAR(16) NOT NULL  -- 'SUS_VC' / 'CU_VC' / 'HP'
     * owner_id          BIGINT NOT NULL FK users.id  -- 项目负责人
     * status            VARCHAR(16) NOT NULL DEFAULT 'active'  -- active / cancelled
     * cancel_reason     VARCHAR(256) NULL
     * cancelled_at      DATETIME NULL
     * cancelled_by      BIGINT NULL FK users.id
     * planned_start_date DATE NULL
     * planned_end_date   DATE NULL
     * version           INT NOT NULL DEFAULT 1
     * created_at        DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
     * updated_at        DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
     * created_by        BIGINT NOT NULL FK users.id

Step 2 — 编写 Model:
   在 backend/app/models/project.py 创建 Project 类,加 utf8mb4 __table_args__,
   核心表必备字段已全部体现在字段清单中(无关联表)。

Step 3 — 导出 Model:
   backend/app/models/__init__.py 加 `from .project import Project`

Step 4 — 生成迁移:
   flask db migrate -m "Phase 1: add projects table"

Step 5 — 迁移脚本审查报告:[按正文格式给我]

## 【⛔ 动作纪律 — 在此处打断点】
[同正文]

Step 6 — flask db upgrade
Step 7 — SHOW CREATE TABLE projects; / DESCRIBE projects;

## 【验收防线】
[同正文 4 条 grep]

## 【完工汇报】
[同正文格式]
```

---

## T02 - 新建后端 Service + Blueprint API 端点

### 适用场景

在 T01 已建好 Model 之后,实现该业务模块的 CRUD API。**仅**覆盖 Service 层业务逻辑 + Blueprint 路由,**不**新建表(走 T01)、**不**写单元测试(走 T07)、**不**做前端(走 T03 / T04)。

### 需准备的参数清单

| 变量 | 含义 | 示例 |
|------|------|------|
| `[Entity_Name]` | 实体类名 | `Project` |
| `[entity_filename]` | 服务/蓝图文件名(snake_case) | `project` |
| `[resource_path]` | API 资源路径(kebab-case 复数) | `projects` |
| `[端点清单]` | 要实现的端点(方法 / 路径 / 说明) | 见使用示例 |
| `[权限矩阵]` | 每个端点的 `@require_role` 范围 | 见使用示例 |
| `[Phase_Number]` | 当前 Phase | `1` |

### 提示词正文

```text
# 任务:新建 Service + Blueprint — [Entity_Name]

## 上下文
- 当前阶段:Phase [Phase_Number]
- 前置条件:T01 已完成,[Entity_Name] Model + Migration 已 upgrade 通过
- 本任务范围:Service 层 + Blueprint 路由 + 注册到 app factory
- 不在本任务范围:新建 Model / 新建表 / 前端 / 单元测试(分别走 T01 / T03 / T04 / T07)

## 【文档约束】开工前必须复述以下条款,缺一不可

1. **Doc/04_api_spec.md 通用约束 8 条**(全部背诵):
   - 核心表禁止 HTTP DELETE,走 `PATCH .../cancel`
   - 配置表用 `PATCH .../deactivate` + `PATCH .../activate`
   - 写操作请求体必传 `version` 字段
   - 业务单据扁平化(`POST /api/iqc-reports`,不嵌套在 `/fixtures/:id/` 下)
   - 状态流转统一 `PATCH /api/fixtures/:id/status`,用 `trigger` 字段区分
   - JWT identity 强转 int:`user_id = int(get_jwt_identity())`
   - Blueprint 注册不重复前缀(Blueprint 定义**不带** url_prefix,注册时统一加 `/api/[resource_path]`)
   - PUT/PATCH 字段更新用 `'key' in body`,**禁止** `body.get('key')`(0 / null 会被静默吞掉)

2. **CLAUDE.md §e.5 + 09_dev_rules.md 后端 #7**:乐观锁手动校验
   - Service 层模板:
     ```python
     if record.version != body['version']:
         raise ConflictError("Conflict: modified by another user. Please refresh.")
     # ...业务字段更新...
     record.version += 1
     db.session.commit()
     ```
   - **严禁**用 `body.get('version')`,关键写入路径加 `assert request_version is not None` 守卫

3. **CLAUDE.md §e.4 + 09_dev_rules.md 后端 #3**:状态变更必须走 `services/state_machine.py`,**禁止**直接 `record.current_status = ...`(状态机专项走 T05)

4. **CLAUDE.md §e.3 + §e.12 + 09_dev_rules.md 后端 #2**:
   - **禁止** `methods=['DELETE']` 路由出现在核心表 Blueprint
   - 配置表只允许 `PATCH .../deactivate` + `PATCH .../activate`

5. **CLAUDE.md §e.11 + 09_dev_rules.md 后端 #9**:报表导出限制
   - 涉及导出端点(如 `GET /api/[resource_path]/export`)必须用 `openpyxl(write_only=True)` + DB 游标分批
   - **禁止** `pandas.to_excel()`、`query.all()` 一次性加载万行、`openpyxl` 默认模式
   - **禁止**"用户触发异步导出 + 邮件下载链接 / 状态轮询"工作流

6. **CLAUDE.md §d Rule 3**:Blueprint 定义不带 url_prefix:
   ```python
   # ✅ blueprints/[entity_filename].py
   [entity_filename]_bp = Blueprint('[entity_filename]', __name__)

   # ✅ app/__init__.py
   app.register_blueprint([entity_filename]_bp, url_prefix='/api/[resource_path]')
   ```

7. **09_dev_rules.md 命名约定**:
   - Service 文件:`backend/app/services/[entity_filename]_service.py`
   - Blueprint 文件:`backend/app/blueprints/[entity_filename].py`
   - 路由路径:kebab-case;Python 函数:snake_case

8. **CLAUDE.md §h 风险点**:自定义异常类不撞 Python 内置——HTTP 403 用 `ForbiddenError`,422 用 `ValidationError`,409 用 `ConflictError`,404 用 `NotFoundError`(Phase 0.3 已建好)

9. **统一响应**:走 `app/utils/responses.py` 的 `success_response(data, message='success')` / `error_response(code, message)`,**禁止**直接 `jsonify({...})`

10. **认证**:每个端点除 `/api/auth/*` 外必须 `@jwt_required()`;权限按 [权限矩阵] 加 `@require_role(...)`

## 【开发动作】

**Step 1 — 端点对齐**:
   阅读 Doc/04_api_spec.md 与下方端点清单对照,确认每个端点的方法 / 路径 / 请求体 / 响应体一致,差异列出来等我确认。

   端点清单:
   [端点清单]

   权限矩阵:
   [权限矩阵]

**Step 2 — Service 层**:
   创建 `backend/app/services/[entity_filename]_service.py`,每个端点对应一个函数:
   - `list_[resource]_with_filter(filters, page, page_size)` — 列表 + 分页
   - `get_[resource]_by_id(id)` — 详情(NotFoundError 兜底)
   - `create_[resource](payload, operator_id)` — 创建
   - `update_[resource](id, payload, operator_id)` — 编辑(乐观锁手动校验)
   - `cancel_[resource](id, reason, operator_id, version)` — 作废(核心表)/ deactivate / activate(配置表)

   Service 层**只**做业务编排,DB 提交在 Service 完成(`db.session.commit()`),
   Blueprint 层只做参数校验 + 调 Service + 包响应。

**Step 3 — Blueprint**:
   创建 `backend/app/blueprints/[entity_filename].py`:
   - `[entity_filename]_bp = Blueprint('[entity_filename]', __name__)` — **不带** url_prefix
   - 每个路由加 `@jwt_required()` + `@require_role(...)`
   - 参数解析用 `request.get_json(silent=True) or {}`
   - 更新接口必校验 `if 'version' not in body: raise ValidationError("version is required")`
   - PUT/PATCH 字段更新一律 `if 'xxx' in body:` 模式
   - 响应统一 `return success_response(data)`

**Step 4 — 注册 Blueprint**:
   在 `backend/app/__init__.py` 的 `create_app()` 函数 **⑤ 注册 Blueprint** 处追加:
   ```python
   from app.blueprints.[entity_filename] import [entity_filename]_bp
   app.register_blueprint([entity_filename]_bp, url_prefix='/api/[resource_path]')
   ```
   (与已有的 `auth_bp` 注册风格保持一致;`blueprints/__init__.py` 是空文件,**不要**在其中创建新函数)

**Step 5 — 自检稿件**:
   把 Service 文件和 Blueprint 文件完整贴在对话里,告诉我:
   - 每个端点的方法 / 路径 / 权限装饰器 / 是否带 version 校验
   - 是否有 DELETE 路由(应当无,除非是非核心表的特殊场景,需说明)
   - 是否有 `record.current_status = ...` 直接赋值(应当无,状态变更走 T05)
   - 是否有 `body.get('version')`(应当无,只允许 `body['version']` + 上方 ValidationError 守卫)

## 【⛔ 动作纪律 — 在此处打断点】

**禁止**未经我回复 `go` 就把 Blueprint 注册到 `app/__init__.py`。
原因:注册即生效,出错后路由会污染整个 dev server,排查成本高。
请把 Step 4 的 patch 单独贴给我,我看完回 `go` 再 commit。

## 【开发动作 续】

**Step 6 — 烟测**:
   启动 dev server,用 `curl` 或对话里给我的请求样例,对**至少** 3 个端点跑通(列表 / 创建 / 编辑 含 version 冲突 409),贴出 HTTP 响应。

## 【验收防线】完工后必须执行以下 grep 并贴出输出

```bash
# 1. 严禁 body.get('version')(0 / null 静默吞掉)
grep -RIn "body.get(['\"]version['\"]" backend/app/
# 期望:无匹配

# 2. 核心表 Blueprint 不得出现 DELETE
grep -RIn "methods=\['DELETE'\]" backend/app/blueprints/[entity_filename].py
# 期望:无匹配

# 3. 不得直接改 current_status(状态变更走 T05 state_machine.py)
grep -RIn "current_status\s*=" backend/app/services/[entity_filename]_service.py
# 期望:无匹配,或仅 state_machine.py 内部出现

# 4. Blueprint 不得自带 url_prefix(防止前缀翻倍)
grep -RIn "Blueprint(.*url_prefix" backend/app/blueprints/
# 期望:无匹配

# 5. JWT identity 必强转 int
grep -RIn "get_jwt_identity()" backend/app/
# 期望:每个调用点附近都有 int(...) 包裹

# 6. 自定义异常类不撞 Python 内置
grep -RIn "class \(PermissionError\|ValueError\|TypeError\|NotImplementedError\)" backend/app/
# 期望:无匹配

# 7. 报表导出端点(若本任务含)严禁 pandas / openpyxl 默认模式
grep -RIn "to_excel\|Workbook(" backend/app/services/[entity_filename]_service.py
# 期望:仅 `Workbook(write_only=True)` 形式,不得有裸 `Workbook(` 或 `to_excel`
```

## 【完工汇报】格式

- 新增 Service:[路径],含 N 个函数
- 新增 Blueprint:[路径],含 N 个端点
- Blueprint 注册位置:`backend/app/__init__.py` `create_app()` ⑤注册Blueprint处，第 X 行
- 烟测结果:[逐端点贴 curl + response]
- 验收防线 7 条 grep 输出:[贴]
- 偏离 04_api_spec.md 的地方(若有):[逐项说明并附原因]
```

### 使用示例(填充 Phase 1 — 项目 CRUD)

```text
# 任务:新建 Service + Blueprint — Project

## 上下文
- 当前阶段:Phase 1
- 前置条件:T01 已完成,Project Model + Migration 已 upgrade 通过
- 本任务范围:Service 层(project_service.py) + Blueprint(project.py) + 注册
- 不在本任务范围:新建表 / 前端 / 单元测试

## 【文档约束】开工前必须复述以下条款,缺一不可
[同正文 10 条]

## 【开发动作】

Step 1 — 端点对齐:
   阅读 Doc/04_api_spec.md 第 1.1 节"项目(无 DELETE)",与下方端点清单对照。

   端点清单(覆盖 Phase 1 项目 CRUD,不含甘特图 / 模板同步 / 导出 — 那些走 Phase 5 / Phase 6):
     * GET    /api/projects                  列表(支持 product_type / status / owner_id 过滤 + 分页)
     * POST   /api/projects                  新建(系统分配 project_code)
     * GET    /api/projects/:id              详情
     * PUT    /api/projects/:id              编辑(body 必含 version)
     * PATCH  /api/projects/:id/cancel       作废(body 必含 version 和 reason)
     * PUT    /api/projects/:id/owner        转移负责人(body 必含 version 和 new_owner_id)

   权限矩阵(参 Doc/05_permissions.md):
     * GET 列表 / 详情     → 全员登录可见(@jwt_required)
     * POST / PUT          → @require_role('pm', 'super_admin')
     * PATCH cancel        → @require_role('pm', 'super_admin')
     * PUT owner           → @require_role('pm', 'super_admin', 'management')

Step 2 — Service 层:[同正文]
Step 3 — Blueprint:[同正文]
Step 4 — 注册到 backend/app/blueprints/__init__.py 的 register_blueprints():[同正文]
Step 5 — 自检稿件:[同正文]

## 【⛔ 动作纪律 — 打断点】[同正文]

Step 6 — 烟测:
  必跑用例:
    a) POST /api/projects(创建一个 SUS_VC 项目,断言返回的 project_code 已生成)
    b) PUT /api/projects/1(带正确 version,断言成功)
    c) PUT /api/projects/1(带过期 version,断言 409)
    d) PATCH /api/projects/1/cancel(断言 status=cancelled,无 DELETE)

## 【验收防线】[同正文 7 条 grep]

## 【完工汇报】[同正文格式]
```

---

## T03 - 新建 Vue 列表页(含搜索栏 + 分页)

### 适用场景

为某个业务模块(Phase 1 项目、Phase 2 治具、Phase 6 字典维护等)新建列表页。**仅**覆盖列表展示 + 搜索 + 分页 + 操作按钮(跳详情 / 编辑 / 作废),**不**写表单页(走 T04)、**不**改后端(走 T02)。

### 需准备的参数清单

| 变量 | 含义 | 示例 |
|------|------|------|
| `[Entity_Name]` | 实体类名 | `Project` |
| `[entity_filename]` | 文件名(snake_case) | `project` |
| `[view_filename]` | 视图文件名(PascalCase) | `ProjectList` |
| `[resource_path]` | API 资源路径(kebab-case 复数) | `projects` |
| `[列定义]` | 表格列(字段 / 标题 / 是否时间字段 / 是否状态字段) | 见使用示例 |
| `[搜索条件]` | 搜索栏字段(下拉 / 输入框 / 日期范围) | 见使用示例 |
| `[操作按钮]` | 操作列按钮(权限 + 文案 + 行为) | 见使用示例 |

### 提示词正文

```text
# 任务:新建 Vue 列表页 — [view_filename]

## 上下文
- 前置条件:T02 已完成,GET /api/[resource_path] 列表接口已通
- 本任务范围:列表页组件 + API client 函数 + 路由挂载
- 不在本任务范围:表单页(T04)/ 后端(T02)
- 技术栈:Vue 3 (Composition API + script setup) + Element Plus 2.x + Axios 1.x;**不引入**任何额外 UI 库

## 【文档约束】开工前必须复述以下条款,缺一不可

1. **CLAUDE.md §d Rule 7 + 09_dev_rules.md 前端 #7 + Rule 14**:
   - 导入用**相对路径**(`../../api/[entity_filename].js`),**严禁** `@/` 路径别名(vite 未配 alias,运行时 404)
   - eslint 已经在 `no-restricted-imports` 拦截 `@/*`,违反会编译失败

2. **CLAUDE.md §e.10 + 09_dev_rules.md 前端 #1**:时间处理
   - 后端 datetime 字符串**只能**走 `utils/datetime.js` 的 `parseBackendTime(str)` / `formatBackendTime(str, fmt)`
   - **严禁** `dayjs(str)` 裸调、**严禁** `new Date(str)`(浏览器按本地时区解析,异地访问偏差)
   - eslint 已在 `no-restricted-syntax` 拦截裸 dayjs / new Date

3. **CLAUDE.md §d Rule 8 + 09_dev_rules.md 前端 #5**:状态标签
   - 12 种治具状态(或本模块自有状态)颜色映射定义在 `utils/status.js`,组件 import 引用
   - `el-tag` 的 `:type` 兜底必须合法:`{ pending: 'warning', passed: 'success', failed: 'danger' }[x] || 'info'`,**不许** `|| ''`
   - 本模块若引入新状态,先在 `utils/status.js` 增补单一来源
   - **前置检查**:`frontend/src/utils/status.js` 若**尚不存在**(Phase 0 未建),本任务**第一步先创建该文件**——按当前模块需要导出 `XXX_STATUS_MAP`(状态码 → 中文标签 + el-tag type)和解析函数 `statusTag(code)` / `statusLabel(code)`;治具列表场景需含 12 种状态,项目/批次等少状态模块可仅含本模块状态,后续模块按需追加到同一文件

4. **CLAUDE.md §d Rule 11**:Element Plus 反馈组件必须显式 import:
   ```javascript
   import { ElMessage, ElMessageBox, ElNotification } from 'element-plus'
   ```

5. **CLAUDE.md §d Rule 12**:JWT token 过滤已在 axios 拦截器统一处理,本组件**不要**自己读 localStorage

6. **09_dev_rules.md 前端 #3**:409 由 `api/request.js` 拦截器统一处理(弹窗 + reload),组件 catch **不要**捕获 409

7. **09_dev_rules.md 前端 #6**:按钮可见性走 `useAuthStore().hasPermission('action_code')`,**严禁**组件内硬编码 `if (role === 'pm')`

8. **CLAUDE.md 技术栈表 + 09_dev_rules.md 命名约定**:
   - Vue 组件 PascalCase:`[view_filename].vue`
   - API client 文件:`src/api/[entity_filename].js`,导出具名函数(`listProjects(params)` / `cancelProject(id, payload)` 等)
   - Pinia **仅用于全局**(auth / 字典缓存),列表页本地状态用 `ref / reactive`,不要无脑塞 Pinia

9. **CLAUDE.md §d Rule 9**(操作按钮二次确认):任何作废 / 删除按钮必须 `ElMessageBox.confirm` 二段 try/catch(用户取消静默退出)— 详见 T04 提示词,本列表页若提供"作废"按钮也适用

10. **CLAUDE.md §e.11 + 09_dev_rules.md 前端 #8**:导出按钮(若本列表页含)
    - 列表 < 1000 条:前端 `xlsx` (SheetJS)直接生成
    - >= 1000 条 / 多表关联:调后端 `GET /api/[resource_path]/export`
    - **严禁**任何"前端轮询导出状态 / 邮件下载链接"工作流

## 【开发动作】

**Step 1 — API client**:
   创建 `frontend/src/api/[entity_filename].js`(或在已存在文件追加):
   ```javascript
   import request from './request'  // ✅ 相对路径,request.js 与本文件同在 api/ 目录下

   export function list[Entity_Name]s(params) {
     return request.get('/api/[resource_path]', { params })
   }
   // ...其他按 [操作按钮] 需要的函数...
   ```

**Step 2 — 列定义对齐**:
   把 [列定义] 列在对话里,逐字段标注:
   - 是否时间字段(必须 `formatBackendTime`)
   - 是否状态字段(必须从 `utils/status.js` 取标签 + 颜色)
   - 是否需要权限挡(部分敏感字段仅特定角色可见,参 Doc/05_permissions.md)

**Step 3 — 列表页组件**:
   创建 `frontend/src/views/[entity_filename]/[view_filename].vue`,结构:
   ```vue
   <script setup>
   import { ref, reactive, onMounted } from 'vue'
   import { ElMessage, ElMessageBox } from 'element-plus'  // 显式 import
   import { list[Entity_Name]s } from '../../api/[entity_filename]'  // 相对路径
   import { formatBackendTime } from '../../utils/datetime'
   import { statusTag, statusLabel } from '../../utils/status'
   import { useAuthStore } from '../../stores/auth'
   import { useRouter } from 'vue-router'

   const auth = useAuthStore()
   const router = useRouter()
   const loading = ref(false)
   const list = ref([])
   const pagination = reactive({ page: 1, pageSize: 20, total: 0 })
   const filters = reactive({ /* [搜索条件] 对应字段 */ })

   async function load() { /* 调 list[Entity_Name]s + 处理结果 */ }
   async function onSearch() { pagination.page = 1; await load() }
   async function onReset() { /* 清空 filters,刷新 */ }
   async function onCancelItem(row) {
     try {
       await ElMessageBox.confirm('确认作废?', '提示', { type: 'warning' })
     } catch { return }  // 二段 try/catch
     try { /* 调 cancel API */ } catch (err) { ElMessage.error(err?.response?.data?.message || '操作失败') }
   }

   onMounted(load)
   </script>

   <template>
     <!-- 搜索栏:el-form inline,字段对应 [搜索条件] -->
     <!-- 表格:el-table,列对应 [列定义];时间列用 formatBackendTime,状态列用 el-tag :type="statusTag(row.status)" -->
     <!-- 操作列:按 [操作按钮] 渲染,按钮加 v-if="auth.hasPermission('xxx')" -->
     <!-- 分页:el-pagination v-model:current-page="pagination.page" ... -->
   </template>
   ```

**Step 4 — 路由挂载**:
   在 `frontend/src/router/index.js` 加路由:
   ```javascript
   {
     path: '/[resource_path]',
     name: '[Entity_Name]List',
     component: () => import('../views/[entity_filename]/[view_filename].vue'),
     meta: { requiresAuth: true }
   }
   ```

**Step 5 — 自检稿件**:
   贴出整个 .vue 文件 + API client diff + router diff,自我核对:
   - 所有 import 是相对路径?
   - 时间字段是否走 formatBackendTime?
   - 状态字段是否走 utils/status.js?
   - 按钮是否有 hasPermission?
   - ElMessage / ElMessageBox 是否显式 import?

## 【⛔ 动作纪律 — 在此处打断点】

**禁止**直接 `pnpm dev` 启动前在对话里跳过 Step 5 自检稿件。
**禁止**自行在 `utils/status.js` 增加新状态而不告诉我(单一来源,本模块若需新状态,先与我对齐)。
等我回 `go` 再继续 Step 6。

## 【开发动作 续】

**Step 6 — 本地启动验证**:
   - `pnpm dev` 启动,访问 `/[resource_path]`,贴出截图或 console 输出
   - 验证:列表加载 / 搜索 / 分页 / 时间显示带 +08:00 / 状态标签颜色正确 / 无权限按钮隐藏

## 【验收防线】完工后必须执行以下 grep 并贴出输出

```bash
# 1. 严禁 @/ 路径别名
grep -RIn "from ['\"]@/" frontend/src/views/[entity_filename]/ frontend/src/api/[entity_filename].js
# 期望:无匹配

# 2. 严禁裸 dayjs(str) / new Date(str)
grep -RInE "(^|[^a-zA-Z])dayjs\([a-zA-Z_]" frontend/src/views/[entity_filename]/
grep -RIn "new Date(" frontend/src/views/[entity_filename]/
# 期望:无匹配(仅 utils/datetime.js 内部可有)

# 3. 严禁组件内硬编码角色判断
grep -RIn "role === " frontend/src/views/[entity_filename]/
# 期望:无匹配,统一走 hasPermission()

# 4. 严禁 el-tag :type 兜底为空字符串
grep -RInE "\|\| ''[^a-zA-Z]" frontend/src/views/[entity_filename]/
# 期望:无匹配

# 5. ElMessage / ElMessageBox 必须 import(不能裸用)
grep -RIn "ElMessage\|ElMessageBox" frontend/src/views/[entity_filename]/
# 配套检查:每个用到的文件顶部必须有 `import { ElMessage, ElMessageBox } from 'element-plus'`
```

## 【完工汇报】格式

- 新增视图:[路径]
- 新增 API client 函数:[列出]
- router 改动:[贴 diff]
- 烟测截图 / 关键 console 输出:[贴]
- 验收防线 5 条 grep 输出:[贴]
```

### 使用示例(填充 Phase 1 — 项目列表页)

```text
# 任务:新建 Vue 列表页 — ProjectList

## 上下文
- 前置条件:T02 已完成,GET /api/projects + PATCH /api/projects/:id/cancel 已通
- 本任务范围:ProjectList.vue + api/project.js 函数补全 + router 挂载
- 不在本任务范围:新建项目表单 / 项目详情(走 T04)
- 技术栈:Vue 3 + Element Plus + Axios;不引入额外库

## 【文档约束】[同正文 10 条]

## 【开发动作】

Step 1 — API client(api/project.js):
  listProjects(params) / cancelProject(id, { reason, version })

Step 2 — 列定义对齐:
  | 字段 | 标题 | 类型 |
  |------|------|------|
  | project_code   | 项目编号 | 文本 |
  | project_name   | 项目名称 | 文本(可点击进详情) |
  | product_type   | 产品线 | 文本(SUS VC / Cu VC / HP) |
  | owner_name     | 负责人 | 文本(后端返回) |
  | status         | 状态   | el-tag,走 utils/status.js(active / cancelled) |
  | planned_start_date | 计划开始 | 时间,走 formatBackendTime(str, 'YYYY-MM-DD') |
  | created_at     | 创建时间 | 时间,走 formatBackendTime |

  搜索条件 [搜索条件]:
    - product_type:el-select(SUS_VC / CU_VC / HP / 全部)
    - status:el-select(active / cancelled / 全部,默认 active)
    - owner_id:el-select(下拉,从字典缓存取人员)
    - keyword:el-input(模糊匹配 project_code / project_name)

  操作按钮 [操作按钮]:
    - 查看详情(全员可见,跳 /projects/:id)
    - 编辑(hasPermission('project.edit'),跳 /projects/:id/edit)
    - 作废(hasPermission('project.cancel'),弹 confirm 输 reason,调 cancelProject)

Step 3 — ProjectList.vue 组件:[按正文模板填充]
Step 4 — 路由挂载:/projects → ProjectList
Step 5 — 自检稿件:[同正文]

## 【⛔ 动作纪律 — 打断点】[同正文]

Step 6 — 本地启动验证:
  必看:
    a) 列表加载 + 分页切换
    b) 时间列显示 "2026-05-11 09:30:00"(+08:00,与后端 ISO 字符串一致)
    c) status=cancelled 的行 tag 显示 'info' 灰色
    d) 无 project.cancel 权限的用户看不到作废按钮

## 【验收防线】[同正文 5 条 grep]
## 【完工汇报】[同正文格式]
```

---

## T04 - 新建 Vue 表单页(新增/编辑/详情)

### 适用场景

为某个业务模块新建表单页(创建 / 编辑 / 只读详情三合一,或拆分)。**仅**覆盖表单组件 + 提交逻辑 + 路由,**不**改后端 / 不动列表页(走 T02 / T03)。

### 需准备的参数清单

| 变量 | 含义 | 示例 |
|------|------|------|
| `[Entity_Name]` | 实体类名 | `Project` |
| `[entity_filename]` | 文件名 | `project` |
| `[view_filename]` | 视图文件名 | `ProjectForm` |
| `[resource_path]` | API 资源路径 | `projects` |
| `[字段表]` | 表单字段(名 / 类型 / 必填 / 校验 / 是否仅编辑可见) | 见使用示例 |
| `[模式]` | `create` / `edit` / `detail` 三合一,或拆分 | `三合一` |

### 提示词正文

```text
# 任务:新建 Vue 表单页 — [view_filename]

## 上下文
- 前置条件:T01 + T02 已完成(Model / GET / POST / PUT 均已通)
- 本任务范围:表单组件 + 提交逻辑 + 路由
- 不在本任务范围:列表页(T03)/ 后端(T02)
- 模式:[模式]

## 【文档约束】开工前必须复述以下条款,缺一不可

1. **CLAUDE.md §e.5 + Doc/04_api_spec.md 通用约束**:乐观锁
   - 编辑模式提交时 **body 必带 version 字段**,从 GET 详情接口的返回值继承
   - 409 由全局拦截器处理(09_dev_rules.md 前端 #3),组件 catch **不要**单独处理 409

2. **CLAUDE.md §d Rule 5**:PUT/PATCH 字段更新语义
   - 后端用 `'key' in body` 判断,所以前端"未改的字段"**应当不放进** payload(只 PATCH 已修改字段)
   - 若用 PUT 全量更新,前端必须送全字段(包括 0 / 空字符串等"假值",**不要**用 `data || undefined` 之类筛掉)

3. **CLAUDE.md §d Rule 9 + 09_dev_rules.md 前端 #3**:ElMessageBox.confirm 二段 try/catch
   ```javascript
   try {
     await ElMessageBox.confirm('确认提交?', '提示', { type: 'warning' })
   } catch { return }  // 用户取消,静默退出,不抛错
   try {
     await api.update(...)
     ElMessage.success('已保存')
     router.push(`/[resource_path]`)
   } catch (err) {
     ElMessage.error(err?.response?.data?.message || '保存失败')
   }
   ```

4. **CLAUDE.md §d Rule 10**:`v-for` 可编辑表格禁用 index 作 key
   - 若表单含动态行(如 PO 明细 / 治具批次清单),用 `nanoid` 生成 `_temp_id` 作 :key
   ```javascript
   import { nanoid } from 'nanoid'
   items.value = data.map(it => ({ ...it, _temp_id: nanoid() }))
   ```

5. **CLAUDE.md §e.7**:**严禁**在前端拼接编码(`project_code` / `fixture_code`),编码由后端 `services/code_generator.py` 生成,前端只展示

6. **CLAUDE.md §e.10 + 09_dev_rules.md 前端 #1**:时间字段
   - 表单回显:用 `parseBackendTime(str)` 后再喂给 `el-date-picker`(避免本地时区解析偏差)
   - 提交时:`el-date-picker` 的 v-model 已是 Date 对象 / 字符串,**确认与后端约定**(详见 Doc/04_api_spec.md,通常 ISO 字符串 + 时区);若需格式化用 `formatBackendTime(val, 'YYYY-MM-DD')`
   - **严禁** `dayjs(str)` 裸调、`new Date(str)`

7. **CLAUDE.md §d Rule 7**:导入相对路径,**严禁** `@/`

8. **CLAUDE.md §d Rule 11**:`ElMessage` / `ElMessageBox` 必须显式 import

9. **09_dev_rules.md 前端 #6**:字段是否可编辑走 `hasPermission()`,**禁止**硬编码角色判断

10. **状态变更**:表单页**不直接**调状态机相关接口(那是治具操作类按钮的范畴,走列表页或详情页操作区,且后端走 `PATCH /api/fixtures/:id/status` — 详 T05);本任务专注 Model 字段的 CRUD

## 【开发动作】

**Step 1 — 字段表对齐**:
   把 [字段表] 列在对话里,逐字段标注:
   - 表单控件类型(input / textarea / select / date-picker / number / cascader / 自定义)
   - 是否必填、校验规则(maxLength / pattern / range)
   - 创建 vs 编辑可见性(如 `project_code` 创建时不显示,由后端生成;编辑时只读展示)
   - 是否需要 hasPermission 才可编辑
   - 是否时间字段(必须 parseBackendTime / formatBackendTime)

**Step 2 — API client 补全**:
   `frontend/src/api/[entity_filename].js` 增加:
   - `get[Entity_Name]ById(id)`
   - `create[Entity_Name](payload)`
   - `update[Entity_Name](id, payload)` — payload 必含 version

**Step 3 — 表单组件**:
   创建 `frontend/src/views/[entity_filename]/[view_filename].vue`,结构(三合一模式):
   ```vue
   <script setup>
   import { ref, reactive, onMounted, computed } from 'vue'
   import { useRoute, useRouter } from 'vue-router'
   import { ElMessage, ElMessageBox } from 'element-plus'
   import { get[Entity_Name]ById, create[Entity_Name], update[Entity_Name] } from '../../api/[entity_filename]'
   import { parseBackendTime, formatBackendTime } from '../../utils/datetime'
   import { useAuthStore } from '../../stores/auth'

   const route = useRoute(), router = useRouter(), auth = useAuthStore()
   const mode = computed(() => route.meta.mode || 'create')  // create / edit / detail
   const readOnly = computed(() => mode.value === 'detail')
   const form = reactive({ /* 按 [字段表] 初始化 */ version: null })
   const rules = { /* el-form-item 校验规则 */ }
   const formRef = ref(null)

   onMounted(async () => {
     if (mode.value !== 'create') {
       const res = await get[Entity_Name]ById(route.params.id)
       Object.assign(form, res.data.data)
       // 时间字段需 parseBackendTime 后赋给 el-date-picker
     }
   })

   async function onSubmit() {
     await formRef.value.validate()
     try { await ElMessageBox.confirm(mode.value === 'create' ? '确认新建?' : '确认保存?', '提示', { type: 'warning' }) } catch { return }
     try {
       if (mode.value === 'create') {
         await create[Entity_Name]({ ...form })
       } else {
         await update[Entity_Name](route.params.id, { ...form })  // 必含 version
       }
       ElMessage.success('已保存')
       router.push('/[resource_path]')
     } catch (err) {
       ElMessage.error(err?.response?.data?.message || '保存失败')
     }
   }
   </script>

   <template>
     <el-form ref="formRef" :model="form" :rules="rules" :disabled="readOnly">
       <!-- 按 [字段表] 逐字段渲染 -->
       <!-- 编辑模式额外展示 project_code(只读) -->
       <!-- 时间字段:<el-date-picker v-model="form.planned_start_date" type="date" value-format="YYYY-MM-DD" /> -->
       <!-- 字段权限:某字段仅特定角色可编辑,加 :disabled="!auth.hasPermission('xxx')" -->
     </el-form>
     <div v-if="!readOnly">
       <el-button type="primary" @click="onSubmit">保存</el-button>
       <el-button @click="router.back()">取消</el-button>
     </div>
   </template>
   ```

**Step 4 — 路由挂载**:
   `router/index.js`:
   ```javascript
   { path: '/[resource_path]/new',       name: '[Entity_Name]Create', component: () => import('...'), meta: { mode: 'create', requiresAuth: true } },
   { path: '/[resource_path]/:id',       name: '[Entity_Name]Detail', component: () => import('...'), meta: { mode: 'detail', requiresAuth: true } },
   { path: '/[resource_path]/:id/edit',  name: '[Entity_Name]Edit',   component: () => import('...'), meta: { mode: 'edit',   requiresAuth: true } },
   ```

**Step 5 — 自检稿件**:
   贴出 .vue 文件 + API client diff + router diff,自检:
   - 编辑提交时 body 是否含 version?
   - 是否前端拼接了 [Entity_Name]_code?(严禁)
   - 时间字段回显是否走 parseBackendTime?
   - 动态行(若有)是否用 _temp_id 作 key?
   - ElMessageBox.confirm 是否二段 try/catch?

## 【⛔ 动作纪律 — 在此处打断点】

**禁止**未经我回复 `go` 就 `pnpm dev` 验证。
**禁止**自行扩大字段(如顺手加"项目预算"字段),如发现字段表缺漏,先在对话里告诉我,等我确认是否走 T01 加字段后再继续。

## 【开发动作 续】

**Step 6 — 烟测**:
   必跑 5 个场景:
   a) `/[resource_path]/new` — 创建成功后跳列表
   b) `/[resource_path]/:id` — 详情只读,无保存按钮
   c) `/[resource_path]/:id/edit` — 字段回填正确(时间字段带 +08:00)
   d) 编辑模式提交时 payload 含 version(浏览器 Network 面板验证)
   e) 故意发个过期 version → 全局拦截器弹窗 + reload(09_dev_rules.md 前端 #3)

## 【验收防线】完工后必须执行以下 grep 并贴出输出

```bash
# 1. 严禁 @/ 路径别名
grep -RIn "from ['\"]@/" frontend/src/views/[entity_filename]/ frontend/src/api/[entity_filename].js
# 期望:无匹配

# 2. 严禁前端拼接编码
grep -RIn "[Entity_Name]_code\s*=" frontend/src/views/[entity_filename]/
# 期望:无匹配(前端只展示,不参与拼接)

# 3. 编辑提交必含 version
grep -RIn "update[Entity_Name]\s*(" frontend/src/views/[entity_filename]/
# 配套人工检查:payload 中必含 version 字段

# 4. 严禁裸 dayjs / new Date
grep -RInE "(^|[^a-zA-Z])dayjs\([a-zA-Z_]" frontend/src/views/[entity_filename]/
grep -RIn "new Date(" frontend/src/views/[entity_filename]/
# 期望:无匹配

# 5. v-for 可编辑表格禁用 index 作 key
grep -RInE ":key=['\"]index['\"]" frontend/src/views/[entity_filename]/
# 期望:无匹配(应该用 _temp_id)

# 6. ElMessageBox.confirm 必须二段 try/catch(无对应 catch 的会让用户取消变成异常冒泡)
# 人工核对:每个 confirm 后必有 try { } catch { return }
```

## 【完工汇报】格式

- 新增视图:[路径]
- API client 新增/修改函数:[列出]
- router 改动:[贴 diff]
- 烟测 5 场景结果:[逐场景贴]
- 验收防线 6 条 grep + 人工核对结果:[贴]
```

### 使用示例(填充 Phase 1 — 项目表单三合一)

```text
# 任务:新建 Vue 表单页 — ProjectForm

## 上下文
- 前置条件:T02 已通(GET /api/projects/:id / POST /api/projects / PUT /api/projects/:id 已实现)
- 本任务范围:ProjectForm.vue + api/project.js 增 get/create/update + router 三条路由
- 不在本任务范围:列表页(T03,已完成)
- 模式:三合一(create / edit / detail 共用同一组件,通过 route.meta.mode 区分)

## 【文档约束】[同正文 10 条]

## 【开发动作】

Step 1 — 字段表:
  | 字段 | 控件 | 必填 | create 可见 | edit 可见 | detail 可见 | 备注 |
  |------|------|------|------------|----------|------------|------|
  | project_code     | text(只读) | -    | ❌(后端生成) | ✅(只读)  | ✅(只读) | **严禁前端拼接** |
  | project_name     | el-input             | ✅   | ✅           | ✅       | ✅       | maxLength=128 |
  | product_type     | el-select(SUS_VC / CU_VC / HP) | ✅ | ✅ | ✅(创建后通常不改,但允许) | ✅ | — |
  | owner_id         | el-select(人员下拉) | ✅   | ✅           | ❌(走 PUT /api/projects/:id/owner 转移) | ✅(显示姓名) | 转移走单独接口 |
  | planned_start_date | el-date-picker     | ❌   | ✅           | ✅       | ✅       | value-format='YYYY-MM-DD' |
  | planned_end_date   | el-date-picker     | ❌   | ✅           | ✅       | ✅       | value-format='YYYY-MM-DD',校验需 >= start |
  | version          | hidden               | -    | -            | ✅(payload 必带) | -        | edit 模式提交必含 |

Step 2 — API client(api/project.js)新增:
  getProjectById(id) / createProject(payload) / updateProject(id, payload)

Step 3 — ProjectForm.vue:[按正文模板填充,readOnly = mode === 'detail']
Step 4 — 路由:
  /projects/new       → mode='create'
  /projects/:id       → mode='detail'
  /projects/:id/edit  → mode='edit'

Step 5 — 自检稿件:[同正文]

## 【⛔ 动作纪律 — 打断点】[同正文]

Step 6 — 烟测 5 场景:[同正文,把 [resource_path] 替换成 projects]

## 【验收防线】[同正文 6 条 grep]
## 【完工汇报】[同正文格式]
```

---

## T05 - 状态机相关开发(transition / reject / force_transition)

### 适用场景

涉及治具状态流转的任意变更:新增触发器、调整 TRANSITIONS / REJECT_CONFIG、新增/修改 `PATCH /api/fixtures/:id/status` 的 trigger 分支、超管强制跳转、状态历史表落地等。**这是项目最危险的模块,改一行影响 5 处文档与代码**。

### 需准备的参数清单

| 变量 | 含义 | 示例 |
|------|------|------|
| `[变更类型]` | `新增触发器` / `修改触发器` / `新增驳回路径` / `修改驳回路径` / `新增超管动作` | `新增触发器` |
| `[from_status]` | 起始状态 | `INSTALLING` |
| `[to_status]` | 目标状态 | `ACCEPTANCE_TESTING` |
| `[trigger]` | 触发器名 | `normal` / `iqc_pass` / 等 |
| `[业务场景]` | 一句话描述本次变更的业务原因 | "ME 安装完成后由 IQC 触发验收" |
| `[决策类型]` | (审批驳回场景)`approved` / `rejected` / `concession_approved` | `rejected` |

### 提示词正文

```text
# 任务:状态机变更 — [变更类型]

## 上下文
- 当前阶段:Phase 2 / Phase 3(状态机核心实现 / 流程节点接入)
- 本任务范围:state_machine.py + status_history 表落地 + Service 调用点 + 前端 status.js + i18n + 文档同步(5 处必须同步)
- 不在本任务范围:Model 字段变更(走 T01)、前端列表/表单页大改(走 T03 / T04)

## 【文档约束】开工前必须复述以下条款,缺一不可

1. **CLAUDE.md §e.4 + 09_dev_rules.md 后端 #3**:状态机三函数职责清晰
   - `transition(fixture, to_status, trigger, operator_id, reason, related)` — 正常流转,**严格走 TRANSITIONS**,**禁止**加 force / bypass 参数
   - `reject(fixture, operator_id, reason)` — 审批驳回,走 `REJECT_CONFIG` 配置的合法路径
   - `force_transition(fixture, to_status, operator_id, reason)` — 超管强制跳转,**唯一**绕过 TRANSITIONS 的入口,**必填 reason** + **自动写审计日志**(`audit_service.log_force_action(...)`)

2. **CLAUDE.md §h 风险点**:
   - 写代码前 `grep -RIn "force=True\|force_transition.*force=" backend/app/services/state_machine.py` 必须只在 `force_transition` 函数体内出现
   - **严禁**让 `transition()` 函数签名再次出现 force 参数(V1.4 已消除 V1.2 的后门设计)

3. **CLAUDE.md §g 关键流程改动同步 5 处**:本任务必须**同时**改:
   - (1)`backend/app/services/state_machine.py` 的 `TRANSITIONS` 和/或 `REJECT_CONFIG`
   - (2)`backend/app/models/fixture_status_history.py` 字段(若新增 trigger 类型需要新字段才能容纳,需走 T01 加字段)
   - (3)`frontend/src/utils/status.js` 颜色映射 + 标签
   - (4)前端 i18n 中英文标签(如有)
   - (5)`Doc/03_architecture_v1.4.md` 第 3.3 节 TRANSITIONS 表 + `Doc/04_api_spec.md` 第 2 节 trigger 取值表

4. **Doc/04_api_spec.md §2 + §5**:状态变更**唯一**入口
   - 所有状态变更走 `PATCH /api/fixtures/:id/status`,body 含 `trigger` + `version` + 其他业务参数
   - **不许**新增 `POST /api/fixtures/:id/install` 之类的"动词"路由
   - 超管强制走 `POST /api/fixtures/:id/force-status`(Doc/04_api_spec.md 已列出,**唯一**调用 `force_transition()` 的端点)

5. **Doc/04_api_spec.md trigger 取值表**:当前合法 trigger **以 Doc/04_api_spec.md 第 2 节"`PATCH /api/fixtures/:id/status` 的 trigger 取值参考"为唯一权威来源**,本模板不维护副本。
   - **新增** trigger:**必须先**在 04_api_spec.md 第 2 节增条目,再回来改 state_machine.py(详 Step 6 文档同步)
   - **删除/重命名** trigger:风险极高,涉及历史 `status_history.trigger_type` 列已写入的旧值,**必须**走架构评审,本模板拒绝处理

6. **CLAUDE.md §e.5 + 09_dev_rules.md 后端 #7**:`PATCH /api/fixtures/:id/status` 同样必传 `version`,Service 内手动比对 + 自增

7. **CLAUDE.md §e.6 + 09_dev_rules.md 后端 #5**:`reject()` 若由审批触发,审批 Service 透传 `decision_type`(approved / rejected / concession_approved),写入 status_history.reason 或独立字段

8. **CLAUDE.md §e.9 + 09_dev_rules.md 后端 #8**:状态变更若触发邮件告警(如进入 EMERGENCY_PENDING),走 `services/alert_service.py:send_alert_dedup()`,失败 try/except 不抛出

## 【开发动作】

**Step 1 — 变更影响面分析**(写在对话里,不准跳):
   - 本次 [变更类型] 的 from → to 流转:[from_status] → [to_status],trigger=[trigger]
   - 业务场景:[业务场景]
   - 影响的现有代码位置(grep `[from_status]` / `[trigger]` 列出每个文件 + 行号)
   - 是否需要新增 trigger 字符串?(如是,先告诉我并暂停)
   - 是否需要新增 status 字符串?(如是,这不是状态机变更而是流程重大调整,**停下来等架构评审**)

**Step 2 — 改 state_machine.py**:
   修改 `backend/app/services/state_machine.py`:
   - 若 [变更类型] = 新增触发器:在 `TRANSITIONS[<from>]` dict 中加 `<to>: '<trigger>'`
   - 若 [变更类型] = 新增驳回路径:在 `REJECT_CONFIG[<from>]` 加 `(<trigger>, <to>)`
   - 若 [变更类型] = 新增超管动作:超管跳转通常**不**需要改 TRANSITIONS(force_transition 本就绕过);只需在 audit_service 验证写日志路径正常即可
   - **严禁**在 `transition()` 函数体新增 `force=...` 或 `bypass=...` 参数(无论以何借口)

**Step 3 — 改 status_history 写入点**:
   `transition()` / `reject()` / `force_transition()` 三个函数内已统一写 `FixtureStatusHistory`。若本次新增字段(如 `decision_type`),需走 T01 加字段后再回来接入。

**Step 4 — 改 Blueprint 路由 trigger 分发**:
   `backend/app/blueprints/fixture.py` 的 `PATCH /api/fixtures/:id/status` 已用 trigger 字段分发,本任务**可能**需要:
   - 加新的 trigger case(if trigger == 'xxx': call transition(...))
   - **不许**在该路由直接调 `force_transition()`(那是 `POST /api/fixtures/:id/force-status` 的活)

**Step 5 — 前端同步 5 处中的(3)(4)**:
   - `frontend/src/utils/status.js`:若新增状态用到的标签 / 颜色映射,在此单一来源里加
   - i18n:中英文标签同步(若项目当前未启用 i18n,在 utils/status.js 内放中文字典即可,代码内不要硬编码字符串)

**Step 6 — 文档同步 5 处中的(5)**:
   - `Doc/03_architecture_v1.4.md` 第 3.3 节 TRANSITIONS / REJECT_CONFIG 表更新
   - `Doc/04_api_spec.md` 第 2 节 `PATCH /api/fixtures/:id/status` 的 trigger 取值表更新(若新增)
   - 改动记录写入 `Doc/03_architecture_v1.4.md` 修订记录(或对应章节)与 `CLAUDE.md` §j 修订记录

## 【⛔ 动作纪律 — 在此处打断点(连续两次)】

**断点 1**:Step 2 改完 state_machine.py 后,**禁止**继续动 Blueprint,先把 diff 贴给我,我核对 TRANSITIONS / REJECT_CONFIG 的正确性。回 `go-1` 再继续。

**断点 2**:Step 5 + Step 6 全部完成后,**禁止**直接 `pnpm dev` / `pytest` 验证,先把 5 处同步的所有 diff 完整贴出(state_machine / Blueprint / status.js / i18n / 文档),让我整体核对"5 处一致"。回 `go-2` 再继续 Step 7。

## 【开发动作 续】

**Step 7 — 单元测试同步**(若本次新增触发器,T07 中必加用例,但本任务**先简单冒烟**):
   - 跑现有 `tests/test_state_machine.py`(若已有 — Phase 2 后期会建立),验证不破坏既有流转
   - 至少新写 2 个用例:
     a) 合法触发器:`transition(fixture, [to_status], '[trigger]', ...)` 应成功
     b) 非法组合:`transition(fixture, [to_status], 'wrong_trigger', ...)` 应抛 `StateMachineError`

**Step 8 — 烟测**:
   - 起 dev server,用 curl 跑 `PATCH /api/fixtures/:id/status`,body `{ "trigger": "[trigger]", "version": N, ... }`
   - 检查 `fixture_status_history` 表新插一行,trigger_type=[trigger]
   - 检查 fixture.current_status = [to_status]
   - 检查 fixture.version 自增

## 【验收防线】完工后必须执行以下 grep 并贴出输出

```bash
# 1. 严禁 transition() 函数签名出现 force 参数
grep -A 3 "^def transition" backend/app/services/state_machine.py
# 期望:函数签名仅 (fixture, to_status, trigger, operator_id, reason=None, related=None)

# 2. force=True 只能在 force_transition 函数体内出现
grep -RIn "force\s*=\s*True" backend/app/services/state_machine.py
# 期望:无匹配,或仅作为旧代码注释存在(V1.4 已废)

# 3. 严禁 Service / Blueprint 直接改 current_status(绕过状态机)
grep -RIn "current_status\s*=\s*['\"]" backend/app/services/ backend/app/blueprints/
# 期望:仅 state_machine.py 内出现

# 4. 严禁 force_transition 在普通端点出现
grep -RIn "force_transition" backend/app/blueprints/
# 期望:仅 POST /api/fixtures/:id/force-status 端点调用

# 5. 严禁前端 status.js 之外硬编码状态颜色
grep -RIn "status.*color\|currentStatus.*color" frontend/src/views/
# 期望:无匹配(颜色统一从 utils/status.js 取)

# 6. 5 处同步证据(列出本次改动文件的清单,核对不少于 4 个 — state_machine.py / status.js / 文档 至少各 1)
git diff --name-only HEAD
# 期望:覆盖 backend/app/services/state_machine.py、frontend/src/utils/status.js、Doc/03_architecture_v1.4.md、Doc/04_api_spec.md(以及视情况 Blueprint / i18n)
```

## 【完工汇报】格式

- 变更类型:[变更类型]
- 流转规则:[from_status] --[trigger]--> [to_status]
- 影响文件清单(5 处同步):
  - backend/app/services/state_machine.py:[diff 行号]
  - backend/app/blueprints/fixture.py:[diff 行号]
  - frontend/src/utils/status.js:[diff 行号]
  - i18n / 标签字典:[diff 行号]
  - Doc/03_architecture_v1.4.md:[diff 行号]
  - Doc/04_api_spec.md:[diff 行号]
- 新增测试用例:[列出 + pytest 输出]
- 烟测结果:[curl + response 贴出]
- 验收防线 6 条输出:[贴]
```

### 使用示例(填充 Phase 2 — 治具试产验收合格)

```text
# 任务:状态机变更 — 新增触发器

## 上下文
- 当前阶段:Phase 2(模治具核心模块,状态机三函数实现 + 测试)
- 本任务范围:确认 ACCEPTANCE_TESTING --acceptance_pass--> IN_STOCK 流转已在 TRANSITIONS 中,并接入 PATCH /api/fixtures/:id/status 的 trigger 分发,前后端文档 5 处同步
- 不在本任务范围:试产验收报告单 POST /api/acceptance-reports 表单(走 T01 + T02 + T04)

## 【文档约束】[同正文 8 条]

## 【开发动作】

Step 1 — 变更影响面分析:
  本次:ACCEPTANCE_TESTING --acceptance_pass--> IN_STOCK
  业务场景:试产验收合格,治具入库待领用
  现有代码位置:架构文档 V1.4 第 3.3 节 TRANSITIONS 已列出此条,本任务核对 state_machine.py 与文档一致即可
  新增 trigger?:否(acceptance_pass 已在 04_api_spec.md trigger 取值表)
  新增 status?:否

Step 2 — state_machine.py:核对 TRANSITIONS[S.ACCEPTANCE_TESTING][S.IN_STOCK] == 'acceptance_pass',若已存在则跳过
Step 3 — status_history:无需新增字段
Step 4 — Blueprint:在 PATCH /api/fixtures/:id/status 的 trigger 分发里,acceptance_pass 分支调 transition(...)
Step 5 — 前端 status.js:确认 IN_STOCK 状态颜色 + 标签已有
Step 6 — 文档:确认 03_architecture_v1.4.md 第 3.3 节与 04_api_spec.md 第 2 节一致

## 【⛔ 动作纪律 — 两次断点】[同正文]

Step 7 — 测试:
  a) test_acceptance_pass_to_in_stock_ok:fixture.status=ACCEPTANCE_TESTING,调 transition(fix, S.IN_STOCK, 'acceptance_pass', user_id),断言状态变 IN_STOCK + history 表多一行
  b) test_acceptance_pass_wrong_trigger_raises:同上但 trigger='wrong',断言 StateMachineError

Step 8 — 烟测:[同正文]

## 【验收防线】[同正文 6 条 grep]
## 【完工汇报】[同正文格式]
```

---

## T06 - Bug 修复分析与执行

### 适用场景

线上或开发环境发现 bug,需要 CLI AI 协助定位与修复时使用。**铁律**:先根因后动手。**严禁** CLI AI 拿到 bug 描述就上手改代码。

### 需准备的参数清单

| 变量 | 含义 | 示例 |
|------|------|------|
| `[Bug 现象]` | 现象描述(用户操作 / 期望 / 实际) | "用户编辑项目后保存,前端报 500" |
| `[复现步骤]` | 1-N 步可复现 | "登录→进项目列表→点编辑→改项目名→点保存" |
| `[错误信息]` | 后端 traceback / 前端 console / 浏览器 Network 响应 | (贴 log) |
| `[影响范围]` | 受影响的端点 / 页面 / 用户角色 | "仅 PM 角色编辑项目时" |
| `[紧急度]` | `阻塞` / `重要不紧急` / `打磨` | `阻塞` |

### 提示词正文

```text
# 任务:Bug 修复 — [Bug 现象简述]

## 上下文
- 紧急度:[紧急度]
- 影响范围:[影响范围]
- 本任务范围:根因分析 + 最小化修复 + 回归测试
- 不在本任务范围:借机重构其他模块、引入新依赖、动既定架构

## 【文档约束】开工前必须复述以下条款,缺一不可

1. **CLAUDE.md 整体铁律**:修复**不得**引入任何违反 §d / §e 的新代码
   - 改 Service / Blueprint → 不得违反乐观锁 / 状态机 / DELETE 等铁律
   - 改前端 → 不得引入 `@/` 别名、裸 dayjs、硬编码角色

2. **CLAUDE.md §h 风险点 + 09_dev_rules.md Code Review Checklist**:修复完成后,自跑全套 grep 自查(详见验收防线)

3. **CLAUDE.md §g 关键流程改动同步 5 处**:若 bug 涉及状态机,修复必须 5 处同步(详 T05)

4. **09_dev_rules.md 通用 Checklist**:修复后必须问自己:
   - 改动是否更新到 Doc/?(若 bug 源自文档与代码不一致,文档优先)
   - 单元测试是否覆盖了"会再次踩到"的路径?(必须新增 1 个回归用例)

5. **CLAUDE.md §d Rule 2 + Schema-First**:**禁止**为修复 bug 临时手动 ALTER TABLE,必须走 Flask-Migrate

## 【开发动作】

**Step 1 — 根因复述**(不许跳,**不许猜**):
   - 复述 [Bug 现象] + [复现步骤] + [错误信息],用自己的话讲清楚
   - 在本地复现:跑 [复现步骤],贴出 backend log / frontend console / Network 响应
   - **如果不能复现**:说明缺什么环境/数据,**停下来**让我补充,**禁止**继续

**Step 2 — 定位根因**(给出至少 2 个候选假设,**逐一**用代码/日志证伪):
   - 候选 A:???
     * 证据:???
     * 是否成立:???
   - 候选 B:???
     * 证据:???
     * 是否成立:???
   - 结论:根因是 ???,证据链:[文件:行号] → [文件:行号]

**Step 3 — 修复方案设计**(给出**最小化**修复 + 备选方案):
   - 主方案:???(改动文件:???,预计 N 行)
   - 备选(更保守):???
   - 是否触及 CLAUDE.md §d / §e 铁律?(逐条核对)
   - 是否触及 5 处同步规则?(若涉及状态机)
   - 是否需要 DB Migration?(若是,走 Schema-First,本任务一并准备)

## 【⛔ 动作纪律 — 在此处打断点】

**禁止**未经我回复 `go` 就开始改代码。
根因分析(Step 2)与修复方案(Step 3)必须先得到我的认可。
特别注意:若你的修复方案需要**改架构文档**或**改既定铁律**,**禁止**自行决定,务必停下来标红。
回 `go` 再继续 Step 4。

## 【开发动作 续】

**Step 4 — 实施修复**:
   - 改动**只**做 Step 3 主方案描述的事,不夹带其他 refactor
   - 每个改动文件贴 diff(最小化 patch),不要贴整个文件

**Step 5 — 回归测试**:
   - 至少新增 1 个回归用例(用 T07 模板):覆盖本次 bug 的输入路径,断言修复后行为正确
   - 跑本模块全部测试(`pytest backend/tests/test_<module>.py` 或前端 vitest 对应文件),贴输出

**Step 6 — 复现路径再验证**:
   - 按 [复现步骤] 在本地再走一遍,贴出"现在好了"的证据(log / Network 响应)

**Step 7 — 文档同步**(若涉及):
   - 文档与代码哪里不一致?哪个该改?
   - 若是文档 bug → 改文档(Doc/03 / Doc/04 / Doc/09)+ CLAUDE.md §j 修订记录
   - 若是代码 bug → 是否需要在 CLAUDE.md §h 风险点 / 09_dev_rules.md 中新增防线?(把"踩过的坑"沉淀为规则)

## 【验收防线】完工后必须执行以下 grep 并贴出输出(按改动类型选择)

```bash
# 通用(任何修复都必跑)
grep -RIn "version_id_col" backend/app/models/
grep -RIn "methods=\['DELETE'\]" backend/app/blueprints/
grep -RIn "class \(PermissionError\|ValueError\|TypeError\|NotImplementedError\)" backend/app/
grep -RIn "from sqlalchemy.exc import StaleDataError" backend/app/  # 错误导入路径,期望无匹配
grep -RIn "body.get(['\"]version['\"]" backend/app/

# 若修复涉及前端
grep -RIn "from ['\"]@/" frontend/src/  # 期望无匹配
grep -RInE "(^|[^a-zA-Z])dayjs\([a-zA-Z_]" frontend/src/views/ frontend/src/components/  # 期望无匹配
grep -RIn "new Date(" frontend/src/views/ frontend/src/components/  # 期望无匹配
grep -RIn "role === " frontend/src/  # 期望无匹配

# 若修复涉及状态机
grep -A 3 "^def transition" backend/app/services/state_machine.py  # 期望签名无 force 参数
grep -RIn "force\s*=\s*True" backend/app/  # 期望仅 force_transition 内出现

# 若修复涉及导出
grep -RIn "to_excel\|pandas" backend/app/  # 期望无匹配
grep -RIn "Workbook(" backend/app/  # 期望仅 Workbook(write_only=True)
```

## 【完工汇报】格式

- Bug 现象:[Bug 现象]
- 根因:[一句话 + 文件:行号]
- 修复方案:[主方案]
- 改动文件清单 + diff 摘要:[贴]
- 回归用例:[列出测试名 + pytest 输出]
- 复现路径再验证:[贴证据]
- 文档同步:[列出文档变更,若无说明无]
- 沉淀到 CLAUDE.md §h?:[是/否 + 原因]
- 验收防线 grep 输出:[贴]
```

### 使用示例(填充 — 编辑项目报 500 的 bug)

```text
# 任务:Bug 修复 — 编辑项目保存后 500

## 上下文
- 紧急度:阻塞
- 影响范围:所有有 project.edit 权限的用户编辑项目时
- 本任务范围:根因分析 + 最小化修复 + 回归测试
- 不在本任务范围:借机重构 Project Service

## 【文档约束】[同正文 5 条]

## 【开发动作】

Step 1 — 根因复述:
  现象:PM 用户登录,进 /projects/1/edit,改 project_name 后点保存,前端 ElMessage error 弹"保存失败",
        浏览器 Network 显示 PUT /api/projects/1 → HTTP 500 {"code": 500, "message": "Internal Server Error"}
  复现步骤:登录→/projects 列表→点 1 号项目编辑→改 project_name='新名称'→点保存
  错误信息:
    backend log:
      File "app/services/project_service.py", line 87, in update_project
        if record.version != body['version']:
      KeyError: 'version'
  请你本地复现并贴更详细的 traceback。

Step 2 — 定位根因:
  候选 A:前端没传 version
    证据:浏览器 Network → Request Body 看不到 version 字段?(请贴)
    成立?:???
  候选 B:后端 GET /api/projects/:id 返回值里没带 version,前端无法回填
    证据:curl GET /api/projects/1 看 data 里是否有 version
    成立?:???
  结论:[等你给]

Step 3 — 修复方案设计:
  主方案:???(待 Step 2 出根因后,给出 patch 计划 + 估行数)
  备选:???
  是否动铁律:???
  是否需 Migration:???

## 【⛔ 动作纪律 — 打断点】
根因(Step 2)和修复方案(Step 3)必须先得到我的认可。

## 【开发动作 续】
Step 4 — 实施修复:[最小化 patch,贴 diff]
Step 5 — 回归用例:test_update_project_without_version_field_returns_400_not_500
        + test_update_project_with_correct_version_returns_200
Step 6 — 复现路径再验证:[同正文]
Step 7 — 文档同步:
  - 若根因是"前端没传 version" → 09_dev_rules.md 前端 Checklist 已有"编辑提交必含 version",
    沉淀:在该条增加"且 GET 详情接口的返回必须包含 version"
  - CLAUDE.md §h 风险点表新增一行?(看是否值得规则化)

## 【验收防线】[同正文,含通用 + 前端 + 后端]
## 【完工汇报】[同正文格式]
```

---

## T07 - 单元测试生成

### 适用场景

为已实现的 Service / 状态机 / 关键 utility 补单元测试。**不**修改被测代码;**不**新建表;**不**改前端。Phase 1+ 每个 Service 与每次状态机变更都应触发本模板。

### 需准备的参数清单

| 变量 | 含义 | 示例 |
|------|------|------|
| `[被测模块]` | Service / state_machine / utility 名 | `project_service` |
| `[被测函数列表]` | 要测的函数清单 | `list_projects` / `create_project` / `update_project` / `cancel_project` |
| `[测试文件路径]` | 测试输出位置 | `backend/tests/test_project_service.py` |
| `[覆盖场景]` | 每个函数要覆盖的场景(成功 / 失败 / 边界) | 见使用示例 |

### 提示词正文

```text
# 任务:单元测试生成 — [被测模块]

## 上下文
- 前置条件:被测模块代码已实现且通过烟测
- 本任务范围:测试用例编写 + pytest 跑通 + 覆盖率统计
- 不在本任务范围:**不修改**被测代码;**不**新建表;**不**改前端;**不**引入 mock 框架以外的新库

## 【文档约束】开工前必须复述以下条款,缺一不可

1. **CLAUDE.md §g + 09_dev_rules.md 通用 Checklist**:测试**至少**覆盖
   - 成功路径(happy path)
   - 权限拒绝(`@require_role` 装饰的接口,缺权限返 403)
   - 数据校验失败(缺字段 / 字段类型错 / 字段值非法,返 400)
   - 乐观锁冲突(写操作传过期 version,返 409)
   - 状态机 / 业务规则边界(非法 trigger 抛 StateMachineError 等)

2. **CLAUDE.md §e.5 + §e.4 + §h**:专项测试必须存在
   - 乐观锁:`test_<module>_update_with_stale_version_returns_409`
   - 状态机三函数后门防护:`test_no_back_door_in_transition`(断言 `transition` 函数签名不含 force 参数,grep 验证)
   - 自定义异常类不撞 Python 内置:可在 conftest 加一次性 grep 守卫

3. **CLAUDE.md 技术栈 + 测试库隔离策略**:Flask 3 + SQLAlchemy 2.x + Flask-Migrate
   - **必须用真 MySQL 测试库**,**不**用 SQLite(行为差异:utf8mb4 / ENUM / ON UPDATE CURRENT_TIMESTAMP 等会让测试与生产脱节)
   - `conftest.py` 中 `create_app('testing')`:动态把 `SQLALCHEMY_DATABASE_URI` 替换为测试库 URL(如 `mysql+pymysql://...:.../dbu_fixture_test?charset=utf8mb4`),与 dev 库**物理隔离**
   - Schema 准备:推荐**两选其一**(本任务沿用项目已有的 conftest 现状,不存在则用方案 A):
     * **方案 A — db.create_all() + 用例级 nested transaction**(简单,适合 MVP)
     * **方案 B — flask db upgrade 测试库 + 用例级 nested transaction**(更贴近生产,推荐 Phase 7 上线前切换)
   - **每个测试用例必须完全隔离**——简单 `db.session.rollback()` **不够**(若被测 Service 内部有 `db.session.commit()`,后续测试会看到脏数据)。**正确做法**:把每个用例包在 **connection-level transaction + nested savepoint** 里,无论被测代码 commit 多少次,用例结束统一回滚整个外层 transaction。参考 conftest 模板:
     ```python
     from sqlalchemy.orm import sessionmaker, scoped_session  # ← 必须从 sqlalchemy.orm 直接导入
                                                               #   db.sessionmaker / db.scoped_session 不存在
     @pytest.fixture(scope='function')
     def db_session(app):
         """SQLAlchemy 2.x: nested transaction + savepoint,
            被测代码内的 commit 只清空 savepoint,外层 transaction 仍可 rollback。
            用例结束后还原 db.session，避免污染后续用例。"""
         with app.app_context():
             connection = db.engine.connect()
             transaction = connection.begin()
             _original_session = db.session          # 保存原始 session，用例结束后还原
             db.session = scoped_session(
                 sessionmaker(bind=connection, join_transaction_mode='create_savepoint')
             )
             try:
                 yield db.session
             finally:
                 db.session.remove()
                 db.session = _original_session      # 还原，防止后续用例拿到已关闭的连接
                 transaction.rollback()
                 connection.close()
     ```
   - **禁止**:直接在 fixture 里 `db.drop_all()` 然后 `db.create_all()`(慢且会污染并发测试);用单个共享 session 跑全部测试(用例间脏数据互串)

4. **MVP 极简依赖**:**禁止**引入 `factory_boy` / `faker` / `pytest-factoryboy` / `mimesis` 等新测试库;用 `pytest.fixture` 手写 seed 数据足够,后续如需再走架构评审

5. **CLAUDE.md §d Rule 4 + @require_role 对齐**:`get_jwt_identity()` 返回 str,JWT fixture 创建 token 时 identity 传 str；**同时必须加 `additional_claims={'role_codes': [...]}`**，否则 `@require_role` 读取 claims 时 role_codes 为空列表，所有需要角色的端点静默返回 403，正向测试全挂且**无明显报错**：
   ```python
   # ✅ 正确 — identity str + additional_claims 同时传
   create_access_token(identity=str(user.id), additional_claims={'role_codes': ['pm']})

   # ❌ 错误 — 缺 additional_claims，require_role 永远 403
   create_access_token(identity=str(user.id))
   ```

6. **CLAUDE.md §e.9**:`send_alert_dedup` 测试时必须 patch SMTP(`mocker.patch('flask_mail.Mail.send')`),断言失败不抛出,断言去重表 / 日志被正确记录

7. **测试文件命名**:`test_<被测模块>.py`,放 `backend/tests/`;测试函数 `test_<scenario>_<expected>`(snake_case);**严禁**测试代码内 `print` 调试,用 `caplog` fixture 验证日志

## 【开发动作】

**Step 1 — 用例矩阵设计**(必须先列在对话里,**不准**先写代码):

   对 [被测函数列表] 逐函数列矩阵,例如:

   | 函数 | 场景 | 期望 |
   |------|------|------|
   | create_project | 合法 payload | 返回新 project,project_code 已生成,DB 中能查到 |
   | create_project | 缺 project_name | ValidationError(400) |
   | create_project | 缺权限调用(role=iqc) | ForbiddenError(403) |
   | update_project | 合法 + 正确 version | 字段更新成功,record.version + 1 |
   | update_project | 缺 version 字段 | ValidationError(400) |
   | update_project | version 过期 | ConflictError(409) |
   | cancel_project | 合法 + 状态 active | status='cancelled', cancelled_at / cancelled_by 写入 |
   | cancel_project | 状态已是 cancelled | ValidationError 或幂等?(看架构文档决策) |
   | list_projects | 默认参数 | 返回 page=1, page_size=20 |
   | list_projects | 过滤 product_type=SUS_VC | 仅返回该产品线 |

**Step 2 — conftest.py 检查/补充**:
   - 是否已有 `app fixture`(create_app('testing'))?若无,创建
   - 是否已有 `db fixture`(每个测试 setup 建表 / teardown 清空,或 transaction rollback)?
   - 是否已有 `client fixture`(Flask test client)?
   - 是否已有 `auth_headers fixture`(按 role 生成 JWT token)?

**Step 3 — 编写测试文件**:
   - 文件 [测试文件路径]
   - 用 `pytest.fixture` 准备测试数据(避免 hard-code id)
   - 每个测试只测一件事
   - 断言用 `assert response.status_code == 409` + `assert response.get_json()['code'] == 409`(双层断言)
   - 状态机相关用例必加 `test_no_back_door_in_transition`:
     ```python
     def test_no_back_door_in_transition():
         """transition() 函数签名不得含 force / bypass 参数(防止 V1.2 后门重现)"""
         import inspect
         from app.services.state_machine import transition
         sig = inspect.signature(transition)
         assert 'force' not in sig.parameters
         assert 'bypass' not in sig.parameters
     ```
   - 乐观锁用例:
     ```python
     def test_update_<entity>_stale_version_returns_409(client, auth_headers, seeded_<entity>):
         payload = { 'project_name': 'X', 'version': seeded_<entity>.version - 1 }
         res = client.put(f'/api/projects/{seeded_<entity>.id}', json=payload, headers=auth_headers['pm'])
         assert res.status_code == 409
         assert res.get_json()['code'] == 409
     ```

**Step 4 — 跑测试**:
   - `pytest [测试文件路径] -v`(贴完整输出)
   - 若失败,逐个分析:被测代码 bug → 走 T06;测试 bug → 改测试

**Step 5 — 覆盖率**(可选,有 coverage 工具时):
   - **注意**:`pytest --cov` 在本项目会与 `cryptography`（PyO3 编译）冲突，改用：
     ```bash
     coverage run -m pytest [测试文件路径]
     coverage report --include="app/services/<被测模块>.py" --show-missing
     ```
   - 报告覆盖率,目标 ≥ 80%(关键写路径 100%)

## 【⛔ 动作纪律 — 在此处打断点】

**禁止**未经我回复 `go` 就修改被测代码。
若测试跑挂,**先**分析根因:
- 被测代码 bug:**停下来**,告诉我,转 T06(本任务范围严禁改被测代码)
- 测试 bug:可继续调测试
- conftest fixture 问题:可调 conftest

## 【开发动作 续】

**Step 6 — 整理交付**:
   - 列出新增测试函数清单(函数名 + 一句话场景)
   - 列出本次测试发现的潜在 bug(若有,转 T06)
   - 贴出最终 pytest 输出

## 【验收防线】完工后必须执行以下 grep / 命令并贴出输出

```bash
# 1. 测试文件存在且可被发现
ls -la backend/tests/test_<被测模块>.py
pytest --collect-only backend/tests/test_<被测模块>.py | head -30

# 2. 状态机后门防护测试存在(若被测模块涉及状态机)
grep -RIn "def test_no_back_door_in_transition" backend/tests/

# 3. 乐观锁冲突测试存在(若被测模块有 PUT/PATCH 接口)
grep -RIn "stale_version_returns_409\|version_conflict" backend/tests/

# 4. 权限拒绝测试存在(若被测模块有 @require_role 装饰)
grep -RIn "returns_403\|forbidden\|unauthorized_role" backend/tests/

# 5. 严禁测试代码内引入新库
grep -RIn "import factory\|import faker" backend/tests/test_<被测模块>.py
# 期望:无匹配(MVP 不引入新依赖)

# 6. 严禁测试代码绕过铁律(测试代码本身也不许 @/、裸 dayjs 等,虽然 backend 不太可能)
grep -RIn "current_status\s*=" backend/tests/test_<被测模块>.py
# 期望:无匹配(测试也要走 state_machine.py)
```

## 【完工汇报】格式

- 测试文件:[路径]
- 新增测试函数(N 个):[列出函数名 + 一句话场景]
- pytest 输出:[贴]
- 覆盖率(若跑):X%
- 发现的潜在 bug(若有):[列出,等待启动 T06]
- 验收防线 6 条 grep 输出:[贴]
```

### 使用示例(填充 Phase 1 — project_service 单元测试)

```text
# 任务:单元测试生成 — project_service

## 上下文
- 前置条件:T01 + T02 已完成,Project Model / project_service.py / project Blueprint 烟测通过
- 本任务范围:backend/tests/test_project_service.py + conftest 必要 fixture
- 不在本任务范围:不改 project_service.py / 不动 Model / 不改前端

## 【文档约束】[同正文 7 条]

## 【开发动作】

Step 1 — 用例矩阵:
  | 函数 | 场景 | 期望 |
  |------|------|------|
  | create_project | role=pm,合法 payload(name + product_type=SUS_VC + owner_id) | 201,返回 project_code 不为空,DB 多一条记录 |
  | create_project | role=pm,缺 project_name | 400(ValidationError) |
  | create_project | role=iqc(无权限) | 403(ForbiddenError) |
  | update_project | role=pm,正确 version | 200,project_name 更新,record.version=2 |
  | update_project | role=pm,缺 version 字段 | 400(version is required) |
  | update_project | role=pm,version 过期 | 409(ConflictError) |
  | cancel_project | role=pm,active 项目 | 200,status='cancelled',cancelled_at/by 写入 |
  | list_projects | 默认(无过滤) | 200,page=1,page_size=20 |
  | list_projects | product_type=SUS_VC 过滤 | 仅返回 SUS_VC |

Step 2 — conftest.py:
  - app fixture(create_app('testing'))
  - db fixture(每个测试 transaction rollback)
  - auth_headers fixture(返回 dict { 'pm': {Authorization: Bearer ...}, 'iqc': {...}, 'super_admin': {...} })
  - seeded_project fixture(预建一个 active 项目,version=1)

Step 3 — 测试文件 backend/tests/test_project_service.py:
  按矩阵逐个写 test_create_project_*、test_update_project_*、test_cancel_project_*、test_list_projects_*

Step 4 — pytest backend/tests/test_project_service.py -v

## 【⛔ 动作纪律 — 打断点】[同正文]

Step 5(可选)— 覆盖率
Step 6 — 整理交付

## 【验收防线】[同正文 6 条,被测模块名替换 project_service]
## 【完工汇报】[同正文格式]
```

---

## 修订记录

| 日期 | 内容 | 操作人 |
|------|------|--------|
| 2026-05-11 | 初版:T01-T07 共 7 个模板,每模板含适用场景 / 参数清单 / 提示词正文(含【文档约束】【开发动作】【⛔ 动作纪律】【验收防线】4 段)/ 使用示例。所有铁律直接引用 CLAUDE.md §d/§e/§h 与 09_dev_rules.md 后端 11 条 + 前端 8 条 + Checklist。技术栈固定 Flask 3 / SQLAlchemy 2.x / Vue 3 / Element Plus / Pinia,不得引入其他库。 | Claude |
| 2026-05-11 | 第二轮整合 CLI AI 评审建议:① 顶部"使用规则"加第 5 条 Git Bash 环境要求;② T01 适用场景扩展至"新建表 + 字段变更",Step 2/5 措辞同步;③ T02 Blueprint 注册位置改为 `blueprints/__init__.py:register_blueprints(app)`(对齐项目实际结构);④ T03 axios 导入路径 `./request`;⑤ T03 文档约束第 3 条补 `utils/status.js` 前置说明;⑥ T05 文档约束第 5 条 trigger 取值表解耦,改为引用 `04_api_spec.md` 单一来源;⑦ T07 文档约束第 3 条改为"真 MySQL 测试库 + nested transaction + savepoint"模式(技术修正:简单 rollback 在 Service 内 commit 时不够),并新增"MVP 极简依赖"独立成第 4 条,JWT identity / send_alert_dedup mock / 文件命名顺延至 5-7 条;⑧ 新增 T00 会话启动与上下文同步模板,作为每次新 CLI 会话第一条强制运行。 | Claude |
| 2026-05-11 | 第三轮勘误:① T00 铁律复述计数修正：删去错误的"19+4+8=31 条"，改为"§d+§e 共 26 条；09_dev_rules.md 后端 11+前端 8 由各模板验收防线 grep 覆盖"；② T02 Blueprint 注册路径纠偏：`blueprints/__init__.py:register_blueprints(app)` 实为空文件不存在该函数，改回 `app/__init__.py` `create_app()` ⑤处直接 register_blueprint（与 auth_bp 现有写法一致）；同步修正断点文本与完工汇报格式。 | Claude |
| 2026-05-13 | Phase 1 Step 1-1-3 实战修正 T07：① conftest 模板修正（`db.sessionmaker`/`db.scoped_session` 不存在，改为 `from sqlalchemy.orm import sessionmaker, scoped_session`）；② 补 `_original_session` 保存/还原与 `try/finally`（防用例失败时连接未归还）；③ 文档约束第 5 条补 `additional_claims={'role_codes': [...]}` 必须与 `@require_role` 对齐（缺失时正向用例全返 403 且无明显报错）；④ Step 5 覆盖率命令改为 `coverage run -m pytest`（`pytest --cov` 与 PyO3/cryptography 包冲突）。 | Claude |
