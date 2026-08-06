"""FastAPI server —— Tan同学-AI英语助教"""

VERSION = "2.0.0"

import time
import json
import logging
import os
import sys
from typing import List, Dict, Any
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

sys.path.insert(0, str(Path(__file__).parent.parent))

from agent import HermesAgent, MODEL
from api.schemas import ChatRequest, ChatCompletion, ErrorResponse
from logging_config import log_user_action

# API 路由
from api.tts import router as tts_router
from api.admin import router as admin_router
from api.auth import router as auth_router
from api.asr import router as asr_router
from api.pronunciation import router as pronunciation_router
from api.tasks import router as tasks_router
from api.progress import router as progress_router
from api.achievements import router as achievements_router
from api.scenarios import router as scenarios_router

# 数据库
from database.database import init_db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("edulingua-api")

app = FastAPI(
    title="Tan同学-AI英语助教 API",
    description="AI驱动的全栈英语学习系统 — 每日任务 + 发音评估 + 场景对话 + 进度看板",
    version="2.0.0"
)


@app.on_event("startup")
async def startup_check():
    """启动验证：检查关键文件并初始化数据库"""
    # 检查 SOUL.md
    soul_path = Path(os.getcwd()) / "SOUL.md"
    if not soul_path.exists():
        logger.critical(
            f"致命错误：SOUL.md 未找到！期望路径：{soul_path}，"
            f"当前工作目录：{os.getcwd()}"
        )
        sys.exit(1)
    logger.info(f"SOUL.md 验证通过：{soul_path}")

    # 初始化数据库
    try:
        init_db()
        logger.info("数据库初始化完成")
    except Exception as e:
        logger.error(f"数据库初始化失败: {e}")

    logger.info(f"Tan同学-AI英语助教 v{VERSION} 启动完成")


# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(tts_router)                # /api/tts/*
app.include_router(admin_router)              # /api/admin/*
app.include_router(auth_router)               # /api/auth/*
app.include_router(asr_router)                # /api/asr/*
app.include_router(pronunciation_router)      # /api/pronunciation/*
app.include_router(tasks_router)              # /api/tasks/*
app.include_router(progress_router)           # /api/progress/*
app.include_router(achievements_router)       # /api/achievements/*
app.include_router(scenarios_router)          # /api/scenarios/*

# Agent 缓存
_agents: Dict[str, HermesAgent] = {}


def get_agent(user_id: str = "default") -> HermesAgent:
    """获取或创建用户 Agent"""
    if user_id not in _agents:
        _agents[user_id] = HermesAgent(user_id)
        logger.info(f"创建 Agent: user='{user_id}'")
    return _agents[user_id]


def generate_completion_id() -> str:
    """生成唯一 completion ID"""
    return f"chatcmpl-{int(time.time() * 1000)}"


# =============================================================================
# 核心端点
# =============================================================================


@app.get("/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "version": VERSION,
        "model": MODEL,
        "service": "Tan同学-AI英语助教"
    }


@app.get("/")
async def root():
    """API 根路径"""
    return {
        "service": "Tan同学-AI英语助教",
        "version": VERSION,
        "docs": "/docs",
        "endpoints": {
            "chat": "/v1/chat/completions",
            "tts": "/api/tts/*",
            "asr": "/api/asr/*",
            "pronunciation": "/api/pronunciation/*",
            "tasks": "/api/tasks/*",
            "progress": "/api/progress/*",
            "achievements": "/api/achievements/*",
            "scenarios": "/api/scenarios/*",
            "auth": "/api/auth/*",
        }
    }


@app.post("/v1/chat/completions")
async def chat_completions(request: ChatRequest):
    """
    OpenAI 兼容的聊天补全端点

    支持 Agent 工具调用（记忆、发音评估、场景对话、任务生成、知识检索）
    """
    try:
        log_user_action(logger, request.user_id, "chat_completion",
                        model=request.model, stream=request.stream,
                        message_count=len(request.messages))

        agent = get_agent(request.user_id)

        last_message = request.messages[-1]
        if last_message.role != "user":
            raise HTTPException(status_code=400, detail="最后一条消息必须是用户消息")

        response_text = agent.chat(last_message.content)

        completion_id = generate_completion_id()
        created = int(time.time())

        return ChatCompletion(
            id=completion_id,
            created=created,
            model=request.model,
            choices=[{
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": response_text
                },
                "finish_reason": "stop"
            }],
            usage={
                "prompt_tokens": len(str(last_message.content)),
                "completion_tokens": len(response_text),
                "total_tokens": len(str(last_message.content)) + len(response_text)
            }
        )

    except Exception as e:
        logger.error(f"聊天异常: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# 用户管理（兼容旧接口）
# =============================================================================


@app.delete("/v1/users/{user_id}/history")
async def clear_user_history(user_id: str):
    """清除用户对话历史"""
    try:
        log_user_action(logger, user_id, "clear_history")

        if user_id in _agents:
            agent = _agents[user_id]
            agent.clear_history()
            del _agents[user_id]

        temp_agent = HermesAgent(user_id)
        temp_agent.clear_history()

        logger.info(f"已清除用户历史: '{user_id}'")
        return {"status": "success", "message": f"已清除用户 '{user_id}' 的历史记录"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/v1/users/{user_id}/history")
async def get_user_history(user_id: str):
    """获取用户对话历史"""
    try:
        log_user_action(logger, user_id, "get_history")
        temp_agent = HermesAgent(user_id)
        history_count = len(temp_agent.history)
        return {
            "user_id": user_id,
            "messages": temp_agent.history,
            "count": history_count
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/v1/users")
async def list_users():
    """列出所有用户"""
    try:
        memories_dir = Path("memories")
        if not memories_dir.exists():
            return {"users": []}

        users = []
        for user_dir in memories_dir.iterdir():
            if user_dir.is_dir():
                history_path = user_dir / "history.json"
                has_history = history_path.exists()
                message_count = 0
                if has_history:
                    try:
                        with open(history_path, 'r', encoding='utf-8') as f:
                            history_data = json.load(f)
                            message_count = len(history_data) if isinstance(history_data, list) else 0
                    except Exception:
                        pass

                memory_dir = user_dir / "memory"
                user_config_dir = user_dir / "user"
                users.append({
                    "user_id": user_dir.name,
                    "has_history": has_history,
                    "message_count": message_count,
                    "has_memory": memory_dir.exists() and any(memory_dir.iterdir()),
                    "has_user_config": user_config_dir.exists() and any(user_config_dir.iterdir())
                })

        return {"users": users}
    except Exception as e:
        logger.error(f"获取用户列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn

    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", "8000"))

    logger.info(f"启动 Tan同学-AI英语助教 API: {host}:{port}")

    uvicorn.run(app, host=host, port=port)
