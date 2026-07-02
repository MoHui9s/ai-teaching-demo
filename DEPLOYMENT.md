# Hermes Agent 远程部署手册

## 服务器信息

- **服务器**: hk
- **域名**: https://www.mrqiu.xyz/
- **SSH**: `ssh hk`
- **当前版本**: 1.2.0

## 部署架构

```
┌─────────────────────────────────────────────────────────┐
│                        NGINX                            │
│  https://www.mrqiu.xyz/                                 │
│  ├── / (静态文件)         → /www/wwwroot/www.mrqiu.xyz  │
│  ├── /v1/*               → 127.0.0.1:8000/v1/          │
│  ├── /api/*              → 127.0.0.1:8000/api/         │
│  └── /health             → 127.0.0.1:8000/health       │
└─────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────┐
│                    后端服务 (systemd)                     │
│                    lee-agent.service                    │
│  路径: /opt/lee_agent                                   │
│  端口: 8000                                             │
│  Python: /opt/lee_agent/venv                            │
└─────────────────────────────────────────────────────────┘
```

## 快速发布流程

### 1. 本地构建前端

```bash
cd /home/ben/gitee/lee/lee_agent_admin
npm run build
# 输出到 ../lee_agent/static/
```

> **注意**: vite.config.js 中 `outDir` 必须为 `'../lee_agent/static'`，不是 `'../static'`。

### 2. 上传静态文件到 NGINX

```bash
rsync -avz --delete --rsync-path="sudo rsync" \
  /home/ben/gitee/lee/lee_agent/static/ \
  hk:/www/wwwroot/www.mrqiu.xyz/
```

### 3. 上传后端代码

```bash
# 完整后端代码（排除运行时数据）
rsync -avz --rsync-path="sudo rsync" \
  --exclude __pycache__ --exclude "*.pyc" \
  --exclude ".git" --exclude "memories" \
  --exclude "data" --exclude "logs" --exclude ".env" \
  /home/ben/gitee/lee/lee_agent/ \
  hk:/opt/lee_agent/
```

### 4. 重启后端服务

```bash
ssh hk "sudo systemctl restart lee-agent"
```

### 5. 处理浏览器缓存

部署后用户浏览器可能缓存旧 JS/CSS。临时方案是 NGINX 已设置 `expires 0`。如果仍然加载旧版，访问时添加随机参数：`https://www.mrqiu.xyz/?v=2`

### 6. 验证部署

```bash
# 版本和健康检查
curl -s https://www.mrqiu.xyz/health

# 管理员状态
curl -s https://www.mrqiu.xyz/api/admin/status

# 用户列表
curl -s https://www.mrqiu.xyz/api/admin/users \
  -H "X-Admin-Token: lee_admin_2026"

# SPA 路由（应返回 200，非 404）
curl -s -o /dev/null -w "%{http_code}" https://www.mrqiu.xyz/admin/dashboard
```

## 清理服务器数据

发布新版本时如需清理所有用户数据：

```bash
ssh hk "sudo rm -rf /opt/lee_agent/data/* /opt/lee_agent/memories/*/ && sudo systemctl restart lee-agent"
```

## 配置文件

### 环境变量

**位置**: `/opt/lee_agent/.env`

```bash
ADMIN_TOKEN=lee_admin_2026
MODEL=deepseek-v4-flash
LOG_LEVEL=INFO
DEV_MODE=true
DEFAULT_USER_EMAIL=user@example.com
DEFAULT_USER_PASSWORD=password123
JWT_SECRET=hermes-secret-key-change-in-production
```

### 本地环境变量

**位置**: `lee_agent/.env`（不部署到服务器）

```bash
ADMIN_TOKEN=lee_admin_2026
MODEL=deepseek-v4-flash
LOG_LEVEL=INFO
DEV_MODE=true
DEFAULT_USER_EMAIL=user@example.com
DEFAULT_USER_PASSWORD=password123
JWT_SECRET=hermes-secret-key-change-in-production
```

### Systemd 服务

**位置**: `/etc/systemd/system/lee-agent.service`

