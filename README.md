# Telegram 接码平台 (Docker 版)

> 🚀 自动接收 Telegram 验证码，支持多账号管理，一键部署，5分钟上线！

## 📖 项目简介

这是一个基于 Docker 的自动化 Telegram 验证码接收平台。它能自动监听多个 Telegram 账号的验证码消息，提供 Web 界面查看和 API 接口调用，非常适合需要批量接收 Telegram 验证码的场景。

### 核心功能

- 📱 **多账号管理** - 支持添加无限个 Telegram 账号
- 🔄 **自动接码** - 后台定时检查新验证码（智能去重）
- 🌐 **Web 界面** - 响应式设计，完美适配手机与电脑
- 🌏 **便捷交互** - 内置国家代码选择，操作状态实时反馈
- 🔌 **REST API** - 方便集成到其他系统
- 💾 **数据持久化** - PostgreSQL 存储，数据不丢失
- 🐳 **Docker 容器化** - 一键部署，环境隔离
- 🔁 **快速迁移** - 换服务器只需 5 分钟

### 技术栈

- **后端**: FastAPI + Telethon + SQLAlchemy + APScheduler
- **数据库**: PostgreSQL 14
- **前端**: 原生 HTML/CSS/JavaScript（轻量级）
- **反向代理**: Nginx
- **容器化**: Docker + Docker Compose

## 📁 项目结构

```
telegram-receiver-docker/
├── docker-compose.yml          # Docker 编排配置
├── .env.example                # 环境变量模板
├── .gitignore                  # Git 忽略规则
├── README.md                   # 项目文档（本文件）
├── deploy.sh                   # 一键部署脚本
├── backup.sh                   # 备份脚本
│
├── backend/                    # 后端服务
│   ├── Dockerfile              # 后端镜像
│   ├── requirements.txt        # Python 依赖
│   ├── main.py                 # FastAPI 主程序
│   ├── config.py               # 配置管理
│   ├── database.py             # 数据库模型
│   ├── receiver.py             # Telegram 接收器
│   ├── scheduler.py            # 定时任务调度
│   └── init_db.py              # 数据库初始化
│
├── nginx/                      # Nginx 反向代理
│   ├── Dockerfile              # Nginx 镜像
│   └── nginx.conf              # Nginx 配置
│
├── frontend/                   # 前端静态文件
│   └── dist/
│       └── index.html          # Web 界面
│
└── sessions/                   # Telegram Session 文件（需手动创建）
    └── .gitkeep
```

## 🚀 快速开始

### 前置准备

#### 1. 服务器要求

- **操作系统**: Ubuntu 22.04 LTS (推荐) / CentOS 7+ / Debian 10+
- **配置**: 最低 2 vCPU, 1GB RAM, 10GB 存储
- **网络**: 能直接访问 Telegram API（香港/日本服务器最佳，无需代理）
- **端口**: 开放 80 端口（或其他自定义端口）

#### 2. 准备工作

无需本地准备 Session 文件！系统已支持 Web 界面直接登录。

### 部署步骤

#### 方法1：一键自动部署（推荐）

```bash
# 1. 上传项目到服务器
# 在本地 PowerShell 执行：
scp -r telegram-receiver-docker root@your-server-ip:/root/

# 2. SSH 登录到服务器
ssh root@your-server-ip

# 3. 进入项目目录
cd /root/telegram-receiver-docker

# 4. 给脚本执行权限
chmod +x deploy.sh backup.sh

# 5. 运行一键部署
./deploy.sh
```

部署脚本会自动完成：
- ✅ 检测操作系统类型
- ✅ 安装 Docker 和 Docker Compose
- ✅ 配置防火墙规则
- ✅ 生成 .env 配置文件（随机密码）
- ✅ 构建 Docker 镜像
- ✅ 启动所有服务容器
- ✅ 初始化数据库

#### 方法2：手动部署

如果自动部署失败，可以手动执行：

