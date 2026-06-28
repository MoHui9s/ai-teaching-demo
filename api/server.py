"""FastAPI server for Hermes Agent."""

import time
import json
import logging
import sys
import os
from typing import List, Dict, Any
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from agent import HermesAgent, build_system_prompt, chat_url, MODEL, TOOL
from memory import MemoryStore
from api.schemas import (
    ChatRequest, ChatCompletion, ChatCompletionChunk, ErrorResponse
)
from api import voice
from logging_config import (
    setup_logging, get_logger, log_request, log_response,
    log_error, log_user_action
)

# Setup logging
logger = setup_logging(log_file=True, log_to_console=True)

# Create FastAPI app
app = FastAPI(
    title="Hermes Agent API",
    description="Multi-user AI agent with persistent memory",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include voice service router
app.include_router(voice.router)

# Mount static files for the frontend
static_dir = Path(__file__).parent.parent / "static"
if static_dir.exists():
    # Mount at root level so /assets/ works correctly
    app.mount("/assets", StaticFiles(directory=str(static_dir / "assets")), name="assets")
    # Also serve icons and other static files
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

@app.get("/")
async def index():
    """Serve the frontend index page."""
    index_path = Path(__file__).parent.parent / "static" / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path))
    return {"message": "Hermes Agent API is running. Build frontend with `cd frontend && npm run build`"}


# In-memory agent cache (simple version)
# In production, use proper cache with TTL
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
    return {"status": "healthy", "model": MODEL}


@app.post("/v1/chat/completions")
async def chat_completions(request: ChatRequest):
    """
    OpenAI-compatible chat completions endpoint.

    Supports both streaming and non-streaming responses.
    """
    try:
        # Log request
        log_user_action(logger, request.user_id, "chat_completion",
                        model=request.model, stream=request.stream,
                        message_count=len(request.messages))

        # Get or create agent for user
        agent = get_agent(request.user_id)

        # Convert request messages to simple format
        # If only one user message, use chat() method
        # If multiple messages, need to reconstruct context

        if len(request.messages) == 1 and request.messages[0].role == "user":
            # Simple case: single user message
            user_prompt = request.messages[0].content

            if request.stream:
                # Streaming response
                from api.stream import stream_agent_chat

                async def stream_generator():
                    # Convert request messages to dicts for streaming
                    messages_dicts = [{"role": msg.role, "content": msg.content} for msg in request.messages]
                    for chunk in stream_agent_chat(agent, messages_dicts, request.model):
                        yield chunk

                return StreamingResponse(
                    stream_generator(),
                    media_type="text/event-stream"
                )
            else:
                # Non-streaming response
                response_text = agent.chat(user_prompt)

                completion_id = generate_completion_id()
                created = int(time.time())

                # Log response
                log_response(logger, 200, completion_id=completion_id,
                             tokens=len(response_text))

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
                        "prompt_tokens": 0,
                        "completion_tokens": len(response_text),
                        "total_tokens": len(response_text)
                    }
                )
        else:
            # Complex case: multiple messages or conversation history
            # Use the last user message for streaming, or last message generally
            last_message = request.messages[-1]

            # Find the last user message
            user_prompt = None
            for msg in reversed(request.messages):
                if msg.role == "user":
                    user_prompt = msg.content
                    break

            if user_prompt and request.stream:
                # Streaming response with conversation history
                from api.stream import stream_agent_chat

                async def stream_generator():
                    # For streaming, we send the last user message
                    # The agent handles history from its own state
                    messages_dicts = [{"role": "user", "content": user_prompt}]
                    for chunk in stream_agent_chat(agent, messages_dicts, request.model):
                        yield chunk

                return StreamingResponse(
                    stream_generator(),
                    media_type="text/event-stream"
                )
            elif user_prompt:
                # Non-streaming response
                response_text = agent.chat(user_prompt)

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
                        "prompt_tokens": 0,
                        "completion_tokens": len(response_text),
                        "total_tokens": len(response_text)
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
