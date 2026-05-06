# 报表导出规约

> 摘自 V1.3 架构文档第 3.7 节"报表导出三档策略"。
>
> **核心目标**:从源头规避大数据量导出导致的 OOM(内存溢出)问题。所有报表导出必须明确归入下述三档之一。
>
> ⚠️ **本系统禁绝一切基于轮询的用户触发异步导出**(详见 §五"明确禁止")。

---

## 一、三档策略总览(V1.3 标准)

| 场景 | 方案 | 实现位置 |
|------|------|----------|
| **单表列表 < 1000 条** | 前端 xlsx 库 | 浏览器内 JSON → Excel |
| **多表关联 / >1000 条** | 后端流式响应 | `services/export_service.py` + `yield` |
| **月度大报表** | APScheduler 后台生成 | 每月 1 日 02:30 跑,结果存 `attachments` |

**判定优先级**:从上到下逐级判定。前一档放不下才走下一档,不允许越级使用。

---

## 二、第一档:前端 `xlsx` 库直接生成(单表列表 < 1000 条)

**适用场景**:单个项目的治具列表、单批次的甘特数据、单台治具的状态历史等。

**实现要点**:
- 数据已在前端表格中渲染或一次性 GET 拿到,**不重新发请求,不调后端导出接口**
- 前端用 `xlsx` 库(SheetJS)在浏览器中合成 .xlsx 文件并触发下载
- 不消耗后端资源,不写临时文件
- 无需进度条

**注意事项**:
- ⚠️ 严禁用此方案导出 1000 行以上数据,浏览器易卡顿/崩溃
- ⚠️ 数据量临界(800~1200 行)时,应在 UI 上提示用户改用筛选条件或走第二档
- 中文字段需确保 `sheetName` 不超过 31 字符(Excel 限制)

### 前端代码骨架

```javascript
// frontend/src/utils/export.js
import * as XLSX from 'xlsx'
import { formatBackendTime } from './datetime'   // V1.4 强制规范

export function exportFixtureList(rows, filename = 'fixtures.xlsx') {
  // 字段映射 + 时间格式化
  const data = rows.map(r => ({
    '治具编码': r.fixture_code,
    '当前状态': r.status_label,
    '所属项目': r.project_name,
    '创建时间': formatBackendTime(r.created_at),
    '采购价格': r.purchase_price ?? '-',
  }))
  const ws = XLSX.utils.json_to_sheet(data)
  const wb = XLSX.utils.book_new()
  XLSX.utils.book_append_sheet(wb, ws, '治具清单')
  XLSX.writeFile(wb, filename)         // 浏览器触发下载
}
```

---

## 三、第二档:后端流式响应(多表关联 / >1000 条)

**适用场景**:跨项目的治具汇总、按状态过滤的报修记录、含 JOIN 的成本明细等。

**实现要点**:
- 用户在前端点击"导出"按钮 → 浏览器同步等待 → 后端边查边写边响应
- 后端必须用 `openpyxl` 的 **`Workbook(write_only=True)` 模式**
- 数据库查询用 `limit/offset` 分页(`page_size=500`)逐批拉取,**禁止 `query.all()` 一次性加载**
- 响应通过 `yield` 流式输出,内存占用恒定(不随数据量增长)
- 用户在请求生命周期内等待(一般 5~30 秒)

**对外接口**:
- `GET /api/projects/export?ids=&format=xlsx`
- `GET /api/fixtures/export?...&format=xlsx`

### 后端代码骨架(V1.3 摘录)

```python
# app/services/export_service.py
import openpyxl
from pathlib import Path
import tempfile

def export_fixtures_streaming(filters):
    """openpyxl write_only 模式 + 分页查询,内存占用恒定"""
    wb = openpyxl.Workbook(write_only=True)
    ws = wb.create_sheet("Fixtures")
    ws.append(['编码','项目','批次','类型','状态','计划到货','实际到货'])

    page_size = 500
    page = 0
    while True:
        rows = Fixture.query.filter_by(**filters).limit(page_size).offset(
            page * page_size).all()
        if not rows:
            break
        for r in rows:
            ws.append([r.fixture_code, r.project.project_code, ...])
        page += 1

    tmp = tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False)
    wb.save(tmp.name)
    return tmp.name
```

**注意事项**:
- ⚠️ **严禁使用 `pandas.DataFrame.to_excel`**(默认全量加载到内存)
- ⚠️ **严禁使用 `openpyxl` 默认(非 write_only)模式**(会持有所有 Cell 对象)
- ⚠️ 单元格内嵌入字符串需做长度检查(>32767 字符会异常)
- 临时文件必须在响应完成后清理(`tempfile.NamedTemporaryFile(delete=False)` 后由调用方在响应钩子中删除,或定期任务清理 tmp 目录)

