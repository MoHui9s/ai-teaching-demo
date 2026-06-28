"""Streaming response handling for SSE."""

import json
import time
from typing import Generator, Dict, Any


def generate_completion_id() -> str:
    """Generate a unique completion ID."""
    return f"chatcmpl-{int(time.time() * 1000)}"


def stream_chat_completion(messages: list, model: str = "hermes") -> Generator[str, None, None]:
    """
    Stream chat completion in SSE format.

    Args:
        messages: List of messages
        model: Model name

    Yields:
        SSE formatted chunks
    """
    completion_id = generate_completion_id()
    created = int(time.time())

    # This is a placeholder - actual streaming would connect to upstream LLM
    # For now, we simulate streaming with chunks
    response_text = "This is a simulated streaming response. In production, this would stream from the upstream LLM API."

    # Split response into chunks for streaming effect
    chunk_size = 10
    for i in range(0, len(response_text), chunk_size):
        chunk = response_text[i:i + chunk_size]

        chunk_data = {
            "id": completion_id,
            "object": "chat.completion.chunk",
            "created": created,
            "model": model,
            "choices": [{
                "index": 0,
                "delta": {"content": chunk},
                "finish_reason": None
            }]
        }

        yield f"data: {json.dumps(chunk_data, ensure_ascii=False)}\n\n"
        time.sleep(0.05)  # Simulate streaming delay

    # Final chunk with finish_reason
    final_chunk = {
        "id": completion_id,
        "object": "chat.completion.chunk",
        "created": created,
        "model": model,
        "choices": [{
            "index": 0,
            "delta": {},
            "finish_reason": "stop"
        }]
    }

    yield f"data: {json.dumps(final_chunk, ensure_ascii=False)}\n\n"
    yield "data: [DONE]\n\n"


def stream_from_upstream(upstream_url: str, headers: Dict[str, str], payload: Dict[str, Any]) -> Generator[str, None, None]:
    """
    Stream response from upstream LLM API.

    Args:
        upstream_url: Upstream API URL
        headers: Request headers
        payload: Request payload

    Yields:
        SSE formatted chunks from upstream
    """
    import requests

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
