#!/usr/bin/env python3
"""
Audit Log Module - Complete Conversation Tracking

Records full conversation history for audit and research purposes:
- User questions
- Tool calls
- Tool results
- Agent responses

Format: JSONL (one JSON object per line, append-only)
Location: memories/{user_id}/audit.jsonl
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
import threading


# Thread-safe file writing
_write_lock = threading.Lock()


def get_user_dir(user_id: str) -> Path:
    """Return the user's memory directory."""
    base_dir = Path(os.getcwd()) / "memories" / user_id
    base_dir.mkdir(parents=True, exist_ok=True)
    return base_dir


def get_audit_filename(user_id: str) -> Path:
    """Generate audit log filename for a specific user."""
    user_dir = get_user_dir(user_id)
    return user_dir / "audit.jsonl"


def write_audit_entry(user_id: str, entry: Dict[str, Any]) -> None:
    """
    Write a single audit entry to the user's audit log.

    Args:
        user_id: User identifier
        entry: Dictionary containing audit data
    """
    audit_file = get_audit_filename(user_id)

    # Add timestamp if not present
    if "timestamp" not in entry:
        entry["timestamp"] = datetime.now().isoformat()

    with _write_lock:
        # Append to file (create if doesn't exist)
        with open(audit_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def log_user_question(user_id: str, request_id: str, question: str,
                     system_prompt_length: int, history_length: int) -> None:
    """Log user's question."""
    entry = {
        "type": "user_question",
        "request_id": request_id,
        "user_id": user_id,
        "question": question,
        "question_length": len(question),
        "system_prompt_length": system_prompt_length,
        "history_messages": history_length
    }
    write_audit_entry(user_id, entry)


def log_api_request(user_id: str, request_id: str, endpoint: str,
                   payload_size: int, tool_count: int, model: str) -> None:
    """Log API request to upstream."""
    entry = {
        "type": "api_request",
        "request_id": request_id,
        "user_id": user_id,
        "endpoint": endpoint,
        "payload_size": payload_size,
        "tool_count": tool_count,
        "model": model
    }
    write_audit_entry(user_id, entry)


def log_api_response(user_id: str, request_id: str, status_code: int,
                    response_size: int, has_tool_calls: bool,
                    finish_reason: str, duration_ms: float) -> None:
    """Log API response from upstream."""
    entry = {
        "type": "api_response",
        "request_id": request_id,
        "user_id": user_id,
        "status_code": status_code,
        "response_size": response_size,
        "has_tool_calls": has_tool_calls,
        "finish_reason": finish_reason,
        "duration_ms": duration_ms
    }
    write_audit_entry(user_id, entry)


def log_tool_call(user_id: str, request_id: str, tool_name: str,
                 action: str, target: str, arguments: Dict[str, Any],
                 result: str, success: bool) -> None:
    """Log tool execution."""
    entry = {
        "type": "tool_call",
        "request_id": request_id,
        "user_id": user_id,
        "tool_name": tool_name,
        "action": action,
        "target": target,
        "arguments": arguments,
        "result": result,
        "success": success,
        "result_length": len(result) if result else 0
    }
    write_audit_entry(user_id, entry)


def log_agent_response(user_id: str, request_id: str, response: str,
                      response_length: int, total_duration_ms: float,
                      tool_calls_count: int) -> None:
    """Log agent's final response."""
    entry = {
        "type": "agent_response",
        "request_id": request_id,
        "user_id": user_id,
        "response": response,
        "response_length": response_length,
        "total_duration_ms": total_duration_ms,
        "tool_calls_count": tool_calls_count
    }
    write_audit_entry(user_id, entry)


def log_error(user_id: str, request_id: str, error_type: str,
             error_message: str, context: Optional[Dict[str, Any]] = None) -> None:
    """Log error during conversation."""
    entry = {
        "type": "error",
        "request_id": request_id,
        "user_id": user_id,
        "error_type": error_type,
        "error_message": error_message,
        "context": context or {}
    }
    write_audit_entry(user_id, entry)


def read_audit_log(user_id: str) -> list:
    """
    Read audit log for a specific user.

    Args:
        user_id: User identifier

    Returns:
        List of audit entries as dictionaries
    """
    audit_file = get_audit_filename(user_id)

    if not audit_file.exists():
        return []

    entries = []
    with open(audit_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    continue

    return entries