---

## 四、第三档:APScheduler 月度大报表(预生成,非用户触发)

**适用场景**:跨年度全部治具档案、年度/季度成本汇总、所有维修记录的月度统计等。

**核心原则**:**不是用户触发,是定时任务自动跑**。

**实现要点**:
- **APScheduler 注册定时任务**:每月 1 日 02:30 自动执行
- 任务调用 `services/export_service.py` 的批量生成函数,产出 .xlsx 文件
- 文件落盘到 `D:\dbu\reports\` 临时区,同时向 `attachments` 表插入记录
- 用户在系统的"附件中心"或"月度报表"页面去下载,**没有专门的触发导出 API**
- 旧报表通过 `attachments` 表的清理任务定期归档/清理

**用户工作流**:

```
                ┌──────────────────────────────────┐
                │  每月 1 日 02:30                  │
                │  APScheduler 自动跑               │
                │  → 生成 xlsx                      │
                │  → 写 attachments 表              │
                └──────────────────────────────────┘
                              │
                              ▼
       用户在"附件中心"看到本月新增的报表 → 点下载
```

**注意事项**:
- ⚠️ 该任务必须包 try/except,失败时记日志,可发邮件通知管理员
- ⚠️ 同样使用 `openpyxl(write_only=True)` + 分页查询,**禁止** `pandas.to_excel`
- ⚠️ 如未来确实需要"用户按需触发的大报表",必须经架构评审,**不允许 AI 或开发者临时加用户触发的异步任务接口绕过本规约**

### 定时任务示例

```python
# app/tasks/monthly_report.py
from app.extensions import scheduler
from app.services.export_service import export_fixtures_streaming
from app.models import Attachment, db

@scheduler.task('cron', id='monthly_full_report', day=1, hour=2, minute=30)
def generate_monthly_report():
    """每月 1 日 02:30 自动生成全量月度报表"""
    try:
        file_path = export_fixtures_streaming(filters={})  # 全量
        att = Attachment(
            file_path=file_path,
            file_type='monthly_report',
            related_table='reports',
            uploaded_by_id=None,   # 系统生成
        )
        db.session.add(att)
        db.session.commit()
    except Exception as e:
        scheduler.app.logger.error(
            f"Monthly report generation failed: {e}", exc_info=True
        )
        # 可选:邮件通知管理员
        db.session.rollback()
```

---

## 五、明确禁止(V1.4 强化)

以下做法**严禁**出现在本系统:

1. ❌ **不允许"用户触发异步导出 + 邮件下载链接"模式**
   原因:增加状态轮询接口、token 鉴权链接、清理任务等额外复杂度,V1.3 明确选择了"月度定时预生成 + 附件中心"这一更简单的方案。
2. ❌ **不允许 `pandas.DataFrame.to_excel`**
   原因:全量加载到内存,数据量大时 OOM。
3. ❌ **不允许 `openpyxl` 默认(非 write_only)模式**
   原因:持有所有 Cell 对象,内存占用线性增长。
4. ❌ **不允许在前端 xlsx 库导出 > 1000 行**
   原因:浏览器卡崩,且无法处理多表关联。
5. ❌ **不允许跨档使用**(例如:用前端 xlsx 导出 5000 行,或用第二档接口生成跨年度大报表)

---

## 六、判断使用哪一档的速查表

| 场景 | 行数预估 | 用哪一档 |
|------|----------|----------|
| 单项目治具列表 | < 100 | 第一档(前端) |
| 单项目甘特图导出 | < 200 | 第一档(前端) |
| 单批次详情导出 | < 100 | 第一档(前端) |
| 全公司在用治具列表 | 500 ~ 2,000 | 第二档(后端流式) |
| 季度报修记录 | 2,000 ~ 5,000 | 第二档(后端流式) |
| 跨项目成本明细(含 JOIN) | 任意行数 | 第二档(后端流式) |
| 月度全量治具档案 | > 10,000 | 第三档(APScheduler 预生成) |
| 年度成本汇总(全部子项) | > 10,000 | 第三档(APScheduler 预生成) |

---

## 七、铁律小结

1. **第一档**:前端 SheetJS,不走后端,< 1000 行
2. **第二档**:后端 `openpyxl(write_only=True)` + 游标分批,流式响应,**禁止 `pandas.to_excel`**
3. **第三档**:APScheduler 每月 1 日 02:30 自动跑 + 存 `attachments`,**不开放用户触发**
4. **第四档?不存在**。任何超出三档的需求必须经架构评审。
