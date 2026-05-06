# 备份与还原手册(Windows Server)

> 摘自 V1.3 架构文档第 1.4 节"备份与还原策略[V1.3 修订:Windows Server 原生]"。
>
> ⚠️ **警告:还原操作需谨慎,建议在测试环境先演练。**
> 误操作可能导致生产数据不可逆丢失,所有操作必须由有权限的运维人员执行,并保留操作记录。

---

## 一、备份目标与频率(V1.3 标准)

| 对象 | 工具 | 频率 | 保留策略 | 存放位置 |
|------|------|------|----------|----------|
| MySQL 数据 | `mysqldump.exe` | 每天 02:00 | **每日 7 + 每周 4 + 每月 12** | `D:\dbu\backup\mysql\` |
| 附件目录 | `robocopy /MIR` | 每天 03:00 | **每日 7** | `D:\dbu\backup\uploads\` |
| 完整目录归档 | 7-Zip 命令行 | 每周一次(周一 04:00) | **保留 4 周** | `D:\dbu\backup\snapshot\` |

**备份目录建议同时同步至独立物理磁盘或 NAS**,避免磁盘故障导致备份失效。

---

## 二、备份脚本

### 2.1 MySQL 每日备份

`D:\dbu\scripts\backup_mysql.bat`(摘自 V1.3):

```batch
@echo off
set BACKUP_DIR=D:\dbu\backup\mysql
set DATE_TAG=%date:~0,4%-%date:~5,2%-%date:~8,2%
set MYSQL_PWD=<密码,从 .env.production 读取或经过加密 Vault>

if not exist "%BACKUP_DIR%" mkdir "%BACKUP_DIR%"

"C:\Program Files\MySQL\MySQL Server 8.4\bin\mysqldump.exe" ^
  --default-character-set=utf8mb4 ^
  --single-transaction --routines --triggers ^
  -u root -p%MYSQL_PWD% ^
  dbu_fixture > "%BACKUP_DIR%\dbu_fixture_%DATE_TAG%.sql"

:: 删除 7 天前的每日备份(每周/每月备份由独立脚本归档,不在此处清理)
forfiles /P "%BACKUP_DIR%" /M *.sql /D -7 /C "cmd /c del @path" 2>nul

echo [%date% %time%] Backup completed >> D:\dbu\logs\backup.log
```

**关键点**:必须加 `--default-character-set=utf8mb4`,否则中文乱码(继承自 vc-cost-system 已踩的坑)。

### 2.2 附件每日备份

`D:\dbu\scripts\backup_uploads.bat`(摘自 V1.3):

```batch
@echo off
robocopy D:\dbu\uploads D:\dbu\backup\uploads /MIR /R:2 /W:5 ^
  /LOG+:D:\dbu\logs\backup_uploads.log
```

`/MIR` 模式镜像源目录,自动反映新增/删除/修改;robocopy 退出码 0~7 都视为成功。

### 2.3 周快照(7-Zip 完整目录归档)

`D:\dbu\scripts\backup_snapshot.bat`(基于 V1.3 第 1.4 节 7-Zip 周备份要求):

```batch
@echo off
set SNAPSHOT_DIR=D:\dbu\backup\snapshot
set DATE_TAG=%date:~0,4%-%date:~5,2%-%date:~8,2%

if not exist "%SNAPSHOT_DIR%" mkdir "%SNAPSHOT_DIR%"

:: 用 7-Zip 把 mysql 当日备份 + uploads 一起打包
"C:\Program Files\7-Zip\7z.exe" a -t7z ^
  "%SNAPSHOT_DIR%\dbu_snapshot_%DATE_TAG%.7z" ^
  "D:\dbu\backup\mysql\dbu_fixture_%DATE_TAG%.sql" ^
  "D:\dbu\backup\uploads\"

:: 删除 28 天前的周快照
forfiles /P "%SNAPSHOT_DIR%" /M *.7z /D -28 /C "cmd /c del @path" 2>nul

