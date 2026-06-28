"""FastAPI server for Hermes Agent."""

import time
import json
import logging
from typing import List, Dict, Any
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware

import sys
import os
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from agent import HermesAgent, build_system_prompt, chat_url, MODEL, TOOL
from memory import MemoryStore
from api.schemas import (
    ChatRequest, ChatCompletion, ChatCompletionChunk, ErrorResponse
)

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("hermes-api")

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
                from api.stream import stream_chat_completion

                async def stream_generator():
                    for chunk in stream_chat_completion(request.messages, request.model):
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
            # Need to handle this properly
            # For now, just use the last message
            last_message = request.messages[-1]
            if last_message.role == "user":
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
        # Remove agent from cache
        if user_id in _agents:
            agent = _agents[user_id]
            agent.clear_history()
            del _agents[user_id]

        # Also clear memory directly
        temp_agent = HermesAgent(user_id)
        temp_agent.clear_history()

        return {
            "status": "success",
            "message": f"History cleared for user '{user_id}'"
        }
    except Exception as e:
        logger.error(f"Error clearing history: {e}")
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
        temp_agent = HermesAgent(user_id)
        return {
            "user_id": user_id,
            "messages": temp_agent.history,
            "count": len(temp_agent.history)
        }
    except Exception as e:
        logger.error(f"Error getting history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/v1/users")
async def list_users():
    """List all users with data."""
    try:
        from pathlib import Path
        memories_dir = Path("memories")
        if not memories_dir.exists():
            return {"users": []}

        users = []
        for user_dir in memories_dir.iterdir():
            if user_dir.is_dir() and (user_dir / "history.json").exists():
                users.append({
                    "user_id": user_dir.name,
                    "has_memory": (user_dir / "MEMORY.md").exists(),
                    "has_user_config": (user_dir / "USER.md").exists()
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
