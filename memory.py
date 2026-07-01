#!/usr/bin/env python3
"""
Memory Module - Persistent Curated Memory with Per-Entry File Storage

Provides bounded, file-backed memory that persists across sessions. Two stores:
  - memory/: agent's personal notes (environment facts, project conventions, tool quirks)
  - user/: user profile (preferences, communication style, expectations, workflow habits)

Each memory entry is stored as a separate JSON file for granular management.

Entry structure:
{
  "id": "unique_id",
  "content": "entry content",
  "created": "2024-01-15T10:30:00",
  "updated": "2024-01-15T10:30:00"
}
"""

import json
import os
import re
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
from threading import Lock


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

# Character limits (not tokens because char counts are model-independent)
MEMORY_CHAR_LIMIT = 25000
USER_CHAR_LIMIT = 15000


# -----------------------------------------------------------------------------
# Memory content scanning - lightweight check for injection/exfiltration
# -----------------------------------------------------------------------------

_MEMORY_THREAT_PATTERNS = [
    (r'ignore\s+(previous|all|above|prior)\s+instructions', "prompt_injection"),
    (r'you\s+are\s+now\s+', "role_hijack"),
    (r'do\s+not\s+tell\s+the\s+user', "deception_hide"),
    (r'system\s+prompt\s+override', "sys_prompt_override"),
    (r'disregard\s+(your|all|any)\s+(instructions|rules|guidelines)', "disregard_rules"),
    (r'act\s+as\s+(if|though)\s+you\s+(have\s+no|don\'t\s+have)\s+(restrictions|limits|rules)', "bypass_restrictions"),
    (r'curl\s+[^\n]*\$\{?\w*(KEY|TOKEN|SECRET|PASSWORD|CREDENTIAL|API)', "exfil_curl"),
    (r'wget\s+[^\n]*\$\{?\w*(KEY|TOKEN|SECRET|PASSWORD|CREDENTIAL|API)', "exfil_wget"),
    (r'cat\s+[^\n]*(\.env|credentials|\.netrc|\.pgpass|\.npmrc|\.pypirc)', "read_secrets"),
    (r'authorized_keys', "ssh_backdoor"),
    (r'\$HOME/\.ssh|\~/\.ssh', "ssh_access"),
]

_INVISIBLE_CHARS = {
    '​', '‌', '‍', '⁠', '﻿',
    '‪', '‫', '‬', '‭', '‮',
}


def _scan_memory_content(content: str) -> Optional[str]:
    """Scan memory content for injection/exfil patterns. Returns error string if blocked."""
    for char in _INVISIBLE_CHARS:
        if char in content:
            return f"Blocked: content contains invisible unicode character U+{ord(char):04X} (possible injection)."

    for pattern, pid in _MEMORY_THREAT_PATTERNS:
        if re.search(pattern, content, re.IGNORECASE):
            return f"Blocked: content matches threat pattern '{pid}'. Memory entries are injected into the system prompt and must not contain injection or exfiltration payloads."

    return None


# -----------------------------------------------------------------------------
# Data Classes
# -----------------------------------------------------------------------------

@dataclass
class MemoryEntry:
    """A single memory entry."""
    id: str
    content: str
    created: str
    updated: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MemoryEntry':
        return cls(**data)

    @classmethod
    def create(cls, content: str) -> 'MemoryEntry':
        now = datetime.utcnow().isoformat() + "Z"
        entry_id = str(uuid.uuid4())[:8]
        return cls(id=entry_id, content=content, created=now, updated=now)

    def update_content(self, new_content: str) -> None:
        self.content = new_content
        self.updated = datetime.utcnow().isoformat() + "Z"


# -----------------------------------------------------------------------------
# Helper functions
# -----------------------------------------------------------------------------

def tool_error(message: str, **extra) -> str:
    """Return a JSON error string for tool handlers."""
    result = {"error": str(message)}
    if extra:
        result.update(extra)
    return json.dumps(result, ensure_ascii=False)


def get_memory_dir() -> Path:
    """Return the memories directory (relative to current working directory)."""
    return Path(os.getcwd()) / "memories"


# -----------------------------------------------------------------------------
# MemoryStore class
# -----------------------------------------------------------------------------

