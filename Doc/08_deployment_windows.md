# Windows Server 生产部署手册

> 摘自 V1.4 架构文档第 1.3 / 1.4 / 1.5 节，整合为完整可执行的部署指南。
>
> **目标环境**：Windows Server（建议 2019 或更高版本），单机部署，局域网访问。
>
> **预计耗时**：首次部署 4~6 小时（含 IT 协调、防火墙、备份配置）。

---

## 一、前置条件检查

部署开始前，确认服务器满足以下条件：

| 项目 | 要求 | 验证命令 |
|------|------|----------|
| 操作系统 | Windows Server 2019 / 2022 | `winver` |
| 磁盘空间 | C:\ 至少 50GB / D:\ 至少 200GB | `wmic logicaldisk get caption,freespace,size` |
| 管理员权限 | 当前账户须为本机管理员 | `whoami /groups` 查 BUILTIN\Administrators |
| 内存 | 建议 16GB 以上 | `wmic OS get TotalVisibleMemorySize` |
| 网络 | 5000 端口可对内网开放 | `netstat -ano \| findstr :5000`（部署前应无返回） |
| 时区 | GMT+8（中国标准时间） | `tzutil /g` 应输出 `China Standard Time` |

### 1.1 安装 Python 3.12

1. 从 https://www.python.org/downloads/ 下载 Python 3.12 Windows 64-bit installer
2. **务必勾选 "Add Python to PATH"**
3. 安装路径建议 `C:\Python312\`
4. 验证：

```powershell
python --version    # 应输出 Python 3.12.x
pip --version
```

### 1.2 安装 MySQL 8.4 LTS

1. 从 https://dev.mysql.com/downloads/installer/ 下载 MySQL Installer
2. 选择 "Server only" 模式安装
3. 配置项：
   - 端口：`3306`
   - 字符集：选择 **Use Strong Encoding (utf8mb4)**
   - root 密码：复杂密码，**记录到密码管理器**
   - 启动类型：**Windows Service - 自动启动**
4. 验证：

```powershell
"C:\Program Files\MySQL\MySQL Server 8.4\bin\mysql.exe" -uroot -p -e "SELECT VERSION();"
```

5. **关键**：检查时区配置，确认与服务器一致：

```sql
SELECT @@global.time_zone, @@session.time_zone;
-- 应输出 SYSTEM 或 +08:00（Windows Server 时区为 GMT+8 时自动继承）
```

### 1.3 安装 NSSM（Windows 服务包装器）

1. 从 https://nssm.cc/download 下载 nssm-2.24.zip
2. 解压，将 `win64\nssm.exe` 拷贝到 `C:\Windows\System32\`（或加入 PATH）
3. 验证：

```powershell
nssm version
```

### 1.4 创建目录结构

```powershell
mkdir C:\dbu
mkdir C:\dbu\backend
mkdir C:\dbu\frontend
mkdir D:\dbu\uploads
mkdir D:\dbu\logs
mkdir D:\dbu\backup\mysql
mkdir D:\dbu\backup\uploads
mkdir D:\dbu\reports
mkdir D:\dbu\scripts
```

---

## 二、应用部署

### 2.1 拉取代码

```powershell
cd C:\dbu
git clone <repo_url> backend
git clone <frontend_repo_url> frontend
```

或使用本地拷贝方式（U 盘 / 共享盘）。

### 2.2 创建 Python 虚拟环境

```powershell
cd C:\dbu\backend
python -m venv venv
.\venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt
pip install waitress python-dotenv
```

### 2.3 配置生产环境变量

创建 `C:\dbu\backend\.env.production`（**禁止提交到 git**）：

```ini
FLASK_ENV=production
DATABASE_URL=mysql+pymysql://root:YOUR_PROD_PASSWORD@localhost:3306/dbu_fixture?charset=utf8mb4

JWT_SECRET=GENERATE_A_LONG_RANDOM_STRING_AT_LEAST_64_CHARS

UPLOAD_BASE=D:/dbu/uploads
LOG_DIR=D:/dbu/logs

