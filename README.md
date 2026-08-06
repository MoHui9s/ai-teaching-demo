# Tan同学-AI英语助教 📚

> **AI 驱动的全栈英语学习系统** — 基于大模型 Agent + RAG + 语音评估

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
| 🗣️ 发音不标准 | Azure 语音评估 + 逐词评分 + 音素级纠错 |
| 🌍 缺少语言环境 | 10+ 内置场景对话，AI NPC 角色扮演 |
| 📅 目标模糊 | 每日"三件事"任务引擎 + 进度热力图 |
| 🏆 自制力弱 | 成就徽章系统 + 连续打卡激励 |

## 🏗️ 技术架构

```
┌─────────────────────────────────────────────────────┐
│               前端 (React + TS + Tailwind)             │
│  Dashboard │ Tasks │ Pronunciation │ Scenarios │ Progress │ Achievements │
└─────────────────────┬───────────────────────────────┘
                      │ HTTP/REST
┌─────────────────────▼───────────────────────────────┐
│                  后端 (FastAPI)                        │
│  /api/asr  /api/pronunciation  /api/tasks  /api/progress  /api/scenarios │
└──────────────────┬──────────────────────────────────┘
                   │
    ┌──────────────┼──────────────┐
    ▼              ▼              ▼
┌───────┐  ┌──────────┐  ┌──────────────┐
│ Agent │  │ RAG 系统  │  │ Azure 语音    │
│ 5工具  │  │ ChromaDB  │  │ ASR+发音+TTS │
└───────┘  └──────────┘  └──────────────┘
    │              │
    ▼              ▼
┌─────────────────────────────────┐
│  LLM (DeepSeek / 智谱 / GPT)    │
│  Embedding + ChromaDB 向量检索   │
└─────────────────────────────────┘
```

### 技术栈

| 层级 | 选型 |
|------|------|
| **前端** | React 18 + TypeScript + Tailwind CSS + Vite |
| **后端** | FastAPI + Pydantic + SQLAlchemy ORM |
| **Agent** | HermesAgent + 5 工具（记忆/发音/任务/场景/RAG）|
| **RAG** | ChromaDB + OpenAI Embeddings + 内置语法/发音知识库 |
| **语音** | Azure Speech SDK (ASR + 发音评估) + Edge TTS |
| **数据库** | SQLite (开发) / PostgreSQL (生产) |
| **部署** | Docker + Nginx |

## 🚀 快速开始

### 前置要求

- Python ≥ 3.11
- Node.js ≥ 18
- Edge TTS（免费，无需 API Key）
- Azure Speech（可选，用于发音评估）

### 1. 环境配置

```bash
cd Tan同学-AI英语助教
# 编辑 .env，填入 API Key
```

### 2. 后端启动

```bash
# 安装依赖
uv sync

# 初始化数据库
python -c "from database.database import init_db; init_db()"

# 加载 RAG 知识库（可选）
python -c "from rag.document_loader import get_document_loader; get_document_loader().load_all()"

# 启动 API 服务
uv run uvicorn api.server:app --host 0.0.0.0 --port 8000 --reload
```

访问 http://localhost:8000/docs 查看 API 文档。

### 3. 前端启动

```bash
cd frontend
npm install
npm run dev
```

访问 http://localhost:5173

### 4. Docker 部署（推荐）

```bash
docker-compose -f deploy/docker-compose.yml up -d
```

## 📡 API 端点

| 端点 | 说明 |
|------|------|
| `POST /v1/chat/completions` | OpenAI 兼容聊天（Agent 5工具）|
| `POST /api/pronunciation/evaluate` | 发音评估（逐词评分）|
| `POST /api/asr/transcribe` | 语音转文字 |
| `GET /api/tasks/daily` | 获取/生成每日任务 |
| `POST /api/tasks/daily/complete` | 完成子任务 |
| `POST /api/tasks/diagnosis` | 初始能力诊断 |
| `GET /api/progress/overview` | 学习进度概览（热力图）|
| `GET /api/progress/weekly-report` | 周报 |
| `GET /api/scenarios/list` | 场景列表 |
| `POST /api/scenarios/start` | 启动场景对话 |
| `POST /api/tts/audio` | 文字转语音 |
| `GET /api/achievements/list` | 成就列表 |
| `POST /api/auth/login` | 用户登录 |

## 🧠 Agent 工具

| 工具 | 功能 |
|------|------|
| `memory` | 持久化学生偏好、薄弱项、学习历史 |
| `evaluate_pronunciation` | 发音评估，逐词评分 + 音素纠错 |
| `generate_daily_task` | 基于学生水平动态生成每日任务 |
| `start_scenario` | 启动 10+ 场景 NPC 对话 |
| `search_knowledge` | RAG 检索语法规则/发音技巧 |

## 📁 项目结构

```
Tan同学-AI英语助教/
├── api/                    # FastAPI 端点 (9路由)
├── agent.py                # Agent 核心 (5工具)
├── memory.py               # 文件系统记忆
├── rag/                    # RAG 系统 (ChromaDB+Embedding)
├── services/               # Azure ASR/发音/TTS/场景/周报
├── database/               # SQLAlchemy ORM
├── frontend/               # React 前端 (6页面)
├── deploy/                 # Docker 部署
├── SOUL.md                 # Agent 人格定义
└── .env                    # 环境配置
```

## 🎓 求职展示要点

1. **全栈能力**：React + FastAPI + Docker 完整链路
2. **大模型应用**：Agent 工具调用循环 + Prompt 工程 + RAG
3. **第三方 API 集成**：Azure 语音评估 / Edge TTS
4. **工程化思维**：分层架构、数据库设计、API 文档
5. **产品思维**：从真实痛点出发，设计完整用户体验闭环

## 📝 License

MIT — 开源用于学习交流。

---

> **Tan同学-AI英语助教** — 让每一个英语困难户每天进步一点点 🌟
