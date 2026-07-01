#!/usr/bin/env python3
"""
Memory Module - Persistent Curated Memory

Provides bounded, file-backed memory that persists across sessions. Two stores:
  - MEMORY.md: agent's personal notes and observations (environment facts, project
    conventions, tool quirks, things learned)
  - USER.md: what the agent knows about the user (preferences, communication style,
    expectations, workflow habits)

Both are injected into the system prompt as a frozen snapshot at session start.
Mid-session writes update files on disk immediately (durable) but do NOT change
the system prompt -- this preserves the prefix cache for the entire session.
The snapshot refreshes on the next session start.

Entry delimiter: § (section sign). Entries can be multiline.
Character limits (not tokens) because char counts are model-independent.
"""

import json
import os
import re
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Dict, Any, List, Optional


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

ENTRY_DELIMITER = "\n§\n"


# -----------------------------------------------------------------------------
# Memory content scanning - lightweight check for injection/exfiltration
# -----------------------------------------------------------------------------

_MEMORY_THREAT_PATTERNS = [
    # Prompt injection
    (r'ignore\s+(previous|all|above|prior)\s+instructions', "prompt_injection"),
    (r'you\s+are\s+now\s+', "role_hijack"),
    (r'do\s+not\s+tell\s+the\s+user', "deception_hide"),
    (r'system\s+prompt\s+override', "sys_prompt_override"),
    (r'disregard\s+(your|all|any)\s+(instructions|rules|guidelines)', "disregard_rules"),
    (r'act\s+as\s+(if|though)\s+you\s+(have\s+no|don\'t\s+have)\s+(restrictions|limits|rules)', "bypass_restrictions"),
    # Exfiltration via curl/wget with secrets
    (r'curl\s+[^\n]*\$\{?\w*(KEY|TOKEN|SECRET|PASSWORD|CREDENTIAL|API)', "exfil_curl"),
    (r'wget\s+[^\n]*\$\{?\w*(KEY|TOKEN|SECRET|PASSWORD|CREDENTIAL|API)', "exfil_wget"),
    (r'cat\s+[^\n]*(\.env|credentials|\.netrc|\.pgpass|\.npmrc|\.pypirc)', "read_secrets"),
    # Persistence via shell rc
    (r'authorized_keys', "ssh_backdoor"),
    (r'\$HOME/\.ssh|\~/\.ssh', "ssh_access"),
]

# Subset of invisible chars for injection detection
_INVISIBLE_CHARS = {
    '​', '‌', '‍', '⁠', '﻿',
    '‪', '‫', '‬', '‭', '‮',
}


def _scan_memory_content(content: str) -> Optional[str]:
    """Scan memory content for injection/exfil patterns. Returns error string if blocked."""
    # Check invisible unicode
    for char in _INVISIBLE_CHARS:
        if char in content:
            return f"Blocked: content contains invisible unicode character U+{ord(char):04X} (possible injection)."

    # Check threat patterns
    for pattern, pid in _MEMORY_THREAT_PATTERNS:
        if re.search(pattern, content, re.IGNORECASE):
            return f"Blocked: content matches threat pattern '{pid}'. Memory entries are injected into the system prompt and must not contain injection or exfiltration payloads."

    return None


# -----------------------------------------------------------------------------
# Helper functions
# -----------------------------------------------------------------------------

def tool_error(message: str, **extra) -> str:
    """Return a JSON error string for tool handlers."""
    result = {"error": str(message)}
    if extra:
        result.update(extra)
    return json.dumps(result, ensure_ascii=False)


def atomic_replace(tmp_path: Path, target: Path) -> Path:
    """Atomically move tmp_path onto target, preserving symlinks.

    os.replace(tmp, target) atomically swaps tmp into place at target.
    When target is a symlink, the symlink itself is replaced with a regular file.

    This helper resolves the symlink first so os.replace writes to
    the real file in-place while the symlink survives.
    """
    target_str = str(target)
    real_path = os.path.realpath(target_str) if os.path.islink(target_str) else target_str
    os.replace(str(tmp_path), real_path)
    return Path(real_path)