echo [%date% %time%] Weekly snapshot completed >> D:\dbu\logs\backup.log
```

### 2.4 任务计划程序配置(V1.3 标准)

```powershell
# PowerShell 创建任务(管理员执行)
schtasks /Create /SC DAILY /ST 02:00 /TN "DBU-Backup-MySQL" ^
  /TR "D:\dbu\scripts\backup_mysql.bat" /RU SYSTEM /F

schtasks /Create /SC DAILY /ST 03:00 /TN "DBU-Backup-Uploads" ^
  /TR "D:\dbu\scripts\backup_uploads.bat" /RU SYSTEM /F

schtasks /Create /SC WEEKLY /D MON /ST 04:00 /TN "DBU-Backup-Snapshot" ^
  /TR "D:\dbu\scripts\backup_snapshot.bat" /RU SYSTEM /F
```

**勾选要点**:
- "无论用户是否登录都要运行"
- "使用最高权限运行"
- 用户账户:`SYSTEM`

---

## 三、还原流程(标准操作步骤)

> ⚠️ **以下操作会停止生产服务并覆盖现有数据**,执行前必须:
> 1. 通知所有用户停止使用系统
> 2. 在测试环境完整演练过本流程
> 3. **执行 Step 0:对当前生产数据再做一次"应急快照"备份**(强制)
> 4. 准备好回滚方案

### Step 0:应急快照备份(V1.4 强制第一步)

⚠️ **本步骤为强制项,不可跳过。** 在覆盖任何生产数据前,先把"还原前"的当前状态保留下来,以便发现还原后数据有问题时能回退到还原前的状态。

```batch
:: 0.1 创建当日应急快照目录
set TODAY=%date:~0,4%%date:~5,2%%date:~8,2%
mkdir D:\dbu\emergency_snapshot\%TODAY%

:: 0.2 dump 当前生产数据库
"C:\Program Files\MySQL\MySQL Server 8.4\bin\mysqldump.exe" ^
  --default-character-set=utf8mb4 ^
  --single-transaction --routines --triggers ^
  -u root -p<密码> dbu_fixture ^
  > D:\dbu\emergency_snapshot\%TODAY%\before_restore.sql

:: 0.3 镜像当前 uploads 目录
robocopy D:\dbu\uploads D:\dbu\emergency_snapshot\%TODAY%\uploads /MIR /R:2 /W:5

:: 0.4 校验快照文件存在且非零字节
dir D:\dbu\emergency_snapshot\%TODAY%
:: 必须看到 before_restore.sql 文件大小 > 0,uploads 目录有内容
```

**只有 Step 0 全部成功后,才能进入 Step 1。** 如果快照失败(磁盘满、MySQL 不可达等),立即停止还原流程,先解决环境问题。

### Step 1:停止服务

```powershell
# 以管理员身份打开 PowerShell
nssm stop DBU-Fixture-Backend
# 等待几秒确认服务已停
nssm status DBU-Fixture-Backend
# 应输出 SERVICE_STOPPED
```

### Step 2:还原 MySQL 数据库(V1.3 核心命令)

```batch
:: 1. 选择要还原的备份文件(从 mysql/、snapshot/ 中选)
set BACKUP_FILE=D:\dbu\backup\mysql\dbu_fixture_2026-04-25.sql

:: 2. 还原(V1.3 推荐:直接 mysql 客户端导入)
"C:\Program Files\MySQL\MySQL Server 8.4\bin\mysql.exe" ^
  --default-character-set=utf8mb4 ^
  -u root -p<密码> dbu_fixture < %BACKUP_FILE%
```

**关键点**:导入时必须显式 `--default-character-set=utf8mb4`,否则中文将变成 `?` 或乱码。

> **建议**:如果备份文件来自不同 schema 版本,先 `DROP DATABASE; CREATE DATABASE` 重建库以保证字符集干净一致。但 V1.3 默认假设 schema 一致,直接覆盖导入即可。

### Step 3:还原附件目录

```batch
:: V1.3 推荐:用 robocopy /MIR 镜像还原
robocopy D:\dbu\backup\uploads D:\dbu\uploads /MIR /R:2 /W:5
```

### Step 4:数据校验(V1.3 标准命令)

```batch
:: V1.3 给出的核心校验命令
"C:\Program Files\MySQL\MySQL Server 8.4\bin\mysql.exe" ^
  -u root -p<密码> dbu_fixture -e "SELECT COUNT(*) FROM fixtures;"