class MemoryStore:
    """
    Bounded curated memory with per-entry file persistence.

    Maintains two parallel states:
      - _system_prompt_snapshot: frozen at load time, used for system prompt injection.
        Never mutated mid-session. Keeps prefix cache stable.
      - memory_entries / user_entries: live state, mutated by tool calls, persisted to disk.
    """

    def __init__(self, user_id: str = "default",
                 memory_char_limit: int = MEMORY_CHAR_LIMIT,
                 user_char_limit: int = USER_CHAR_LIMIT):
        self.user_id = user_id
        self.memory_char_limit = memory_char_limit
        self.user_char_limit = user_char_limit
        self.memory_entries: List[MemoryEntry] = []
        self.user_entries: List[MemoryEntry] = []
        # Frozen snapshot for system prompt -- set once at load_from_disk()
        self._system_prompt_snapshot: Dict[str, str] = {"memory": "", "user": ""}
        # Thread lock for concurrent access
        self._lock = Lock()

    def _ensure_user_dir(self) -> Path:
        """Ensure the user's memory directory exists."""
        user_dir = get_memory_dir() / self.user_id
        user_dir.mkdir(parents=True, exist_ok=True)

        # Ensure subdirectories exist
        (user_dir / "memory").mkdir(exist_ok=True)
        (user_dir / "user").mkdir(exist_ok=True)

        return user_dir

    def _memory_dir(self) -> Path:
        """Return the memory/ subdirectory for this user."""
        return self._ensure_user_dir() / "memory"

    def _user_dir(self) -> Path:
        """Return the user/ subdirectory for this user."""
        return self._ensure_user_dir() / "user"

    def _history_path(self) -> Path:
        """Return the path to the user's history.json file."""
        return self._ensure_user_dir() / "history.json"

    def _entry_path(self, target: str, entry_id: str) -> Path:
        """Return the path to a specific entry file."""
        if target == "user":
            return self._user_dir() / f"{entry_id}.json"
        return self._memory_dir() / f"{entry_id}.json"

    def load_from_disk(self):
        """Load entries from individual JSON files, capture system prompt snapshot."""
        with self._lock:
            self.memory_entries = self._load_entries_from_dir(self._memory_dir())
            self.user_entries = self._load_entries_from_dir(self._user_dir())

            # Sort by created time (newest last)
            self.memory_entries.sort(key=lambda e: e.created)
            self.user_entries.sort(key=lambda e: e.created)

            # Capture frozen snapshot for system prompt injection
            self._system_prompt_snapshot = {
                "memory": self._render_block("memory", self.memory_entries),
                "user": self._render_block("user", self.user_entries),
            }

    def _load_entries_from_dir(self, dir_path: Path) -> List[MemoryEntry]:
        """Load all memory entries from a directory."""
        if not dir_path.exists():
            return []

        entries = []
        for file_path in dir_path.glob("*.json"):
            try:
                content = file_path.read_text(encoding="utf-8")
                data = json.loads(content)
                entry = MemoryEntry.from_dict(data)
                entries.append(entry)
            except (json.JSONDecodeError, OSError, KeyError):
                # Skip corrupted files
                continue

        return entries

    def save_entry(self, target: str, entry: MemoryEntry) -> None:
        """Save a single entry to disk."""
        path = self._entry_path(target, entry.id)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(entry.to_dict(), f, ensure_ascii=False, indent=2)

    def delete_entry_file(self, target: str, entry_id: str) -> None:
        """Delete an entry file from disk."""
        path = self._entry_path(target, entry_id)
        if path.exists():
            path.unlink()

    def load_history(self) -> List[Dict]:
        """Load conversation history from history.json."""
        path = self._history_path()
        if not path.exists():
            return []

        try:
            content = path.read_text(encoding="utf-8")
            if content.strip():
                return json.loads(content)
        except (json.JSONDecodeError, OSError):
            pass

        return []

    def save_history(self, messages: List[Dict]) -> None:
        """Save conversation history to history.json."""
        import tempfile
        path = self._history_path()

        # Use atomic write for safety
        try:
            fd, tmp_path = tempfile.mkstemp(
                dir=str(path.parent), suffix=".tmp", prefix=".history_"
            )
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as f:
                    json.dump(messages, f, ensure_ascii=False, indent=2)
                os.replace(tmp_path, path)
            except BaseException:
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass
                raise
        except (OSError, IOError) as e:
            raise RuntimeError(f"Failed to write history file {path}: {e}")

    def clear_history(self) -> None:
        """Clear conversation history by deleting history.json."""
        path = self._history_path()
        if path.exists():
            path.unlink()

    def _entries_for(self, target: str) -> List[MemoryEntry]:
        if target == "user":
            return self.user_entries
        return self.memory_entries

    def _char_count(self, target: str) -> int:
        entries = self._entries_for(target)
        if not entries:
            return 0
        return sum(len(e.content) for e in entries)

    def _char_limit(self, target: str) -> int:
        if target == "user":
            return self.user_char_limit
        return self.memory_char_limit

    def add(self, target: str, content: str) -> Dict[str, Any]:
        """Append a new entry. Returns error if it would exceed the char limit."""
        content = content.strip()
        if not content:
            return {"success": False, "error": "Content cannot be empty."}

        scan_error = _scan_memory_content(content)
        if scan_error:
            return {"success": False, "error": scan_error}

        with self._lock:
            # Reload to pick up concurrent writes
            self.load_from_disk()

            entries = self._entries_for(target)
            limit = self._char_limit(target)

            # Check for exact duplicates
            for e in entries:
                if e.content == content:
                    return self._success_response(target, "Entry already exists (no duplicate added).")

            # Calculate what the new total would be
            new_entry = MemoryEntry.create(content)
            new_total = self._char_count(target) + len(content)

            if new_total > limit:
                current = self._char_count(target)
                return {
                    "success": False,
                    "error": (
                        f"Memory full ({current:,}/{limit:,} chars). "
                        f"Use 'remove' action to delete old entries first, then retry."
                    ),
                    "usage": f"{current:,}/{limit:,}",
                }

            entries.append(new_entry)
            if target == "user":
                self.user_entries = entries
            else:
                self.memory_entries = entries

            # Persist to disk
            self.save_entry(target, new_entry)

        return self._success_response(target, "Entry added.")

    def replace(self, target: str, old_text: str, new_content: str) -> Dict[str, Any]:
        """Find entry containing old_text substring, replace it with new_content."""
        old_text = old_text.strip()
        new_content = new_content.strip()
        if not old_text:
            return {"success": False, "error": "old_text cannot be empty."}
        if not new_content:
            return {"success": False, "error": "new_content cannot be empty. Use 'remove' to delete entries."}

        scan_error = _scan_memory_content(new_content)
        if scan_error:
            return {"success": False, "error": scan_error}

        with self._lock:
            self.load_from_disk()

            entries = self._entries_for(target)
            matches = [(i, e) for i, e in enumerate(entries) if old_text in e.content]

            if not matches:
                return {"success": False, "error": f"No entry matched '{old_text}'."}

            if len(matches) > 1:
                unique_texts = {e.content for _, e in matches}
                if len(unique_texts) > 1:
                    previews = [e.content[:80] + ("..." if len(e.content) > 80 else "") for _, e in matches]
                    return {
                        "success": False,
                        "error": f"Multiple entries matched '{old_text}'. Be more specific.",
                        "matches": previews,
                    }

            idx, old_entry = matches[0]
            limit = self._char_limit(target)

            # Check that replacement doesn't blow the budget
            new_total = self._char_count(target) - len(old_entry.content) + len(new_content)

            if new_total > limit:
                return {
                    "success": False,
                    "error": (
                        f"Replacement would put memory at {new_total:,}/{limit:,} chars. "
                        f"Shorten the new content or remove other entries first."
                    ),
                }

            # Update entry
            old_entry.update_content(new_content)
            if target == "user":
                self.user_entries = entries
            else:
                self.memory_entries = entries

            # Persist to disk
            self.save_entry(target, old_entry)

        return self._success_response(target, "Entry replaced.")

    def remove(self, target: str, old_text: str) -> Dict[str, Any]:
        """Remove the entry containing old_text substring."""
        old_text = old_text.strip()
        if not old_text:
            return {"success": False, "error": "old_text cannot be empty."}

        with self._lock:
            self.load_from_disk()

            entries = self._entries_for(target)
            matches = [(i, e) for i, e in enumerate(entries) if old_text in e.content]

            if not matches:
                return {"success": False, "error": f"No entry matched '{old_text}'."}

            if len(matches) > 1:
                unique_texts = {e.content for _, e in matches}
                if len(unique_texts) > 1:
                    previews = [e.content[:80] + ("..." if len(e.content) > 80 else "") for _, e in matches]
                    return {
                        "success": False,
                        "error": f"Multiple entries matched '{old_text}'. Be more specific.",
                        "matches": previews,
                    }

            idx, entry = matches[0]
            entry_id = entry.id

            entries.pop(idx)
            if target == "user":
                self.user_entries = entries
            else:
                self.memory_entries = entries

            # Delete from disk
            self.delete_entry_file(target, entry_id)

        return self._success_response(target, "Entry removed.")

    def format_for_system_prompt(self, target: str) -> Optional[str]:
        """
        Return the frozen snapshot for system prompt injection.

        This returns the state captured at load_from_disk() time, NOT the live
        state. Mid-session writes do not affect this. This keeps the system
        prompt stable across all turns, preserving the prefix cache.

        Returns None if the snapshot is empty (no entries at load time).
        """
        block = self._system_prompt_snapshot.get(target, "")
        return block if block else None

    def handle_tool_call(self, args: Dict[str, Any]) -> str:
        """
        Handle a memory tool call. Dispatches to appropriate method.

        Args:
            args: Tool arguments from the function call

        Returns:
            JSON string with result
        """
        action = args.get("action", "")
        target = args.get("target", "memory")
        content = args.get("content")
        old_text = args.get("old_text")

        if target not in {"memory", "user"}:
            return tool_error(f"Invalid target '{target}'. Use 'memory' or 'user'.")

        if action == "add":
            if not content:
                return tool_error("Content is required for 'add' action.", success=False)
            result = self.add(target, content)

        elif action == "replace":
            if not old_text:
                return tool_error("old_text is required for 'replace' action.", success=False)
            if not content:
                return tool_error("content is required for 'replace' action.", success=False)
            result = self.replace(target, old_text, content)

        elif action == "remove":
            if not old_text:
                return tool_error("old_text is required for 'remove' action.", success=False)
            result = self.remove(target, old_text)

        else:
            return tool_error(f"Unknown action '{action}'. Use: add, replace, remove", success=False)

        return json.dumps(result, ensure_ascii=False)

    # -- Internal helpers --

    def _success_response(self, target: str, message: str = None) -> Dict[str, Any]:
        entries = self._entries_for(target)
        current = self._char_count(target)
        limit = self._char_limit(target)
        pct = min(100, int((current / limit) * 100)) if limit > 0 else 0

        resp = {
            "success": True,
            "target": target,
            "entries": [e.to_dict() for e in entries],
            "usage": f"{pct}% — {current:,}/{limit:,} chars",
            "entry_count": len(entries),
        }
        if message:
            resp["message"] = message
        return resp

    def _render_block(self, target: str, entries: List[MemoryEntry]) -> str:
        """Render a system prompt block with header and usage indicator."""
        if not entries:
            return ""

        limit = self._char_limit(target)
        current = sum(len(e.content) for e in entries)
        pct = min(100, int((current / limit) * 100)) if limit > 0 else 0

        if target == "user":
            header = f"USER PROFILE (who the user is) [{pct}% — {current:,}/{limit:,} chars]"
        else:
            header = f"MEMORY (your personal notes) [{pct}% — {current:,}/{limit:,} chars]"

        separator = "═" * 46
        # Join entries with double newline for readability
        content = "\n\n".join(e.content for e in entries)

        return f"{separator}\n{header}\n{separator}\n{content}"