```bash
# 1. 安装 Docker
curl -fsSL https://get.docker.com | sh
systemctl start docker
systemctl enable docker

# 2. 安装 Docker Compose
curl -L "https://github.com/docker/compose/releases/download/v2.24.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose

# 3. 配置环境变量
cp .env.example .env
nano .env  # 编辑配置

# 4. 创建必要的目录
mkdir -p sessions logs

# 5. 启动服务
docker-compose up -d

# 6. 查看日志
docker-compose logs -f backend
```

### 访问服务

部署完成后，通过浏览器访问：

```
http://your-server-ip
```

你会看到：
- 📊 账号列表
- 🔢 最新验证码（仅显示最新一条，完整展示消息内容）

## 🔧 手动部署

如果你想自己控制每一步：

### 1. 安装 Docker

```bash
# 安装 Docker
curl -fsSL https://get.docker.com | sh

# 启动 Docker
sudo systemctl start docker
sudo systemctl enable docker

# 安装 Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

### 2. 配置环境变量

```bash
# 复制配置模板
cp .env.example .env

# 编辑配置（必须修改以下两项）
nano .env
```

**必须修改**:
- `DB_PASSWORD` - 数据库密码（改成强密码）
- `SECRET_KEY` - 应用密钥（运行 `openssl rand -hex 32` 生成）

### 3. 构建前端

```bash
cd frontend
npm install
npm run build
cd ..
```

### 4. 启动服务

```bash
# 启动所有容器
docker-compose up -d

# 查看状态
docker-compose ps

# 查看日志
docker-compose logs -f
```

### 5. 初始化数据库

```bash
# 进入后端容器
docker-compose exec backend python init_db.py
```

## 📱 添加 Telegram 账号

### 方法: Web 界面直接登录（推荐）

系统内置了完整的 Telegram 登录流程，无需手动操作 Session 文件。

1. 访问部署好的网站 `http://your-server-ip`
2. 点击 **"+ 添加账号"** 按钮
3. 选择国家/地区（默认 +86），输入手机号，点击"发送验证码"
   - 按钮会变灰并提示"正在发送..."，请耐心等待
4. 在手机 Telegram App 上查看验证码
5. 输入验证码（如果开启了两步验证，还需输入密码）
6. 点击"确认登录"（按钮会提示"正在登录..."）

系统会自动：
- ✅ 验证登录信息
- ✅ 生成并保存 Session 文件
- ✅ 在数据库中创建账号记录
- ✅ 立即开始监听验证码

### 管理账号

在 Web 界面首页，你可以：
- 查看所有已登录账号的状态
- 删除不再需要的账号（会自动清理 Session 文件）
- 实时查看接收到的验证码

### Session 文件说明

- **存放位置**: `sessions/` 目录
- **文件格式**: SQLite 数据库文件（由 Telethon 生成）
- **自动管理**: 系统会自动创建和删除，无需人工干预
- **文件格式**: SQLite 数据库文件（由 Telethon 生成）

### 查看已添加的账号

```bash
# 方法1：Web 界面查看
http://your-server-ip

# 方法2：数据库查询
docker-compose exec postgres psql -U telegram_user -d telegram_codes -c "SELECT * FROM accounts;"

# 方法3：查看 sessions 目录
ls -lh sessions/
```

## � API 文档

系统提供 RESTful API，可以方便集成到其他系统。

### 健康检查

```bash
GET /api/health
```

**响应示例**:
```json
{
  "status": "ok",
  "timestamp": "2025-12-26T10:30:00.000Z"
}
```

### 获取所有账号

```bash
GET /api/accounts
```

**响应示例**:
```json
[
  {
    "id": 1,
    "phone": "+8613800138000",
    "is_active": true,
    "created_at": "2025-12-26T08:00:00.000Z"
  }
]
```

### 获取验证码列表

```bash
GET /api/codes?hours=24&limit=100
```

**参数**:
- `hours`: 查询最近多少小时的验证码（默认 24）
- `limit`: 返回记录数量（默认 100）

**响应示例**:
```json
[
  {
    "id": 123,
    "phone": "+8613800138000",
    "code": "12345",
    "message": "Your verification code is 12345",
    "service": null,
    "received_at": "2025-12-26T10:25:30.000Z"
  }
]
```

### 获取指定手机号最新验证码

```bash
GET /api/codes/latest/{phone}
```

