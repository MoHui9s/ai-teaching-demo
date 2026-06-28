"""API schemas for Hermes Agent."""

from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any


class ChatMessage(BaseModel):
    """Chat message in OpenAI format."""
    role: str = Field(..., description="Message role: 'user', 'assistant', or 'system'")
    content: str = Field(..., description="Message content")


class ChatRequest(BaseModel):
    """Chat completion request in OpenAI format."""
    model: str = Field(default="hermes", description="Model name")
    messages: List[ChatMessage] = Field(..., description="List of conversation messages")
    user_id: str = Field(default="default", description="User identifier for memory isolation")
    stream: bool = Field(default=False, description="Enable streaming response")
    temperature: Optional[float] = Field(default=None, description="Sampling temperature")
    max_tokens: Optional[int] = Field(default=None, description="Maximum tokens to generate")
    tools: Optional[List[Dict[str, Any]]] = Field(default=None, description="Tools to use")


class ChatCompletion(BaseModel):
    """Chat completion response."""
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: List[Dict[str, Any]]
    usage: Dict[str, int]


class ChatCompletionChunk(BaseModel):
    """Chat completion chunk for streaming."""
    id: str
    object: str = "chat.completion.chunk"
    created: int
    model: str
    choices: List[Dict[str, Any]]


class ClearHistoryRequest(BaseModel):
    """Request to clear user history."""
    user_id: str = Field(..., description="User identifier")


class ErrorResponse(BaseModel):
    """Error response."""
    error: Dict[str, Any]