```

补充校验项:

```batch
:: 检查表数量与字符集
"C:\Program Files\MySQL\MySQL Server 8.4\bin\mysql.exe" -u root -p<密码> -e ^
  "USE dbu_fixture; SHOW TABLES; SELECT TABLE_NAME, TABLE_COLLATION FROM information_schema.TABLES WHERE TABLE_SCHEMA='dbu_fixture' LIMIT 5;"
```

预期:`TABLE_COLLATION` 全部为 `utf8mb4_unicode_ci`。

```batch
:: 抽查中文是否正常(不应出现 ? 或 □ 等乱码)
"C:\Program Files\MySQL\MySQL Server 8.4\bin\mysql.exe" --default-character-set=utf8mb4 ^
  -u root -p<密码> -e "USE dbu_fixture; SELECT id, project_name FROM projects LIMIT 5;"
```

```batch
:: 抽查附件目录文件数量
dir D:\dbu\uploads /s /b | find /c /v ""
```

### Step 5:启动服务

```powershell
nssm start DBU-Fixture-Backend
nssm status DBU-Fixture-Backend
# 应输出 SERVICE_RUNNING

# 检查日志
Get-Content D:\dbu\logs\app.log -Tail 30
```

### Step 6:业务验证

由 PM 或测试人员登录系统,至少验证:

- [ ] 登录正常,用户列表完整
- [ ] 任意一个项目可以打开,治具列表可见
- [ ] 任意一份图纸/附件可以正常下载查看
- [ ] 中文显示正常(项目名、治具名、备注等)
- [ ] 时间字段无 8 小时偏差(创建时间应为 GMT+8 显示)
- [ ] 创建一条新记录确认写入正常

### Step 7:回滚预案(若 Step 6 验证失败)

如果业务验证发现还原后的数据有问题,使用 Step 0 的应急快照回滚:

```batch
nssm stop DBU-Fixture-Backend

"C:\Program Files\MySQL\MySQL Server 8.4\bin\mysql.exe" ^
  --default-character-set=utf8mb4 ^
  -u root -p<密码> dbu_fixture < D:\dbu\emergency_snapshot\%TODAY%\before_restore.sql

robocopy D:\dbu\emergency_snapshot\%TODAY%\uploads D:\dbu\uploads /MIR /R:2 /W:5

nssm start DBU-Fixture-Backend
```

---

## 四、附:常见问题排查

| 故障现象 | 可能原因 | 处理 |
|----------|----------|------|
| 中文显示 ??? | mysql 客户端字符集错误 | 加 `--default-character-set=utf8mb4` 重导 |
| 时间偏差 8 小时 | MySQL 时区配置错误 | 检查 `SELECT @@global.time_zone, @@session.time_zone;` |
| 附件链接 404 | uploads 目录文件缺失或权限错误 | 用 `icacls` 修复 NSSM 服务账户权限 |
| 服务启动失败 | 数据库连接失败 / 端口占用 | 看 `D:\dbu\logs\nssm_stderr.log` 与 `app.log` |
| 字段缺失报错 | 备份与代码版本不匹配 | 备份必须与代码版本配套,跨版本还原前先回滚代码 |
| robocopy 退出码 8+ | 部分文件复制失败 | 看 robocopy 日志,通常是文件被占用,停服务重试 |

---

## 五、还原演练制度(V1.3 强制)

> 摘自 V1.3 第 1.4 节末段。

- **上线前**:必做 1 次完整还原演练,必须由非备份制作人执行
- **上线后**:每月抽查 1 次最近的备份,做"还原到测试库 + 校验关键表"快速验证
- **每次重大升级前**:先备份再演练,确保新版本与备份兼容