**示例**:
```bash
curl http://your-server-ip/api/codes/latest/+8613800138000
```

**响应示例**:
```json
{
  "code": "12345",
  "message": "Your verification code is 12345",
  "received_at": "2025-12-26T10:25:30.000Z"
}添加账号 - 发送验证码

```bash
POST /api/accounts/send-code
```

**请求体**:
```json
{
  "phone": "+8613800138000"
}
```

### 添加账号 - 验证登录

```bash
POST /api/accounts/verify
```

**请求体**:
```json
{
  "phone": "+8613800138000",
  "code": "12345",
  "password": "optional-2fa-password"
}
```

### 删除账号

```bash
DELETE /api/accounts/{id}
```

### 
```

### 使用示例

```python
# Python 示例
import requests

# 获取最新验证码
response = requests.get('http://your-server-ip/api/codes/latest/+8613800138000')
data = response.json()
print(f"验证码: {data['code']}")

# 获取最近 1 小时的所有验证码
response = requests.get('http://your-server-ip/api/codes?hours=1&limit=50')
codes = response.json()
for item in codes:
    print(f"{item['phone']}: {item['code']}")
```

```bash
# Curl 示例
# 获取最新验证码
curl -s http://your-server-ip/api/codes/latest/+8613800138000 | jq '.code'

# 获取所有账号
curl -s http://your-server-ip/api/accounts | jq '.'
```

## �🔐 SSL 证书配置

### 使用 Let's Encrypt（免费）

```bash
# 1. 确保域名已解析到服务器

# 2. 停止 Nginx（避免端口冲突）
docker-compose stop nginx

# 3. 安装 Certbot
sudo apt install certbot

# 4. 获取证书
sudo certbot certonly --standalone -d your-domain.com -d www.your-domain.com

# 5. 复制证书到项目
sudo cp /etc/letsencrypt/live/your-domain.com/fullchain.pem nginx/ssl/
sudo cp /etc/letsencrypt/live/your-domain.com/privkey.pem nginx/ssl/

# 6. 修改 Nginx 配置（取消 SSL 部分的注释）
nano nginx/nginx.conf

# 7. 重启 Nginx
docker-compose start nginx
```

## ⚙️ 配置说明

### 环境变量 (.env)

```bash
# 数据库配置
DATABASE_URL=postgresql://telegram_user:your-password@postgres:5432/telegram_codes
DB_PASSWORD=your-strong-password

# Telegram API 配置（使用公共测试凭据）
API_ID=2040
API_HASH=b18441a1ff607e10a989891a5462e627

# 应用密钥（用于加密，必须修改！）
SECRET_KEY=your-secret-key-here

# 定时任务间隔（秒）- 检查新验证码的频率
SCHEDULER_INTERVAL=300

# 时区设置
TZ=Asia/Shanghai
```

### 自定义配置

**修改检查频率**：

编辑 `.env`，将 `SCHEDULER_INTERVAL` 改为你想要的秒数：
- `60` = 1分钟检查一次
- `300` = 5分钟检查一次（默认）
- `600` = 10分钟检查一次

```bash
# 修改后重启服务
docker-compose restart backend
```

**修改端口**：

编辑 `docker-compose.yml` 中 nginx 服务的 ports：
```yaml
nginx:
  ports:
    - "8080:80"  # 改为 8080 端口
```

**限制内存使用**：

已经针对 1GB 服务器优化，如果想进一步限制：
```yaml
backend:
  deploy:
    resources:
      limits:
        memory: 256M  # 改小内存限制
```

## 🔄 常用命令

```bash
# 查看所有容器状态
docker-compose ps

# 查看实时日志
docker-compose logs -f

# 查看特定服务日志
docker-compose logs -f backend

# 重启所有服务
docker-compose restart

# 重启单个服务
docker-compose restart backend

# 停止所有服务
docker-compose stop

# 启动所有服务
docker-compose start

# 完全停止并删除容器（数据保留）
docker-compose down

# 停止并删除所有数据（危险！）
docker-compose down -v

# 进入容器内部
docker-compose exec backend bash
docker-compose exec postgres psql -U telegram_user -d telegram_codes

# 查看资源使用
docker stats
```

