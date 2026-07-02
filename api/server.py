"""FastAPI server for Hermes Agent."""

VERSION = "1.4.0"

import time
import json
import logging
from typing import List, Dict, Any
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

import sys
import os
from typing import List, Dict, Any
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from agent import HermesAgent,  MODEL
from api.schemas import (
    ChatRequest, ChatCompletion, ErrorResponse
)
from logging_config import log_user_action
from api.tts import router as tts_router
from api.admin import router as admin_router
from api.auth import router as auth_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("hermes-api")

app = FastAPI(
    title="Hermes Agent API",
    description="Multi-user AI agent with persistent memory",
    version="1.0.0"
)


@app.on_event("startup")
async def startup_check():
    """Startup validation: ensure critical files exist before accepting requests."""
    from pathlib import Path
    import os

    soul_path = Path(os.getcwd()) / "SOUL.md"
    if not soul_path.exists():
        logger.critical(
            f"致命错误：SOUL.md 未找到！期望路径：{soul_path}，"
            f"当前工作目录：{os.getcwd()}"
        )
        import sys
        sys.exit(1)
    logger.info(f"SOUL.md 验证通过：{soul_path}")


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register TTS routes
app.include_router(tts_router)

# Register Admin routes
app.include_router(admin_router)

# Register Auth routes
app.include_router(auth_router)

_agents: Dict[str, HermesAgent] = {}


def get_agent(user_id: str = "default") -> HermesAgent:
    """Get or create agent for user."""
    if user_id not in _agents:
        _agents[user_id] = HermesAgent(user_id)
        logger.info(f"Created new agent for user '{user_id}'")
    return _agents[user_id]


def generate_completion_id() -> str:
    """Generate a unique completion ID."""
    return f"chatcmpl-{int(time.time() * 1000)}"


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "version": VERSION, "model": MODEL}


@app.post("/v1/chat/completions")
async def chat_completions(request: ChatRequest):
    """
    OpenAI-compatible chat completions endpoint.

    Returns non-streaming response. Streaming simulation should be done on client side.
    """
    try:
        # Log request
        log_user_action(logger, request.user_id, "chat_completion",
                        model=request.model, stream=request.stream,
                        message_count=len(request.messages))

        # Get or create agent for user
        agent = get_agent(request.user_id)

        # Get the last user message
        last_message = request.messages[-1]
        if last_message.role != "user":
            raise HTTPException(status_code=400, detail="Last message must be from user")

        # Get response from agent
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
        logger.error(f"Error in chat_completions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/v1/users/{user_id}/history")
async def clear_user_history(user_id: str):
    """
    Clear conversation history for a specific user.

    Args:
        user_id: User identifier

    Returns:
        Success message
    """
    try:
        log_user_action(logger, user_id, "clear_history")

        # Remove agent from cache
        if user_id in _agents:
            agent = _agents[user_id]
            agent.clear_history()
            del _agents[user_id]

        # Also clear memory directly
        temp_agent = HermesAgent(user_id)
        temp_agent.clear_history()

        logger.info(f"History cleared for user '{user_id}'")
        return {
            "status": "success",
            "message": f"History cleared for user '{user_id}'"
        }
    except Exception as e:
        log_error(logger, e, context="clear_user_history")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/v1/users/{user_id}/history")
async def get_user_history(user_id: str):
    """
    Get conversation history for a specific user.

    Args:
        user_id: User identifier

    Returns:
        List of messages
    """
    try:
        log_user_action(logger, user_id, "get_history")
        temp_agent = HermesAgent(user_id)
        history_count = len(temp_agent.history)
        logger.info(f"Retrieved {history_count} messages for user '{user_id}'")
        return {
            "user_id": user_id,
            "messages": temp_agent.history,
            "count": history_count
        }
    except Exception as e:
        log_error(logger, e, context="get_user_history")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/v1/users")
async def list_users():
    """List all users with data."""
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
        logger.error(f"Error listing users: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn

    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", "8000"))

    logger.info(f"Starting Hermes Agent API on {host}:{port}")

    uvicorn.run(app, host=host, port=port)
