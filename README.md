# Hermes Agent

极简 AI 代理框架，支持多用户、持久化记忆、可自定义人格和 OpenAI API 兼容服务。

## 特性

- **极简架构**：核心实现简洁，易于理解和修改
- **多用户支持**：每个用户独立的长短期记忆，数据完全隔离
- **OpenAI API 兼容**：提供 HTTP API 接口，支持流式输出
- **可自定义人格**：通过 SOUL.md 文件定义代理的风格和行为
- **持久化记忆**：基于文件的长短期记忆存储
- **对话历史持久化**：短期对话自动保存，重启后可恢复
- **安全扫描**：防止提示注入、数据外泄、SSH 后门

## 安装

使用 [uv](https://github.com/astral-sh/uv) 管理依赖：

```bash
uv sync
```

## 使用

### 命令行模式

**交互模式**：
```bash
uv run python agent.py
```

**单次执行**：
```bash
uv run python agent.py "your task here"
```

### API 服务模式

**启动服务**：
```bash
uv run uvicorn api.server:app --host 0.0.0.0 --port 8000
```

**或使用 Python**：
```bash
uv run python -m api.server
```

**API 示例**：
```bash
# 发送聊天请求
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "hermes",
    "messages": [{"role": "user", "content": "你好"}],
    "user_id": "user1"
  }'

# 清除用户对话历史
curl -X DELETE http://localhost:8000/v1/users/user1/history

# 获取用户对话历史
curl http://localhost:8000/v1/users/user1/history

# 列出所有用户
curl http://localhost:8000/v1/users
```

## 配置

复制 `.env.example` 到 `.env` 并配置：

```bash
cp .env.example .env
```

```env
# API 配置
OPENAI_API_KEY=your_api_key_here
OPENAI_BASE_URL=https://api.openai.com/v1
MODEL=gpt-4o

# API 服务
API_HOST=0.0.0.0
API_PORT=8000

# 用户设置
DEFAULT_USER_ID=default
MAX_HISTORY_ROUNDS=40

# 调试模式
DEBUG=false
```

## 记忆系统

### 数据结构

```
memories/
├── default/           # 默认用户
│   ├── MEMORY.md      # 长期记忆（代理笔记）
│   ├── USER.md        # 用户配置
│   └── history.json   # 短期对话历史
├── user1/            # 用户 1
│   ├── MEMORY.md
│   ├── USER.md
│   └── history.json
└── user2/            # 用户 2
    ├── MEMORY.md
    ├── USER.md
    └── history.json
```

### 长期记忆（MEMORY.md / USER.md）

- `MEMORY.md`：代理的个人笔记（环境事实、项目约定、工具特性）
- `USER.md`：用户配置（偏好、沟通风格、期望）

记忆工具支持三种操作：
- `add`：添加新条目
- `replace`：替换现有条目
- `remove`：删除条目

### 短期记忆（history.json）

- 存储完整对话历史（OpenAI messages 格式）
- 每次对话后自动保存
- 重启后自动恢复
- 支持通过 API 清除

## API 端点

| 端点 | 方法 | 功能 |
|------|------|------|
| `/v1/chat/completions` | POST | OpenAI 兼容的聊天接口 |
| `/v1/users/{user_id}/history` | GET | 获取用户对话历史 |
| `/v1/users/{user_id}/history` | DELETE | 清除用户对话历史 |
| `/v1/users` | GET | 列出所有用户 |
| `/health` | GET | 健康检查 |

## SOUL.md（代理人格）

SOUL.md 文件用于定义代理的身份、风格和行为方式（全局，所有用户共享）。

**用途**：
- 定义代理的语气和沟通风格
- 指定代理应该避免什么
- 设置代理的默认行为方式

**不属于这里**：
- 用户特定的记忆（使用 MEMORY.md）
- 文件路径、命令、端口等（使用 memory 工具保存）

## 项目结构

```
.
├── agent.py          # 核心代理实现（HermesAgent 类）
├── memory.py         # 记忆模块（MemoryStore 类）
├── api/              # API 服务模块
│   ├── server.py     # FastAPI 服务器
│   ├── schemas.py    # Pydantic 数据模型
│   └── stream.py     # SSE 流式处理
├── session/          # 会话管理（预留）
├── SOUL.md           # 代理人格定义（全局）
├── pyproject.toml    # 项目配置
├── .env              # 环境变量
├── .env.example      # 环境变量示例
└── memories/         # 用户数据目录
    ├── default/      # 默认用户数据
    │   ├── MEMORY.md
    │   ├── USER.md
    │   └── history.json
    └── {user_id}/    # 其他用户数据
```

## 技术栈

- Python 3.11+
- FastAPI - Web 框架
- requests - HTTP 客户端
- python-dotenv - 环境变量管理
- Pydantic - 数据验证

## 数据迁移

从旧版本升级时，单用户记忆会自动迁移：

```
旧版: memories/MEMORY.md
新版: memories/default/MEMORY.md
```

## 故障排除

### 调试模式

```env
DEBUG=true
```

会输出详细日志：API 请求、响应结构、工具调用、错误跟踪。

### 常见问题

**API 服务无法启动**：
1. 检查端口是否被占用
2. 确认依赖已安装：`uv sync`

**用户记忆混淆**：
1. 每个用户使用不同的 `user_id`
2. 检查 `memories/{user_id}/` 目录

**对话历史丢失**：
1. 确认 `user_id` 正确
2. 检查 `memories/{user_id}/history.json` 是否存在