## 💾 备份与恢复

### 备份

```bash
# 运行备份脚本
./backup.sh

# 备份文件位置
# backups/telegram-backup-YYYYMMDD-HHMMSS.tar.gz
```

备份包含：
- 📊 数据库数据
- 🔑 Session 文件
- ⚙️ 配置文件

### 恢复

```bash
# 解压备份文件
tar -xzf backups/telegram-backup-20231226-120000.tar.gz

# 恢复数据库
cat backup/database.sql | docker-compose exec -T postgres psql -U telegram_user -d telegram_codes

# 恢复 session 文件
cp -r backup/sessions/* ./sessions/

# 重启服务
docker-compose restart
```

## 🚚 服务器迁移

只需 5 分钟！

### 旧服务器操作

```bash
# 1. 备份所有数据
./backup.sh

# 2. 传输到新服务器
scp backups/telegram-backup-*.tar.gz root@new-server-ip:~/
```

### 新服务器操作

```bash
# 1. 安装 Docker
curl -fsSL https://get.docker.com | sh

# 2. 解压项目
tar -xzf telegram-backup-*.tar.gz
cd telegram-receiver-docker

# 3. 启动服务
docker-compose up -d

# 完成！访问 http://new-server-ip
```

## 📊 监控

### 查看资源使用

```bash
# 实时资源监控
docker stats

# 容器状态
docker-compose ps

# 磁盘使用
docker system df
```

### 健康检查

```bash
# 检查 API 是否正常
curl http://localhost:8000/api/health

# 检查数据库连接
docker-compose exec postgres pg_isready
```

## 🐛 故障排查

### 容器无法启动

```bash
# 查看详细日志
docker-compose logs backend

# 检查配置文件
docker-compose config

# 重新构建镜像
docker-compose build --no-cache
docker-compose up -d
```

### 数据库连接失败

```bash
# 检查数据库状态
docker-compose ps postgres

# 查看数据库日志
docker-compose logs postgres

# 测试连接
docker-compose exec postgres psql -U telegram_user -d telegram_codes
```

### 内存不足

```bash
# 查看内存使用
free -h
docker stats

# 添加 swap（如果需要）
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

### 清理空间

```bash
# 清理未使用的镜像
docker image prune -a

# 清理未使用的容器
docker container prune

# 清理未使用的卷
docker volume prune

# 清理所有未使用资源
docker system prune -a --volumes
```

### 清理空间

```bash
# 清理未使用的镜像
docker image prune -a

# 清理未使用的容器
docker container prune

# 清理未使用的卷
docker volume prune

# 清理所有未使用资源
docker system prune -a --volumes