SMTP_HOST=smtp.company.com
SMTP_PORT=25
SMTP_USERNAME=dbu-system@company.com
SMTP_PASSWORD=YOUR_SMTP_PASSWORD
MAIL_DEFAULT_SENDER=dbu-system@company.com
```

**安全要点**：
- 路径用正斜杠 `/`（`pathlib.Path` 跨平台处理）
- `JWT_SECRET` 至少 64 字符随机串，绝不复用开发环境值
- 文件 NTFS 权限设为仅 SYSTEM 与本机 Administrators 可读：

```powershell
icacls C:\dbu\backend\.env.production /inheritance:r /grant:r "SYSTEM:R" "Administrators:R"
```

### 2.4 创建数据库

```powershell
"C:\Program Files\MySQL\MySQL Server 8.4\bin\mysql.exe" -uroot -p -e ^
  "CREATE DATABASE dbu_fixture CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
```

### 2.5 执行迁移与种子数据

```powershell
cd C:\dbu\backend
.\venv\Scripts\activate
$env:FLASK_ENV="production"
$env:FLASK_APP="run.py"

flask db upgrade        # 应用 migrations/ 下所有迁移
flask seed              # 写入超管账号 / 9 角色 / 11 供应商 / 40+ 治具模板
```

**种子完成后立即修改超管初始密码**（密码取自 .env，登录后强制改）。

---

## 三、前端构建与拷贝

在**开发机**完成构建：

```powershell
cd <frontend-source>
pnpm install
pnpm build
# 产出在 dist/ 目录
```

将 `dist/` 整体拷贝到生产机：

```powershell
robocopy <开发机dist路径> C:\dbu\frontend\dist /MIR
```

**MVP 方案**：Flask 通过 `static_folder` 直接 serve `C:\dbu\frontend\dist`，无需 nginx。
（详细配置见 V1.4 第 1.3 节）

---

## 四、NSSM 注册 Windows 服务

### 4.1 创建 serve.py（如代码中尚无）

`C:\dbu\backend\serve.py`：

```python
from waitress import serve
from app import create_app
import os

os.environ.setdefault('FLASK_ENV', 'production')
app = create_app()

if __name__ == '__main__':
    serve(
        app,
        host='0.0.0.0',
        port=5000,
        threads=32,                              # V1.4 调优:I/O 友好
        max_request_body_size=536870912,         # 500MB 物理底线
        channel_timeout=120,
        cleanup_interval=30,
    )
```

### 4.2 注册服务

```powershell
nssm install DBU-Fixture-Backend "C:\Python312\python.exe" "C:\dbu\backend\serve.py"
nssm set DBU-Fixture-Backend AppDirectory "C:\dbu\backend"
nssm set DBU-Fixture-Backend AppEnvironmentExtra "FLASK_ENV=production"

# NSSM 仅做兜底输出捕获（主日志由 Flask TimedRotatingFileHandler 处理）
nssm set DBU-Fixture-Backend AppStdout "D:\dbu\logs\nssm_stdout.log"
nssm set DBU-Fixture-Backend AppStderr "D:\dbu\logs\nssm_stderr.log"
nssm set DBU-Fixture-Backend AppRotateFiles 1
nssm set DBU-Fixture-Backend AppRotateBytes 10485760    # 10MB 切割

# 启动延时（可选，等 MySQL 启动稳定）
nssm set DBU-Fixture-Backend AppStopMethodSkip 0
nssm set DBU-Fixture-Backend AppStopMethodConsole 1500
nssm set DBU-Fixture-Backend AppStopMethodWindow 1500
nssm set DBU-Fixture-Backend AppStopMethodThreads 1500

# 失败自动重启
nssm set DBU-Fixture-Backend AppExit Default Restart
nssm set DBU-Fixture-Backend AppRestartDelay 3000

# 启动
nssm start DBU-Fixture-Backend
nssm status DBU-Fixture-Backend       # 应输出 SERVICE_RUNNING
```

### 4.3 验证启动

```powershell
# 看日志
Get-Content D:\dbu\logs\app.log -Tail 30 -Wait

# 简单 ping
curl http://localhost:5000/api/health   # 假设有 /api/health 端点

