# Tan同学-AI英语助教 📚

> **AI 驱动的全栈英语学习系统** — Agent + RAG + ASR + TTS

[![Python](https://img.shields.io/badge/Python-3.12-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green.svg)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18-61DAFB.svg)](https://react.dev)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

## 🎯 项目简介

一个面向国内大学生（以 Tan 同学为典型用户）的 AI 英语学习系统，采用 **每日微小任务 + AI 即时反馈 + 学习进度可视化** 的设计哲学，帮助英语基础薄弱的学习者在碎片时间中稳步提升听说读写能力。

### 核心痛点解决

| 痛点 | 解决方案 |
|------|----------|
| 📝 词汇量不足（~2500） | AI 动态生成每日词汇任务，RAG 知识库即时查词 |
| 🌍 缺少语言环境 | 10+ 内置场景对话，AI NPC 角色扮演 |
| 🎤 口语练习 | 百炼 ASR 语音转文字，Edge TTS 标准发音 |
| 📅 目标模糊 | 每日"三件事"任务引擎 + 进度热力图 |
| 🏆 自制力弱 | 成就徽章系统 + 连续打卡激励 |

## 🏗️ 技术架构

```
┌─────────────────────────────────────────────────────┐
│            前端 (React + TS + Tailwind)                │
│  Dashboard │ Tasks │ Scenario │ Progress              │
│  Achievements │ Diagnosis │ Login/Register            │
└─────────────────────┬───────────────────────────────┘
                      │ HTTP/REST (JWT Auth)
┌─────────────────────▼───────────────────────────────┐
│                  后端 (FastAPI)                        │
│  /api/auth  /api/tasks  /api/progress                 │
│  /api/scenarios  /api/achievements  /api/tts  /api/asr│
│  /v1/chat/completions                                 │
└──────────────────┬──────────────────────────────────┘
                   │
    ┌──────────────┼──────────────┐
    ▼              ▼              ▼
┌───────┐  ┌──────────┐  ┌──────────────┐
│ Agent │  │ RAG 系统  │  │ 语音服务      │
│ 4工具  │  │ ChromaDB  │  │ ASR + TTS    │
└───────┘  └──────────┘  └──────────────┘
    │              │              │
    ▼              ▼              ▼
┌─────────────────────────────────────┐
│     阿里云百炼 DashScope              │
│  qwen-plus + text-embedding-v4      │
│  + qwen3-asr-flash                   │
└─────────────────────────────────────┘
```

### 技术栈

| 层级 | 选型 |
|------|------|
| **前端** | React 18 + TypeScript + Tailwind CSS + Vite |
| **后端** | FastAPI + Pydantic + SQLAlchemy ORM |
| **Agent** | HermesAgent + 4 工具（记忆/任务/场景/RAG）|
| **Chat LLM** | 百炼 qwen-plus（支持 function calling） |
| **RAG** | ChromaDB + 百炼 text-embedding-v4 + 内置语法/发音知识库 |
| **ASR** | 百炼 qwen3-asr-flash（25+ 语言） |
| **TTS** | Edge TTS（免费，6 种英语声音） |
| **数据库** | SQLite (开发) / PostgreSQL (生产) |
| **部署** | Docker + Nginx |

## 🚀 快速开始

### 前置要求

- Python ≥ 3.11
- Node.js ≥ 18
- 百炼 API Key（免费注册获得 100 万 Token/模型）

### 1. 获取 API Key

1. 打开 [阿里云百炼控制台](https://bailian.console.aliyun.com/)
2. 进入「模型广场」→「API Key 管理」→ 创建 API Key
3. 为每个模型开启「免费额度用完即停」

### 2. 环境配置

```bash
cd Tan同学-AI英语助教
# 编辑 .env，将 OPENAI_API_KEY 替换为你的百炼 API Key
```

### 3. 后端启动

```bash
# 安装依赖
uv sync

# 启动 API 服务（数据库 + RAG + 定时任务自动初始化）
uv run uvicorn api.server:app --host 0.0.0.0 --port 8000 --reload
```

访问 http://localhost:8000/docs 查看 API 文档。

### 4. 前端启动

```bash
cd frontend
npm install
npm run dev
```

访问 http://localhost:5173

### 5. 停止服务

```bash
# 停止后端 (占用 8000 端口)
taskkill /F /IM "uvicorn.exe"

# 停止前端 (占用 5173 端口)
taskkill /F /IM "node.exe"
```

或者按端口精确终止：

```bash
# Windows — 一键停全部
netstat -ano | grep -E "8000|5173" | awk '{print $5}' | xargs -I{} taskkill /F /PID {}
```

## 📡 API 端点

| 端点 | 说明 |
|------|------|
| `POST /v1/chat/completions` | Agent 对话（4 工具，qwen-plus）|
| `POST /api/auth/login` | 用户登录（JWT） |
| `POST /api/auth/register` | 用户注册（注册即登录） |
| `GET /api/tasks/daily` | 获取/生成每日任务（LLM 动态生成）|
| `POST /api/tasks/daily/complete` | 完成子任务 |
| `POST /api/tasks/diagnosis` | 初始能力诊断 |
| `GET /api/progress/overview` | 学习进度概览（热力图）|
| `GET /api/progress/weekly-report` | 周报 |
| `GET /api/scenarios/list` | 场景列表 |
| `POST /api/scenarios/start` | 启动场景对话 |
| `POST /api/asr/transcribe` | 语音转文字（百炼 ASR）|
| `GET /api/asr/health` | ASR 服务健康检查 |
| `POST /api/tts/audio` | 文字转语音（Edge TTS）|
| `GET /api/achievements/list` | 成就列表 |
| `POST /api/achievements/check` | 检查并解锁成就 |

## 🧠 Agent 工具

| 工具 | 功能 |
|------|------|
| `memory` | 持久化学生偏好、薄弱项、学习历史 |
| `generate_daily_task` | LLM 动态生成每日任务（基于水平和薄弱项）|
| `start_scenario` | 启动 10+ 场景 NPC 对话 |
| `search_knowledge` | RAG 检索语法规则/发音技巧 |

## 📁 项目结构

```
Tan同学-AI英语助教/
├── api/                    # FastAPI 端点 (9 路由)
│   ├── _user_sync.py       # 双数据库同步工具
│   ├── auth.py             # JWT 认证 + 注册
│   ├── tasks.py            # 每日任务 + 能力诊断
│   ├── progress.py         # 学习进度 + 周报
│   ├── achievements.py     # 成就检测与解锁
│   └── ...
├── agent.py                # Agent 核心 (4 工具)
├── memory.py               # 文件系统记忆
├── rag/                    # RAG 系统 (ChromaDB + text-embedding-v4)
├── services/               # Edge TTS / 场景 / 周报 / 定时任务
├── database/               # SQLAlchemy ORM (7 表)
├── frontend/               # React 前端 (6 页面)
│   └── src/
│       ├── pages/
│       │   ├── Dashboard.tsx      # 学习看板 + 新用户引导
│       │   ├── DailyTasks.tsx     # 每日任务
│       │   ├── ScenarioChat.tsx   # 场景对话
│       │   ├── Progress.tsx       # 进度看板
│       │   ├── Achievements.tsx   # 成就徽章页
│       │   ├── Diagnosis.tsx      # 能力诊断 (NEW)
│       │   └── Login.tsx          # 登录/注册 (NEW)
│       └── components/
│           ├── BottomNav.tsx       # 底部导航 (5 标签)
│           ├── OnboardingGuide.tsx # 新用户引导卡片 (NEW)
│           └── ...
├── scripts/
│   └── cdp_test.py         # Chrome CDP 自动化测试 (NEW)
├── deploy/                 # Docker 部署
├── SOUL.md                 # Agent 人格定义
└── .env                    # 环境配置（百炼 API Key）
```

## 🧪 CDP 自动化测试

项目内置 Chrome DevTools Protocol 前端测试脚本，覆盖全部 9 个关键用户路径：

```bash
# 1. 启动 Chrome headless（仅测试需要）
"C:\Program Files\Google\Chrome\Application\chrome.exe" \
  --headless --disable-gpu \
  --remote-debugging-port=9222 \
  --remote-allow-origins=* \
  --window-size=1920,1080

# 2. 运行测试
cd "d:/cc_demo/Tan同学-AI英语助教"
PYTHONIOENCODING=utf-8 .venv/Scripts/python scripts/cdp_test.py

# 3. 停止 Chrome
taskkill /F /IM "chrome.exe"
```

测试覆盖：登录页 → 注册 → Dashboard → 诊断 → 场景对话 → 成就 → 退出 → 重新登录。截图保存至 `logs/screenshots/`。

## 🎓 求职展示要点

1. **全栈能力**：React + FastAPI + Docker 完整链路
2. **大模型应用**：Agent 工具调用循环 + LLM 动态任务生成 + Prompt 工程 + RAG
3. **多模态集成**：ASR 语音识别 + TTS 语音合成 + 文本对话
4. **云服务对接**：阿里云百炼 DashScope（Chat + Embedding + ASR）
5. **工程化思维**：分层架构、数据库设计、API 文档、定时任务、CDP 自动化测试
6. **产品思维**：从真实痛点出发，设计完整用户体验闭环（注册→诊断→任务→成就）
7. **前后端协同**：JWT 认证、双数据库同步、新用户引导流程

## 📝 License

MIT — 开源用于学习交流。

---

> **Tan同学-AI英语助教** — 让每一个英语困难户每天进步一点点 🌟