# 清理日志文件
truncate -s 0 logs/*.log
```

### Session 文件问题

**问题**: 账号提示未授权

```bash
# 检查 session 文件权限
ls -lh sessions/

# 重新登录账号
docker-compose exec backend bash
python3
>>> from telethon import TelegramClient
>>> client = TelegramClient('sessions/account1', 2040, 'b18441a1ff607e10a989891a5462e627')
>>> await client.connect()
>>> await client.send_code_request('+8613800138000')
>>> code = input("验证码: ")
>>> await client.sign_in('+8613800138000', code)
```

**问题**: 找不到 session 文件

```bash
# 确保 sessions 目录挂载正确
docker-compose down
mkdir -p sessions
# 重新上传 session 文件
docker-compose up -d
```

### 验证码提取问题

**问题**: 无法提取验证码

检查正则表达式匹配：
```bash
# 查看原始消息
docker-compose logs backend | grep "message"

# 当前正则: \b(\d{5,6})\b
# 匹配 5-6 位连续数字
```

如需修改正则，编辑 [backend/receiver.py](backend/receiver.py)：
```python
# 第 31 行左右
code_match = re.search(r'\b(\d{5,6})\b', message.message)
```

### 网络连接问题

**问题**: 无法连接 Telegram

```bash
# 检查服务器网络
ping telegram.org

# 如果需要代理（一般香港/日本服务器不需要）
# 编辑 backend/config.py 添加代理配置
```

**问题**: Docker 网络问题

```bash
# 重建网络
docker-compose down
docker network prune
docker-compose up -d
```

## 🔒 安全建议

1. **修改默认密码** - `.env` 中的 `DB_PASSWORD` 和 `SECRET_KEY`
2. **启用 SSL** - 使用 Let's Encrypt 配置 HTTPS
3. **限制 SSH 访问** - 禁用密码登录，只用密钥
4. **配置防火墙** - 只开放必要端口（22, 80, 443）
5. **定期备份** - 设置 cron 任务自动备份
6. **更新镜像** - 定期更新 Docker 镜像

```bash
# 设置自动备份（每天凌晨 2 点）
crontab -e
# 添加: 0 2 * * * /path/to/backup.sh
```

## 📈 性能优化

### 针对 1GB RAM 优化

已在 `docker-compose.yml` 中配置：
- PostgreSQL: 64MB shared_buffers
- Backend: 400MB 内存限制
- 最大 20 个数据库连接

### 监控资源使用

```bash
# 实时监控
docker stats

# 查看日志大小
du -sh logs/

# 限制日志大小
# 在 docker-compose.yml 中添加：
# logging:
#   driver: "json-file"
#   options:
#     max-size: "10m"
#     max-file: "3"
```

## � 性能优化

### 针对 1GB RAM 优化

已在 `docker-compose.yml` 中配置：
- PostgreSQL: 64MB shared_buffers
- Backend: 400MB 内存限制
- 最大 20 个数据库连接

### 监控资源使用

```bash
# 实时监控
docker stats

# 查看日志大小
du -sh logs/

# 限制日志大小
# 在 docker-compose.yml 中添加：
# logging:
#   driver: "json-file"
#   options:
#     max-size: "10m"
#     max-file: "3"
```

### 优化检查频率

根据实际需求调整 `SCHEDULER_INTERVAL`：
- 高频场景（如自动化测试）：60-120秒
- 普通场景（人工使用）：300-600秒
- 低频场景（备用系统）：900-1800秒

```bash
# 修改 .env
SCHEDULER_INTERVAL=300

# 重启生效
docker-compose restart backend
```

### 数据库优化

如果验证码记录过多，定期清理旧数据：

```sql
-- 删除 30 天前的验证码
DELETE FROM verification_codes 
WHERE received_at < NOW() - INTERVAL '30 days';

-- 清理无用账号
DELETE FROM accounts WHERE is_active = false AND created_at < NOW() - INTERVAL '90 days';
```

设置自动清理任务：

```bash
# 在服务器上添加定时任务
crontab -e

# 每周日凌晨 3 点清理
0 3 * * 0 docker-compose exec -T postgres psql -U telegram_user -d telegram_codes -c "DELETE FROM verification_codes WHERE received_at < NOW() - INTERVAL '30 days';"
```

## 🔍 监控与日志

### 日志查看

```bash
# 查看所有服务日志
docker-compose logs

# 实时跟踪日志
docker-compose logs -f

# 查看特定服务日志
docker-compose logs backend
docker-compose logs postgres
docker-compose logs nginx

# 查看最近 100 行
docker-compose logs --tail=100 backend

# 按时间过滤
docker-compose logs --since 2025-12-26T10:00:00
```

### 日志文件位置

- Backend 日志: `logs/backend.log`
- Nginx 访问日志: Nginx 容器内 `/var/log/nginx/access.log`
- Nginx 错误日志: Nginx 容器内 `/var/log/nginx/error.log`
- PostgreSQL 日志: Docker logs

### 监控告警

建议使用以下工具监控服务：

1. **Uptime Kuma** - 自托管监控
2. **UptimeRobot** - 免费外部监控
3. **Prometheus + Grafana** - 专业监控方案

简单的健康检查脚本：

```bash
#!/bin/bash
# health-check.sh

URL="http://localhost/api/health"
RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" $URL)

if [ $RESPONSE -ne 200 ]; then
    echo "服务异常！HTTP 状态码: $RESPONSE"
    # 发送告警（邮件/Telegram 等）
    docker-compose restart backend
fi
```

添加到 crontab 每 5 分钟检查一次：

```bash
crontab -e
# 添加：
*/5 * * * * /root/telegram-receiver-docker/health-check.sh
```

## 📚 项目结构详解

## 📚 项目结构详解

```
telegram-receiver-docker/
├── docker-compose.yml          # Docker 编排配置文件
│                               # 定义了 3 个服务: postgres, backend, nginx
│
├── .env                        # 环境变量配置（需自己创建）
├── .env.example                # 环境变量模板（复制此文件）
├── .gitignore                  # Git 忽略文件（排除 session、密码等）
│
├── README.md                   # 项目文档（本文件）
├── deploy.sh                   # 一键部署脚本（自动安装 Docker、配置环境）
├── backup.sh                   # 自动备份脚本（数据库+sessions）
│
├── backend/                    # 后端 Python 服务
│   ├── Dockerfile              # 后端镜像构建文件
│   ├── requirements.txt        # Python 依赖包列表
│   ├── config.py               # 配置管理（从 .env 读取）
│   ├── main.py                 # FastAPI 主程序（定义 API 路由）
│   ├── database.py             # 数据库连接和模型定义
│   ├── receiver.py             # Telegram 接码核心逻辑
│   ├── scheduler.py            # 后台定时任务调度器
│   └── init_db.py              # 数据库初始化脚本
│
├── nginx/                      # Nginx 反向代理
│   ├── Dockerfile              # Nginx 镜像构建文件
│   └── nginx.conf              # Nginx 配置（路由规则、代理设置）
│
├── frontend/                   # 前端静态文件
│   └── dist/
│       └── index.html          # Web 界面（单页面应用）
│
├── sessions/                   # Telegram Session 文件目录
│   ├── account1.session        # 账号 1 的会话文件
│   └── account2.session        # 账号 2 的会话文件
│
├── logs/                       # 运行日志目录
│   └── backend.log             # 后端日志
│
└── backups/                    # 备份文件目录（运行 backup.sh 后生成）
    └── telegram-backup-*.tar.gz