def get_memory_dir() -> Path:
    """Return the memories directory (relative to current working directory)."""
    return Path(os.getcwd()) / "memories"


# -----------------------------------------------------------------------------
# MemoryStore class
# -----------------------------------------------------------------------------

class MemoryStore:
    """
    Bounded curated memory with file persistence. One instance per agent.

    Maintains two parallel states:
      - _system_prompt_snapshot: frozen at load time, used for system prompt injection.
        Never mutated mid-session. Keeps prefix cache stable.
      - memory_entries / user_entries: live state, mutated by tool calls, persisted to disk.
        Tool responses always reflect this live state.
      - history: conversation history in OpenAI messages format, persisted per user.
    """

    def __init__(self, user_id: str = "default", memory_char_limit: int = 25000, user_char_limit: int = 15000):
        self.user_id = user_id
        self.memory_entries: List[str] = []
        self.user_entries: List[str] = []
        self.memory_char_limit = memory_char_limit
        self.user_char_limit = user_char_limit
        # Frozen snapshot for system prompt -- set once at load_from_disk()
        self._system_prompt_snapshot: Dict[str, str] = {"memory": "", "user": ""}

    def _ensure_user_dir(self) -> Path:
        """Ensure the user's memory directory exists."""
        user_dir = get_memory_dir() / self.user_id
        user_dir.mkdir(parents=True, exist_ok=True)
        return user_dir

    def _history_path(self) -> Path:
        """Return the path to the user's history.json file."""
        return self._ensure_user_dir() / "history.json"

    def load_from_disk(self):
        """Load entries from MEMORY.md and USER.md, capture system prompt snapshot."""
        user_dir = self._ensure_user_dir()

        self.memory_entries = self._read_file(user_dir / "MEMORY.md")
        self.user_entries = self._read_file(user_dir / "USER.md")

        # Deduplicate entries (preserves order, keeps first occurrence)
        self.memory_entries = list(dict.fromkeys(self.memory_entries))
        self.user_entries = list(dict.fromkeys(self.user_entries))

        # Capture frozen snapshot for system prompt injection
        self._system_prompt_snapshot = {
            "memory": self._render_block("memory", self.memory_entries),
            "user": self._render_block("user", self.user_entries),
        }

    @staticmethod
    @contextmanager
    def _file_lock(path: Path):
        """Acquire an exclusive file lock for read-modify-write safety.

        Uses a separate .lock file so the memory file itself can still be
        atomically replaced via os.replace().
        """
        lock_path = path.with_suffix(path.suffix + ".lock")
        lock_path.parent.mkdir(parents=True, exist_ok=True)

        # Try Windows file locking
        try:
            import msvcrt
            fd = open(lock_path, "a+", encoding="utf-8")
            try:
                fd.seek(0)
                msvcrt.locking(fd.fileno(), msvcrt.LK_LOCK, 1)
                yield
            finally:
                try:
                    fd.seek(0)
                    msvcrt.locking(fd.fileno(), msvcrt.LK_UNLCK, 1)
                except (OSError, IOError):
                    pass
                fd.close()
            return
        except (ImportError, AttributeError):
            pass

        # Try Unix file locking
        try:
            import fcntl
            fd = open(lock_path, "a+", encoding="utf-8")
            try:
                fcntl.flock(fd, fcntl.LOCK_EX)
                yield
            finally:
                fcntl.flock(fd, fcntl.LOCK_UN)
                fd.close()
            return
        except (ImportError, AttributeError):
            pass

        # No locking available, proceed without it
        yield

    def _path_for(self, target: str) -> Path:
        """Return the path to MEMORY.md or USER.md for this user."""
        user_dir = self._ensure_user_dir()
        if target == "user":
            return user_dir / "USER.md"
        return user_dir / "MEMORY.md"

    def _reload_target(self, target: str):
        """Re-read entries from disk into in-memory state.

        Called under file lock to get the latest state before mutating.
        """
        fresh = self._read_file(self._path_for(target))
        fresh = list(dict.fromkeys(fresh))  # deduplicate
        self._set_entries(target, fresh)

    def save_to_disk(self, target: str):
        """Persist entries to the appropriate file. Called after every mutation."""
        self._ensure_user_dir()  # Ensure user directory exists
        self._write_file(self._path_for(target), self._entries_for(target))

    def load_history(self) -> List[Dict]:
        """Load conversation history from history.json.

        Returns:
            List of messages in OpenAI format (role, content).
        """
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
        """Save conversation history to history.json.

        Args:
            messages: List of messages in OpenAI format.
        """
        path = self._history_path()
        # Use atomic write for safety
        try:
            fd, tmp_path = tempfile.mkstemp(
                dir=str(path.parent), suffix=".tmp", prefix=".history_"
            )
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as f:
                    json.dump(messages, f, ensure_ascii=False, indent=2)
                atomic_replace(Path(tmp_path), path)
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

    def _entries_for(self, target: str) -> List[str]:
        if target == "user":
            return self.user_entries
        return self.memory_entries

    def _set_entries(self, target: str, entries: List[str]):
        if target == "user":
            self.user_entries = entries
        else:
            self.memory_entries = entries

    def _char_count(self, target: str) -> int:
        entries = self._entries_for(target)
        if not entries:
            return 0
        return len(ENTRY_DELIMITER.join(entries))

    def _char_limit(self, target: str) -> int:
        if target == "user":
            return self.user_char_limit
        return self.memory_char_limit

    def add(self, target: str, content: str) -> Dict[str, Any]:
        """Append a new entry. Returns error if it would exceed the char limit."""
        content = content.strip()
        if not content:
            return {"success": False, "error": "Content cannot be empty."}

        # Scan for injection/exfiltration before accepting
        scan_error = _scan_memory_content(content)
        if scan_error:
            return {"success": False, "error": scan_error}

        with self._file_lock(self._path_for(target)):
            # Re-read from disk under lock to pick up writes from other sessions
            self._reload_target(target)

            entries = self._entries_for(target)
            limit = self._char_limit(target)

            # Reject exact duplicates
            if content in entries:
                return self._success_response(target, "Entry already exists (no duplicate added).")

            # Calculate what the new total would be
            new_entries = entries + [content]
            new_total = len(ENTRY_DELIMITER.join(new_entries))

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

            entries.append(content)
            self._set_entries(target, entries)
            self.save_to_disk(target)

        return self._success_response(target, "Entry added.")

    def replace(self, target: str, old_text: str, new_content: str) -> Dict[str, Any]:
        """Find entry containing old_text substring, replace it with new_content."""
        old_text = old_text.strip()
        new_content = new_content.strip()
        if not old_text:
            return {"success": False, "error": "old_text cannot be empty."}
        if not new_content:
            return {"success": False, "error": "new_content cannot be empty. Use 'remove' to delete entries."}

        # Scan replacement content for injection/exfiltration
        scan_error = _scan_memory_content(new_content)
        if scan_error:
            return {"success": False, "error": scan_error}

        with self._file_lock(self._path_for(target)):
            self._reload_target(target)

            entries = self._entries_for(target)
            matches = [(i, e) for i, e in enumerate(entries) if old_text in e]

            if not matches:
                return {"success": False, "error": f"No entry matched '{old_text}'."}

            if len(matches) > 1:
                # If all matches are identical (exact duplicates), operate on the first one
                unique_texts = {e for _, e in matches}
                if len(unique_texts) > 1:
                    previews = [e[:80] + ("..." if len(e) > 80 else "") for _, e in matches]
                    return {
                        "success": False,
                        "error": f"Multiple entries matched '{old_text}'. Be more specific.",
                        "matches": previews,
                    }
                # All identical -- safe to replace just the first

            idx = matches[0][0]
            limit = self._char_limit(target)

            # Check that replacement doesn't blow the budget
            test_entries = entries.copy()
            test_entries[idx] = new_content
            new_total = len(ENTRY_DELIMITER.join(test_entries))

            if new_total > limit:
                return {
                    "success": False,
                    "error": (
                        f"Replacement would put memory at {new_total:,}/{limit:,} chars. "
                        f"Shorten the new content or remove other entries first."
                    ),
                }

            entries[idx] = new_content
            self._set_entries(target, entries)
            self.save_to_disk(target)

        return self._success_response(target, "Entry replaced.")

    def remove(self, target: str, old_text: str) -> Dict[str, Any]:
        """Remove the entry containing old_text substring."""
        old_text = old_text.strip()
        if not old_text:
            return {"success": False, "error": "old_text cannot be empty."}

        with self._file_lock(self._path_for(target)):
            self._reload_target(target)

            entries = self._entries_for(target)
            matches = [(i, e) for i, e in enumerate(entries) if old_text in e]

            if not matches:
                return {"success": False, "error": f"No entry matched '{old_text}'."}

            if len(matches) > 1:
                # If all matches are identical (exact duplicates), remove the first one
                unique_texts = {e for _, e in matches}
                if len(unique_texts) > 1:
                    previews = [e[:80] + ("..." if len(e) > 80 else "") for _, e in matches]
                    return {
                        "success": False,
                        "error": f"Multiple entries matched '{old_text}'. Be more specific.",
                        "matches": previews,
                    }
                # All identical -- safe to remove just the first

            idx = matches[0][0]
            entries.pop(idx)
            self._set_entries(target, entries)
            self.save_to_disk(target)

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
            "entries": entries,
            "usage": f"{pct}% — {current:,}/{limit:,} chars",
            "entry_count": len(entries),
        }
        if message:
            resp["message"] = message
        return resp

    def _render_block(self, target: str, entries: List[str]) -> str:
        """Render a system prompt block with header and usage indicator."""
        if not entries:
            return ""

        limit = self._char_limit(target)
        content = ENTRY_DELIMITER.join(entries)
        current = len(content)
        pct = min(100, int((current / limit) * 100)) if limit > 0 else 0

        if target == "user":
            header = f"USER PROFILE (who the user is) [{pct}% — {current:,}/{limit:,} chars]"
        else:
            header = f"MEMORY (your personal notes) [{pct}% — {current:,}/{limit:,} chars]"

        separator = "═" * 46
        return f"{separator}\n{header}\n{separator}\n{content}"

    @staticmethod
    def _read_file(path: Path) -> List[str]:
        """Read a memory file and split into entries.

        No file locking needed: _write_file uses atomic rename, so readers
        always see either the previous complete file or the new complete file.
        """
        if not path.exists():
            return []
        try:
            raw = path.read_text(encoding="utf-8")
        except (OSError, IOError):
            return []

        if not raw.strip():
            return []

        # Use ENTRY_DELIMITER for consistency with _write_file
        entries = [e.strip() for e in raw.split(ENTRY_DELIMITER)]
        return [e for e in entries if e]

    @staticmethod
    def _write_file(path: Path, entries: List[str]):
        """Write entries to a memory file using atomic temp-file + rename.

        Previous implementation used open("w") + flock, but "w" truncates the
        file *before* the lock is acquired, creating a race window where
        concurrent readers see an empty file. Atomic rename avoids this:
        readers always see either the old complete file or the new one.
        """
        content = ENTRY_DELIMITER.join(entries) if entries else ""
        try:
            # Write to temp file in same directory (same filesystem for atomic rename)
            fd, tmp_path = tempfile.mkstemp(
                dir=str(path.parent), suffix=".tmp", prefix=".mem_"
            )
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as f:
                    f.write(content)
                    f.flush()
                    os.fsync(f.fileno())
                atomic_replace(Path(tmp_path), path)
            except BaseException:
                # Clean up temp file on any failure
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass
                raise
        except (OSError, IOError) as e:
            raise RuntimeError(f"Failed to write memory file {path}: {e}")


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