```ini
[Unit]
Description=Lee Agent API Service
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/opt/lee_agent
Environment="PATH=/opt/lee_agent/venv/bin:/usr/local/bin:/usr/bin:/bin"
EnvironmentFile=/opt/lee_agent/.env
Environment="PYTHONUNBUFFERED=1"
ExecStart=/opt/lee_agent/venv/bin/python -m api.server
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### NGINX 配置

**主配置**: `/www/server/panel/vhost/nginx/html_www.mrqiu.xyz.conf`
**扩展目录**: `/www/server/panel/vhost/nginx/extension/www.mrqiu.xyz/`

#### API 反向代理 (`api_proxy.conf`)

```nginx
location /v1/ {
    proxy_pass http://127.0.0.1:8000/v1/;
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_cache_bypass $http_upgrade;
    proxy_read_timeout 300s;
    proxy_connect_timeout 75s;
    proxy_send_timeout 300s;
}

location /api/ {
    proxy_pass http://127.0.0.1:8000/api/;
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_cache_bypass $http_upgrade;
    proxy_read_timeout 300s;
    proxy_connect_timeout 75s;
    proxy_send_timeout 300s;
}

location /health {
    proxy_pass http://127.0.0.1:8000/health;
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    access_log off;
}
```

#### SPA 路由支持 (`spa.conf`)

**必须使用 `try_files`，不能用 `error_page 404`**：

```nginx
location / {
    try_files $uri $uri/ /index.html;
}
```

#### JS/CSS 缓存

主配置中 JS/CSS 缓存已设为 `expires 0`，避免部署后浏览器加载旧版本。

## 服务管理

### 后端

```bash
ssh hk "sudo systemctl status lee-agent"   # 状态
ssh hk "sudo systemctl restart lee-agent"  # 重启
ssh hk "sudo systemctl stop lee-agent"     # 停止
ssh hk "sudo systemctl start lee-agent"    # 启动
ssh hk "sudo journalctl -u lee-agent -f"   # 实时日志
ssh hk "sudo journalctl -u lee-agent -n 100"  # 最近100行
```

### NGINX

```bash
ssh hk "sudo /www/server/nginx/sbin/nginx -t"        # 测试配置
ssh hk "sudo /www/server/nginx/sbin/nginx -s reload" # 重载配置
ssh hk "sudo tail -50 /www/wwwlogs/www.mrqiu.xyz.error.log"  # 错误日志
```

## 数据存储

| 数据 | 位置 | 格式 | 说明 |
|------|------|------|------|
| 用户账户 | `data/users.db` | SQLite | 邮箱、密码哈希、激活状态 |
| TTS 缓存 | `data/tts_cache.leveldb` | LevelDB | 音频二进制缓存 |
| 对话历史 | `memories/{user_id}/history.json` | JSON | OpenAI 消息格式 |
| 智能体记忆 | `memories/{user_id}/MEMORY.md` | Markdown (§ 分隔) | 跨会话持久化 |
| 用户档案 | `memories/{user_id}/USER.md` | Markdown (§ 分隔) | 用户偏好和档案 |
| 审计日志 | `memories/{user_id}/audit.jsonl` | JSONL | 操作审计记录 |

## 依赖

### 服务器依赖

```bash
# Python 包 (在 venv 中)
pip install fastapi uvicorn httpx pydantic requests \
  python-multipart edge-tts python-dotenv \
  plyvel bcrypt pyjwt