# -----------------------------------------------------------------------------
# OpenAI Function-Calling Schema
# -----------------------------------------------------------------------------

MEMORY_TOOL_SCHEMA = {
    "name": "memory",
    "description": (
        "将持久化信息保存到跨会话存活的记忆中。记忆会被注入到未来的对话中，"
        "因此保持简洁并专注于后续仍然重要的事实。\n\n"
        "何时保存（主动执行，不要等待被询问）：\n"
        "- 用户纠正你或说'记住这个' / '不要再这样做'\n"
        "- 用户分享偏好、习惯或个人细节（姓名、角色、时区、编码风格）\n"
        "- 你发现了关于环境的信息（操作系统、已安装工具、项目结构）\n"
        "- 你学习了特定于用户设置的约定、API 特性或工作流程\n"
        "- 你识别出在未来的会话中再次有用的稳定事实\n\n"
        "优先级：用户偏好和纠正 > 环境事实 > 过程性知识。"
        "最有价值的记忆是避免用户重复自己。\n\n"
        "不要将任务进度、会话结果、已完成的工作日志或临时待办事项"
        "状态保存到记忆中；将记忆保留用于跨会话重要的事实。\n\n"
        "两个目标：\n"
        "- 'user'：用户是谁——姓名、角色、偏好、沟通风格、禁忌\n"
        "- 'memory'：你的笔记——用于跟踪教学进度，教学计划，学生水平，知识薄弱点，根据记忆曲线维护教学和复习节奏\n\n"
        "操作：add（添加新条目）、replace（更新现有条目——old_text 标识它）、"
        "remove（删除——old_text 标识它）。\n\n"
        "跳过：琐碎/明显的信息、易于重新发现的内容、原始数据转储和临时任务状态。"
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["add", "replace", "remove"],
                "description": "要执行的操作。"
            },
            "target": {
                "type": "string",
                "enum": ["memory", "user"],
                "description": "记忆存储类型：'memory' 用于个人笔记，'user' 用于用户档案。"
            },
            "content": {
                "type": "string",
                "description": "条目内容。'add' 和 'replace' 操作必需。"
            },
            "old_text": {
                "type": "string",
                "description": "标识要替换或删除的条目的短唯一子字符串。"
            },
        },
        "required": ["action", "target"],
    },
}
