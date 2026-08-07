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
from api.tasks import router as tasks_router
from api.progress import router as progress_router
from api.achievements import router as achievements_router
from api.scenarios import router as scenarios_router
from api.asr import router as asr_router
from api.vocab import router as vocab_router
from api.reading import router as reading_router

# 数据库
from database.database import init_db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("edulingua-api")

app = FastAPI(
    title="Tan同学-AI英语助教 API",
    description="AI驱动的全栈英语学习系统 — 每日任务 + 场景对话 + 语音识别 + 进度看板 + 成就系统",
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

    # 自动加载 RAG 知识库
    try:
        from rag.document_loader import get_document_loader
        loader = get_document_loader()
        loader.load_all()
        logger.info("RAG 知识库初始化完成（8 语法规则 + 7 发音技巧）")
    except Exception as e:
        logger.warning(f"RAG 知识库初始化失败（将使用回退检索）: {e}")

    # 启动定时任务调度器
    try:
        from services.scheduler import start_scheduler
        start_scheduler()
        logger.info("定时任务调度器已启动")
    except Exception as e:
        logger.warning(f"定时任务调度器启动失败: {e}")

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
app.include_router(tasks_router)              # /api/tasks/*
app.include_router(progress_router)           # /api/progress/*
app.include_router(achievements_router)       # /api/achievements/*
app.include_router(scenarios_router)          # /api/scenarios/*
app.include_router(asr_router)                # /api/asr/*
app.include_router(vocab_router)             # /api/vocab/*
app.include_router(reading_router)           # /api/reading/*

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
            "tasks": "/api/tasks/*",
            "progress": "/api/progress/*",
            "achievements": "/api/achievements/*",
            "scenarios": "/api/scenarios/*",
            "asr": "/api/asr/*",
            "auth": "/api/auth/*",
        }
    }


# 非英语学习关键词（API 层拦截，节省 LLM 调用费用）
NON_ENGLISH_KEYWORDS = [
    # 数学
    '微积分', '线性代数', '概率论', '数学题', '解方程', '几何', '三角函数',
    # 编程
    '写代码', '写一个', '编程', 'debug', 'Python代码', 'Java代码', '帮我写', '前端页面', '后端接口',
    'leetcode', '算法题', '数据结构',
    # 物理/化学
    '物理', '化学', '牛顿', '量子', '分子式', '化学方程式',
    # 其他
    '历史', '地理', '政治', '生物',
]

def _is_off_topic(user_message: str) -> bool:
    """检测用户消息是否明显与英语学习无关"""
    msg_lower = user_message.lower()
    # 英语学习相关白名单词（有这些词的不拦截，避免误杀）
    english_white_list = ['英语', '英文', 'english', '单词', '语法', '发音', '口语',
                          '听力', '阅读', '写作', '翻译', '四级', '六级', '雅思',
                          '托福', '考研', '词汇', '句子', '对话', '跟读', '听写',
                          'hello', 'hi', 'what', 'how', 'why', 'when', 'where',
                          'thank', 'sorry', 'please', 'yes', 'no', 'ok']
    for w in english_white_list:
        if w in msg_lower:
            return False
    for kw in NON_ENGLISH_KEYWORDS:
        if kw in msg_lower:
            return True
    return False


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

        # 关键词拦截：非英语学习请求直接拒绝，不调用 LLM
        if _is_off_topic(last_message.content):
            logger.info(f"拦截非英语请求: user={request.user_id}, msg={last_message.content[:80]}")
            return ChatCompletion(
                id=generate_completion_id(),
                created=int(time.time()),
                model=request.model,
                choices=[{
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": "抱歉，我是专为英语学习设计的AI助教，只能辅导英语相关的内容。如果你有英语学习方面的问题（词汇、语法、发音、口语、听力、阅读、写作、考试等），我很乐意帮你！"
                    },
                    "finish_reason": "stop"
                }],
                usage={
                    "prompt_tokens": 0,
                    "completion_tokens": 0,
                    "total_tokens": 0
                }
            )

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
