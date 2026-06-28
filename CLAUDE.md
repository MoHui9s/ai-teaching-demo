# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Common Development Commands

### Dependency Management
```bash
# Install/sync dependencies
uv sync
```

### Running the Agent
```bash
# Interactive REPL mode
uv run python agent.py

# Single command mode
uv run python agent.py "your task here"
```

### Running the API Server
```bash
# Start API server (default: 0.0.0.0:8000)
uv run uvicorn api.server:app --host 0.0.0.0 --port 8000

# Or using Python module
uv run python -m api.server
```

### Frontend Development
```bash
# Development server (frontend/)
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview
```

### Testing
```bash
# Run memory tests
uv run python test_memory.py
```

## Architecture Overview

Hermes Agent is a minimal multi-user AI agent framework with persistent memory and OpenAI API compatibility.

### Core Components

**HermesAgent (`agent.py`)**
- Main agent class implementing chat logic with tool calling support
- Each instance represents one user with isolated memory
- System prompt built from: base personality + SOUL.md + memory + tools guide + working directory
- Tool calls (memory) trigger continuation loop until final response
- History limited to `MAX_CONTEXT_ROUNDS` (default: 40) to manage context window

**MemoryStore (`memory.py`)**
- Per-user, file-based persistent storage
- Two parallel states:
  - `_system_prompt_snapshot`: frozen at load time for stable prefix cache
  - `memory_entries` / `user_entries`: live state mutated by tool calls
- Three memory operations: `add`, `replace`, `remove`
- Per-entry storage: each memory is a separate JSON file (`memories/{user_id}/memory/*.json` or `memories/{user_id}/user/*.json`)
- Character limits: 25,000 for memory, 15,000 for user
- Security scanning blocks injection/exfiltration patterns in memory content

**API Server (`api/server.py`)**
- FastAPI with OpenAI-compatible `/v1/chat/completions` endpoint
- In-memory agent cache per user_id
- Supports both streaming (SSE) and non-streaming responses
- Endpoints: chat completions, user history CRUD, user listing, health check

**Streaming (`api/stream.py`)**
- Two-phase streaming: stream upstream content, then handle tools non-streamingly
- Accumulates tool calls during streaming, executes after stream ends
- Sends "Saving memory..." status when tool_calls detected

### Memory System Details

```
memories/
├── {user_id}/
│   ├── memory/          # Agent's notes (environment facts, conventions)
│   │   └── *.json       # Per-entry files
│   ├── user/            # User profile (preferences, style)
│   │   └── *.json
│   └── history.json     # Short-term conversation history
```

Each memory entry file contains:
```json
{
  "id": "unique_id",
  "content": "entry text",
  "created": "ISO timestamp",
  "updated": "ISO timestamp"
}
```

**Key design choice**: The system prompt snapshot is frozen at `load_from_disk()` time. Mid-session memory writes don't affect the current session's system prompt - this preserves the prefix cache. Changes appear in the next session.

### SOUL.md

Global agent personality file (shared across all users). Used for:
- Defining agent tone and communication style
- Setting default behaviors
- Specifying what to avoid

Do NOT put user-specific memories or technical facts here - use the memory tool for those.

### Configuration

All configuration via `.env`:
- `OPENAI_API_KEY` / `ANTHROPIC_API_KEY`: API authentication
- `OPENAI_BASE_URL`: auto-constructs `/chat/completions` endpoint
- `MODEL`: model to use (default: gpt-4o)
- `MAX_CONTEXT_ROUNDS`: history round limit (default: 40)
- `DEBUG` / `LOG_LEVEL` / `LOG_FILE`: logging controls

### Windows Encoding Fix

The agent applies UTF-8 wrapper to stdout/stderr on Windows to handle encoding issues in CLI output.

## Tool Calling Flow

1. User message → API request
2. Agent builds system prompt with memory snapshot
3. LLM responds with potential tool_calls
4. For each tool call: execute `memory` tool, append result to history
5. Continue API call with updated history
6. Repeat until no more tool_calls
7. Save final history to disk

## Security

Memory content is scanned for:
- Prompt injection patterns (ignore instructions, system prompt override)
- Exfiltration attempts (curl with env vars, reading secret files)
- SSH backdoor patterns (authorized_keys, ~/.ssh)
- Invisible Unicode characters

Blocked content returns error without persisting.