```

### 核心文件说明

#### backend/main.py
FastAPI 主程序，提供 RESTful API：
- `GET /api/health` - 健康检查
- `GET /api/accounts` - 获取账号列表
- `GET /api/codes` - 获取验证码列表
- `GET /api/codes/latest/{phone}` - 获取最新验证码

#### backend/receiver.py
Telegram 接码核心：
- `check_codes_for_account()` - 检查单个账号的新验证码
- `check_all_accounts()` - 遍历所有账号检查
- 正则提取验证码：`\b(\d{5,6})\b`
- 自动过滤重复验证码

#### backend/scheduler.py
后台定时任务：
- 使用 APScheduler 定时调度
- 默认每 300 秒检查一次
- 可通过 `.env` 中 `SCHEDULER_INTERVAL` 配置

#### docker-compose.yml
服务编排：
- **postgres**: PostgreSQL 14，1GB RAM 优化配置
- **backend**: Python FastAPI，挂载 sessions 和 logs
- **nginx**: 反向代理，提供 Web 访问

## 🚀 高级用法

### 多账号批量部署

```bash
# 1. 本地批量生成 session 文件
for i in {1..5}; do
    python setup_simple.py  # 输入不同手机号
    mv telegram_session.session sessions/account$i.session
done

# 2. 上传所有 session
scp -r sessions/ root@server:/root/telegram-receiver-docker/

# 3. 批量插入数据库
docker-compose exec postgres psql -U telegram_user -d telegram_codes <<EOF
INSERT INTO accounts (phone, session_name, is_active) VALUES
  ('+8613800138001', 'account1', true),
  ('+8613800138002', 'account2', true),
  ('+8613800138003', 'account3', true),
  ('+8613800138004', 'account4', true),
  ('+8613800138005', 'account5', true);
EOF
```

### 使用外部数据库

如果想使用云数据库（如阿里云 RDS）：

1. 修改 `.env`：
```bash
DATABASE_URL=postgresql://user:pass@your-rds-host:5432/dbname
```

2. 注释掉 `docker-compose.yml` 中的 postgres 服务

3. 重启：
```bash
docker-compose up -d
```

### API 鉴权

当前版本没有鉴权，如需添加：

编辑 [backend/main.py](backend/main.py)：

```python
from fastapi import Depends, HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer()