# 浏览器访问
# http://<服务器内网IP>:5000/
```

---

## 五、备份任务计划

### 5.1 创建备份脚本

详见 [docs/06_restore_procedure.md](./06_restore_procedure.md) 第 2 节，将 `backup_mysql.bat` 与 `backup_uploads.bat` 放入 `D:\dbu\scripts\`。

### 5.2 注册任务计划

```powershell
# 用 schtasks 或图形化 taskschd.msc 任意一种
schtasks /create /tn "DBU-Backup-MySQL" `
  /tr "D:\dbu\scripts\backup_mysql.bat" `
  /sc DAILY /st 02:00 /ru SYSTEM /rl HIGHEST /f

schtasks /create /tn "DBU-Backup-Uploads" `
  /tr "D:\dbu\scripts\backup_uploads.bat" `
  /sc DAILY /st 02:30 /ru SYSTEM /rl HIGHEST /f

# 验证
schtasks /query /tn "DBU-Backup-MySQL" /v /fo LIST
schtasks /query /tn "DBU-Backup-Uploads" /v /fo LIST
```

### 5.3 立即测试一次

```powershell
schtasks /run /tn "DBU-Backup-MySQL"
# 等待几十秒后检查
dir D:\dbu\backup\mysql
type D:\dbu\backup\mysql\backup.log
```

---

## 六、防火墙设置

只允许内网访问 5000 端口：

```powershell
# 假设公司内网网段为 192.168.0.0/16
New-NetFirewallRule -DisplayName "DBU-Fixture-Backend" `
  -Direction Inbound `
  -Protocol TCP -LocalPort 5000 `
  -RemoteAddress 192.168.0.0/16 `
  -Action Allow
```

**禁止对公网开放 5000 端口。** 如需公网访问，必须通过 VPN 或反向代理网关，由 IT 统一管理。

---

## 七、首次冒烟测试

部署完成后，逐项验证：

- [ ] 浏览器访问 `http://<服务器IP>:5000/` 能看到登录页
- [ ] 用超管账号登录成功
- [ ] 查看用户列表能见 9 角色
- [ ] 查看治具模板库能见 40+ 模板
- [ ] 查看供应商库能见 11 项默认供应商
- [ ] 创建一个测试项目 → 创建批次 → 创建治具 → 编码自动生成
- [ ] 上传一份测试图纸（小于 1MB），下载后可正常打开
- [ ] 触发一次状态流转，状态历史表有记录
- [ ] 检查日志：`D:\dbu\logs\app.log` 有正常请求记录
- [ ] 检查日志：当天日期的 app.log 命名正确（`app.log` 当天 + `app.log.YYYY-MM-DD` 历史）
- [ ] 等到次日 02:00 后检查 `D:\dbu\backup\mysql\` 是否有当日备份文件

---

## 八、运维日常

### 8.1 重启服务

```powershell
nssm restart DBU-Fixture-Backend
```

### 8.2 查看实时日志

```powershell
Get-Content D:\dbu\logs\app.log -Tail 50 -Wait
```

### 8.3 清理过期日志

`TimedRotatingFileHandler` 已配置 30 天自动清理，无需手动操作。
但 NSSM 的 `nssm_stdout.log` / `nssm_stderr.log` 仅按 10MB 切割，需定期手动清理：

```powershell
# 清理 30 天前的 NSSM 日志
forfiles /p D:\dbu\logs /m nssm_*.log* /d -30 /c "cmd /c del @path"
```

### 8.4 升级部署

```powershell
nssm stop DBU-Fixture-Backend
cd C:\dbu\backend
git pull
.\venv\Scripts\activate
pip install -r requirements.txt
flask db upgrade
nssm start DBU-Fixture-Backend
```

前端升级：开发机 `pnpm build` → robocopy dist 到 `C:\dbu\frontend\dist`，**Flask 静态文件无需重启服务**（Vue SPA 路由前端处理）。

---

## 九、附：IT 协调清单

部署启动前需与公司 IT 沟通：

- [ ] 申请 Windows Server 资源 / VM
- [ ] 申请固定内网 IP
- [ ] 申请 5000 端口的内网防火墙开放
- [ ] 申请 SMTP 邮箱账号（用于告警发送）
- [ ] 申请 NAS 备份目录映射（可选，作为本地备份的副本）
- [ ] 加入域 / 配置域账号（如使用 LDAP 认证扩展）
- [ ] 杀软白名单（避免误杀 Python venv 与 NSSM）
- [ ] 系统更新策略（避免自动重启撞业务时段）
