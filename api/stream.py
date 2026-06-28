"""Streaming response handling for SSE."""

import json
import time
import requests
from typing import Generator, Dict, Any

# Import agent utilities
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from agent import chat_url, api_key


def generate_completion_id() -> str:
    """Generate a unique completion ID."""
    return f"chatcmpl-{int(time.time() * 1000)}"


def stream_from_upstream(upstream_url: str, headers: Dict[str, str], payload: Dict[str, Any]) -> Generator[str, None, None]:
    """
    Stream response from upstream LLM API (direct passthrough).

    Args:
        upstream_url: Upstream API URL
        headers: Request headers
        payload: Request payload

    Yields:
        SSE formatted chunks from upstream
    """
    completion_id = generate_completion_id()
    created = int(time.time())

    with requests.post(upstream_url, headers=headers, json=payload, stream=True, timeout=120) as response:
        response.raise_for_status()

        for line in response.iter_lines():
            if line:
                line = line.decode('utf-8')
                if line.startswith('data: '):
                    data_str = line[6:]  # Remove 'data: ' prefix
                    if data_str.strip() == '[DONE]':
                        yield "data: [DONE]\n\n"
                    else:
                        try:
                            data = json.loads(data_str)
                            # Update with our metadata
                            data['id'] = completion_id
                            data['created'] = created
                            data['model'] = 'hermes'
                            yield f"data: {json.dumps(data, ensure_ascii=False)}\n\n"
                        except json.JSONDecodeError:
                            # Pass through non-JSON lines
                            yield f"{line}\n\n"
                else:
                    yield f"{line}\n\n"


def stream_agent_chat(agent, messages: list, model: str = "hermes") -> Generator[str, None, None]:
    """
    Stream chat completion with two-phase: stream content, then handle tools.

    Phase 1: Stream upstream content deltas to client while accumulating full message
    Phase 2: After stream ends, handle tool calls (if any) via non-streaming path, send final result

    Args:
        agent: HermesAgent instance
        messages: List of messages from the request (including the new user message)
        model: Model name

    Yields:
        SSE formatted chunks (content deltas, tool status, final result)
    """
    # Get the user message from the last item in messages
    user_msg = messages[-1] if messages and messages[-1].get("role") == "user" else None
    if not user_msg:
        # No user message to process
        yield "data: [DONE]\n\n"
        return

    # Prepare request using agent's shared logic
    # Pass the user prompt so agent._prepare_request appends it to history
    headers, payload, messages_with_system = agent._prepare_request(user_msg.get("content"))

    # Add stream=True to payload for upstream API
    payload["stream"] = True

    completion_id = generate_completion_id()
    created = int(time.time())

    # Accumulated message from upstream
    accumulated_content = ""
    accumulated_tool_calls = []
    has_tool_calls = False

    # Phase 1: Stream upstream, forward content deltas, accumulate message
    with requests.post(chat_url, headers=headers, json=payload, stream=True, timeout=120) as response:
        try:
            response.raise_for_status()
        except Exception as e:
            # Yield error chunk
            error_chunk = {
                "id": completion_id,
                "object": "chat.completion.chunk",
                "created": created,
                "model": model,
                "choices": [{
                    "index": 0,
                    "delta": {"content": f"# Error: {str(e)}"},
                    "finish_reason": "stop"
                }]
            }
            yield f"data: {json.dumps(error_chunk, ensure_ascii=False)}\n\n"
            yield "data: [DONE]\n\n"
            return

        for line in response.iter_lines():
            if line:
                line = line.decode('utf-8')
                if line.startswith('data: '):
                    data_str = line[6:].strip()
                    if data_str == '[DONE]':
                        break

                    try:
                        data = json.loads(data_str)
                        choice = data.get("choices", [{}])[0]
                        delta = choice.get("delta", {})

                        # Forward content delta immediately for typewriter effect
                        # Handle both 'content' (standard) and skip 'reasoning_content' (GLM model internal)
                        content_delta = delta.get("content", "")
                        if content_delta:
                            accumulated_content += content_delta
                            chunk = {
                                "id": completion_id,
                                "object": "chat.completion.chunk",
                                "created": created,
                                "model": model,
                                "choices": [{
                                    "index": 0,
                                    "delta": {"content": content_delta},
                                    "finish_reason": None
                                }]
                            }
                            yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"
                        # Skip reasoning_content (GLM model's internal thinking process)
                        # but still track it for debugging if needed
                        elif "reasoning_content" in delta and delta["reasoning_content"]:
                            # Silently accumulate or skip reasoning content
                            # We don't forward this to the client
                            pass

                        # Accumulate tool_calls if present
                        if "tool_calls" in delta and delta["tool_calls"]:
                            has_tool_calls = True
                            for tc_delta in delta["tool_calls"]:
                                if tc_delta.get("index") == len(accumulated_tool_calls):
                                    # New tool call
                                    accumulated_tool_calls.append({
                                        "id": tc_delta.get("id"),
                                        "type": tc_delta.get("type", "function"),
                                        "function": {
                                            "name": tc_delta.get("function", {}).get("name"),
                                            "arguments": tc_delta.get("function", {}).get("arguments", "")
                                        }
                                    })
                                else:
                                    # Update existing tool call
                                    idx = tc_delta.get("index")
                                    if idx < len(accumulated_tool_calls):
                                        func = accumulated_tool_calls[idx]["function"]
                                        if tc_delta.get("function", {}).get("name"):
                                            func["name"] = tc_delta["function"]["name"]
                                        if tc_delta.get("function", {}).get("arguments"):
                                            func["arguments"] += tc_delta["function"]["arguments"]

                        # Check finish_reason
                        finish_reason = choice.get("finish_reason")
                        if finish_reason:
                            if finish_reason == "tool_calls":
                                has_tool_calls = True
                                # Send status event for UI to show "Saving memory..."
                                status_chunk = {
                                    "id": completion_id,
                                    "object": "chat.completion.chunk",
                                    "created": created,
                                    "model": model,
                                    "choices": [{
                                        "index": 0,
                                        "delta": {"status": "Saving memory..."},
                                        "finish_reason": None
                                    }]
                                }
                                yield f"data: {json.dumps(status_chunk, ensure_ascii=False)}\n\n"
                            break
                    except json.JSONDecodeError:
                        continue

    # Phase 2: Handle tool calls if any (non-streaming path as per user request)
    if has_tool_calls and accumulated_tool_calls:
        # Construct the assistant message with tool_calls
        assistant_message = {
            "role": "assistant",
            "content": accumulated_content,
            "tool_calls": [
                {
                    "id": tc["id"],
                    "type": tc["type"],
                    "function": {
                        "name": tc["function"]["name"],
                        "arguments": tc["function"]["arguments"]
                    }
                }
                for tc in accumulated_tool_calls
            ]
        }

        # Let agent handle the response (tools, memory, continuation)
        final_text, _ = agent._handle_response_message(assistant_message)

        # Send the final result as a single delta
        final_chunk = {
            "id": completion_id,
            "object": "chat.completion.chunk",
            "created": created,
            "model": model,
            "choices": [{
                "index": 0,
                "delta": {"content": final_text},
                "finish_reason": "stop"
            }]
        }
        yield f"data: {json.dumps(final_chunk, ensure_ascii=False)}\n\n"
    else:
        # No tool calls, just save history via agent
        assistant_message = {
            "role": "assistant",
            "content": accumulated_content
        }
        agent._handle_response_message(assistant_message)

    # Send final [DONE]
    yield "data: [DONE]\n\n"