# 系统依赖
sudo apt install -y python3 python3-pip python3-venv libleveldb-dev
```

### plyvel (LevelDB)

TTS 缓存使用 LevelDB。安装前需系统库：
```bash
sudo apt install -y libleveldb-dev
pip install plyvel
```

## 访问地址

| 页面 | URL | 说明 |
|------|-----|------|
| 主页 | https://www.mrqiu.xyz/ | 自动重定向到 /user |
| 用户登录 | https://www.mrqiu.xyz/user | 用户登录页面 |
| 用户聊天 | https://www.mrqiu.xyz/user/{user_id} | 用户聊天页面 |
| 管理员登录 | https://www.mrqiu.xyz/admin | 管理员登录页面 |
| 管理员仪表板 | https://www.mrqiu.xyz/admin/dashboard | 聊天 + 用户管理 (Tab 切换) |

## 管理员功能

| 功能 | API 端点 | 说明 |
|------|----------|------|
| 验证令牌 | `GET /api/admin/verify` | Header: X-Admin-Token |
| 创建用户 | `POST /api/admin/users` | email, password, (可选 user_id) |
| 用户列表 | `GET /api/admin/users` | 所有注册用户 |
| 用户详情 | `GET /api/admin/users/{id}` | 单个用户信息 |
| 编辑用户 | `PUT /api/admin/users/{id}` | 修改 email, is_active |
| 删除用户 | `DELETE /api/admin/users/{id}` | 删除用户账户 |
| 重置密码 | `POST /api/admin/users/{id}/password` | 自动生成或自定义 |

## 重要凭证

| 项目 | 值 | 说明 |
|------|-----|------|
| ADMIN_TOKEN | `lee_admin_2026` | 管理员访问令牌 |
| API 端口 | 8000 | 后端服务端口 |
| Python venv | `/opt/lee_agent/venv` | Python 虚拟环境 |

## 常见问题

### 部署后 UI 样式丢失 / 加载旧版

1. NGINX 缓存：确认 JS/CSS `expires` 设为 0
2. 浏览器缓存：访问 `https://www.mrqiu.xyz/?v={随机数}` 强制刷新
3. 检查服务器文件版本：
   ```bash
   ssh hk "ls -la /www/wwwroot/www.mrqiu.xyz/assets/"
   ssh hk "cat /www/wwwroot/www.mrqiu.xyz/index.html | grep script"
   ```

### SPA 路由返回 404

```bash
# 检查 spa.conf 内容
ssh hk "cat /www/server/panel/vhost/nginx/extension/www.mrqiu.xyz/spa.conf"
```
必须为 `try_files $uri $uri/ /index.html;`，**不能**用 `error_page 404`。

### 后端请求超时 / 卡死

```bash
# 检查是否有僵尸进程
ssh hk "sudo lsof -i :8000"
# 强制重启
ssh hk "sudo pkill -9 -f 'python.*api.server' && sudo systemctl restart lee-agent"
```

### API 返回错误

```bash
# 检查后端日志
ssh hk "sudo journalctl -u lee-agent -n 50"
# 检查磁盘
ssh hk "df -h /opt"
```

### 构建输出路径错误

确认 `lee_agent_admin/vite.config.js` 中：
```js
build: {
    outDir: '../lee_agent/static',  // 注意：不是 '../static'
    emptyOutDir: true,
}
```

## 首次部署指南

1. **安装系统依赖**
   ```bash
   ssh hk
   sudo apt update
   sudo apt install -y python3 python3-pip python3-venv libleveldb-dev
   ```

2. **创建目录和用户**
   ```bash
   sudo mkdir -p /opt/lee_agent /www/wwwroot/www.mrqiu.xyz
   sudo chown -R ubuntu:ubuntu /opt/lee_agent
   ```

3. **创建 Python 虚拟环境**
   ```bash
   cd /opt/lee_agent
   python3 -m venv venv
   source venv/bin/activate
   pip install fastapi uvicorn httpx pydantic requests \
     python-multipart edge-tts python-dotenv \
     plyvel bcrypt pyjwt
   ```

4. **上传代码** — 按照"快速发布流程"

5. **配置环境变量** — 创建 `/opt/lee_agent/.env`

6. **创建 systemd 服务** — 参考"配置文件"部分

7. **配置 NGINX** — 创建 `spa.conf`、`api_proxy.conf`

8. **启动服务**
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable lee-agent
   sudo systemctl start lee-agent
   sudo /www/server/nginx/sbin/nginx -s reload
   ```

## 版本发布检查清单

- [ ] 本地构建成功 (`npm run build`)
- [ ] 前端输出路径正确 (`lee_agent/static/` 含 AdminDashboard JS)
- [ ] 静态文件上传到 `/www/wwwroot/www.mrqiu.xyz/`
- [ ] 后端代码上传到 `/opt/lee_agent/`
- [ ] `.env` 环境变量配置正确
- [ ] `sudo systemctl restart lee-agent` 成功
- [ ] `curl https://www.mrqiu.xyz/health` 返回版本号
- [ ] SPA 路由 `/admin/dashboard` 返回 200 非 404
- [ ] 管理员登录正常
- [ ] 用户创建 / 登录 / 聊天正常
- [ ] 浏览器缓存已清除 (添加 `?v=` 参数测试)
