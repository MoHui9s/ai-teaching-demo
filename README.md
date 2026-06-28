# Hermes Agent

极简 AI 代理框架，支持跨会话持久化记忆和可自定义人格。

## 特性

- **极简架构**：单文件核心实现，易于理解和修改
- **可自定义人格**：通过 SOUL.md 文件定义代理的风格和行为
- **持久化记忆**：基于文件的 MEMORY.md 和 USER.md 存储关键信息
- **冻结快照模式**：系统提示稳定，写入立即持久化
- **安全扫描**：防止提示注入、数据外泄、SSH 后门
- **双工具支持**：bash + memory

## 安装

使用 [uv](https://github.com/astral-sh/uv) 管理依赖：

```bash
uv sync
```

## 使用

### 交互模式

```bash
uv run python agent.py
```

### 单次执行

```bash
uv run python agent.py "your task here"
```

## 配置

复制 `.env.example` 到 `.env` 并配置 API 密钥：

```bash
cp .env.example .env
```

```env
OPENAI_API_KEY=your_api_key_here
OPENAI_BASE_URL=https://api.openai.com/v1
MODEL=gpt-4o
```

## 记忆系统

记忆文件存储在 `memories/` 目录：

- `MEMORY.md`：代理的个人笔记（环境事实、项目约定、工具特性）
- `USER.md`：用户配置（偏好、沟通风格、期望）

记忆工具支持三种操作：

- `add`：添加新条目
- `replace`：替换现有条目
- `remove`：删除条目

## SOUL.md（代理人格）

SOUL.md 文件用于定义代理的身份、风格和行为方式。

**用途**：
- 定义代理的语气和沟通风格
- 指定代理应该避免什么
- 设置代理的默认行为方式

**不属于这里**：
- 项目特定的约定（使用 memory 工具保存）
- 文件路径、命令、端口等（使用 memory 工具保存）
- 临时的指令或任务

编辑 `SOUL.md` 文件来自定义代理人格，无需修改代码。

## 项目结构

```
.
├── agent.py          # 核心代理实现
├── memory.py         # 记忆模块
├── SOUL.md           # 代理人格定义
├── pyproject.toml    # 项目配置
├── .env              # 环境变量
├── .env.example      # 环境变量示例
└── memories/         # 记忆文件目录
    ├── MEMORY.md     # 代理笔记
    └── USER.md       # 用户配置
```

## 技术栈

- Python 3.11+
- requests（HTTP 客户端）
- python-dotenv（环境变量管理）

## 故障排除

### 调试模式

启用详细日志记录来诊断问题：

```env
DEBUG=true
```

调试模式会输出：
- API 请求详情（URL、模型、消息数）
- 响应状态和结构
- 工具调用信息
- 错误堆栈跟踪

### 常见问题

**Agent 没有响应**：
1. 检查 API 密钥配置：`OPENAI_API_KEY`
2. 检查网络连接和 API 端点：`OPENAI_BASE_URL`
3. 启用调试模式查看详细日志
4. 验证模型名称是否正确：`MODEL`

**空响应警告**：
如果看到 `# 注意：模型返回了空响应`，可能是：
- API 配额或限制问题
- 模型名称不正确
- 内容过滤触发

**超时错误**：
默认超时 120 秒，可在 `agent.py` 中修改。
