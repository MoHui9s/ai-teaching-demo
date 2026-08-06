# CLAUDE.md

This file provides guidance to Claude Code when working with code in this repository.

## 项目概述

**Tan同学-AI英语助教** — 基于 lee_agent (Hermes Agent) 改造的 AI 驱动全栈英语学习系统。面向国内初中级英语学习者，涵盖每日任务引擎、语音识别、场景对话、进度看板、成就系统、RAG 知识检索模块。

## 常用命令

### 依赖管理
```bash
uv sync
```

### 后端启动
```bash
# 数据库 + RAG + 定时任务均在启动时自动初始化
uv run uvicorn api.server:app --host 0.0.0.0 --port 8000 --reload
```

### Agent REPL
```bash
uv run python agent.py "帮我生成今天的英语学习任务"
```

### 前端启动
```bash
cd frontend && npm install && npm run dev
```

### Docker 部署
```bash
docker-compose -f deploy/docker-compose.yml up -d
```

## 架构概览

### AI 供应商：阿里云百炼 DashScope

统一使用百炼 API（`https://dashscope.aliyuncs.com/compatible-mode/v1`）：
- **Chat LLM**: `qwen-plus` — Agent 工具调用
- **Embedding**: `text-embedding-v4` — RAG 向量检索（Qwen3-Embedding，1024 维）
- **ASR**: `qwen3-asr-flash` — 语音转文字（多模态 API）
- **TTS**: Edge TTS（免费，本地调用）

每个模型均有 100 万 Token 免费额度（90 天有效）。

### 核心组件

**Agent (`agent.py`)**
- `HermesAgent` 类：多用户 Agent，4 个工具
- 工具：memory / generate_daily_task / start_scenario / search_knowledge
- `_agent_loop()` 主循环：最多 8 次迭代，支持 tool_calls → execute → continue
- `build_system_prompt()` 构建系统提示：基础人格 + SOUL.md + 工具说明 + 记忆
- `_call_llm_direct()` 方法：单次 LLM 调用（不走 tool loop），用于任务生成等轻量内容

**RAG 系统 (`rag/`)**
- `embeddings.py`：OpenAI 兼容 Embedding（百炼 text-embedding-v4），API 不可用时 fallback 到 MD5 模拟向量
- `vector_store.py`：ChromaDB 持久化向量存储
- `retriever.py`：知识检索器（语义搜索 + 关键词回退）
- `document_loader.py`：内置 8 语法规则 + 7 发音技巧，启动时自动加载

**数据库 (SQLAlchemy ORM)**
- 7 张表：users / daily_tasks / pronunciation_records / dialog_history / daily_progress / achievements / weekly_reports
- `database/database.py`：引擎 + Session 管理
- `database/models.py`：ORM 模型定义 + 12 个预设成就

**API 服务**
- 8 个路由模块：server / auth / tts / asr / tasks / progress / achievements / scenarios
- 兼容 OpenAI `/v1/chat/completions` 格式
- 启动事件自动：init_db() → load_all() → start_scheduler()

**定时任务 (`services/scheduler.py`)**
- APScheduler BackgroundScheduler
- 每周日 23:00 自动生成学习周报

### SOUL.md

定义 Agent 核心人格：耐心鼓励型的 AI 英语私教，支持多种教学模式（每日任务、场景对话、能力诊断、周报总结）。

### 配置

- LLM / Embedding / ASR：`.env` 中 `OPENAI_API_KEY`（百炼 API Key）+ `OPENAI_BASE_URL`
- TTS：Edge TTS，免费无需 API Key
- 每日预算：`DAILY_API_BUDGET=2.0`（元）

## 已知问题

- **`api/voice.py`**：未注册的旧语音服务路由，依赖不存在的 `voice` 模块（WhisperSTT/KokoroTTS），属于废弃代码。
- **前端 `node_modules`**：需 `npm install` 后构建。

## 项目来源

本项目从 lee_agent (https://gitee.com/ichiva_admin/lee_agent.git) 克隆改造而来。保留的模块：Agent 循环、记忆系统、TTS 服务、JWT 认证、审计日志。