def verify_token(credentials: HTTPAuthorizationCredentials = Security(security)):
    if credentials.credentials != "your-secret-token":
        raise HTTPException(status_code=401, detail="Invalid token")
    return credentials.credentials

@app.get("/api/codes", dependencies=[Depends(verify_token)])
async def get_codes():
    # ...
```

使用时带上 token：
```bash
curl -H "Authorization: Bearer your-secret-token" http://server/api/codes
```

### Webhook 通知

收到新验证码时自动通知其他系统：

编辑 [backend/receiver.py](backend/receiver.py)，在保存验证码后添加：

```python
import requests

# 在 new_code = VerificationCode(...) 之后
db.add(new_code)
db.commit()

# 发送 webhook
try:
    requests.post('https://your-webhook-url.com/notify', json={
        'phone': phone,
        'code': code,
        'message': message.message,
        'received_at': message.date.isoformat()
    }, timeout=5)
except Exception as e:
    print(f"Webhook 发送失败: {e}")
```

## 💡 常见问题 (FAQ)

### Q1: 为什么选择 Docker 部署？

**A**: Docker 提供：
- ✅ 环境一致性（开发和生产环境相同）
- ✅ 快速部署（5分钟启动）
- ✅ 轻松迁移（打包即走）
- ✅ 资源隔离（不污染系统）
- ✅ 版本管理（镜像版本控制）

### Q2: 1GB 内存够用吗？

**A**: 完全够用！实际使用：
- PostgreSQL: ~80MB
- Backend: ~150MB
- Nginx: ~10MB
- 系统: ~200MB
- **总计**: ~440MB，还剩 560MB 缓冲

### Q3: 支持哪些国家的号码？

**A**: 所有 Telegram 支持的国家都可以。Web 界面已内置全球常用国家代码选择（如中国、美国、香港等），也支持手动输入其他国家代码。

### Q4: 会被封号吗？

**A**: 使用官方 API，正常使用不会封号。注意：
- ✅ 使用公共 API_ID（2040）
- ✅ 遵守 Telegram 速率限制
- ⚠️ 不要频繁登录/登出
- ⚠️ 建议检查间隔 ≥ 300 秒

### Q5: 如何扩展到更多账号？

**A**: 理论上无限，实际建议：
- 1GB RAM: 最多 10-15 个账号
- 2GB RAM: 最多 30-50 个账号
- 每个账号占用约 5-10MB 内存

### Q6: 可以接收非验证码消息吗？

**A**: 可以！修改 [backend/receiver.py](backend/receiver.py) 的过滤条件，不仅限于 777000（Telegram 官方）。

### Q7: 支持其他数据库吗？

**A**: 支持所有 SQLAlchemy 兼容的数据库：
- PostgreSQL（推荐）
- MySQL
- SQLite
- MariaDB

修改 `.env` 中的 `DATABASE_URL` 即可。

### Q8: 如何设置开机自启？

**A**: Docker Compose 默认已设置 `restart: unless-stopped`，会自动启动。

### Q9: 日志文件会占满磁盘吗？

**A**: 建议配置日志轮转，在 `docker-compose.yml` 中添加：

```yaml
logging:
  driver: "json-file"
  options:
    max-size: "10m"
    max-file: "3"
```

### Q10: 能在 Windows/Mac 本地运行吗？

**A**: 可以！安装 Docker Desktop 后：
```powershell
cd telegram-receiver-docker
docker-compose up -d
```
访问 http://localhost

### Q11: 为什么只显示一条验证码？

**A**: 为了在手机端保持界面简洁，默认只显示最新的一条验证码。后端 API 依然保留了所有历史记录，可以通过 API 参数 `limit` 获取更多。

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📄 许可证

MIT License

## 💬 联系支持

- 🐛 问题反馈: GitHub Issues
- 📖 完整文档: 本 README

---

⭐ 如果这个项目帮到了你，请给个 Star！

Made with ❤️ for Telegram automation
