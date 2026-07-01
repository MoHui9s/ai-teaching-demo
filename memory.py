#!/usr/bin/env python3
"""
Memory Module - Single-file persistent memory per user.

Per-user directory: memories/{user_id}/
  - MEMORY.md: agent's personal notes (§-delimited entries)
  - USER.md: user profile (§-delimited entries)
  - history.json: conversation history

Entry delimiter: § (section sign). Entries can be multiline.
Simple, debuggable, works.
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
DEFAULT_MEMORY_CHAR_LIMIT = 25000
DEFAULT_USER_CHAR_LIMIT = 15000


# -----------------------------------------------------------------------------
# Memory content scanning
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

_INVISIBLE_CHARS = {'​', '‌', '‍', '⁠', '﻿', '‪', '‫', '‬', '‭', '‮',}


def _scan_memory_content(content: str) -> Optional[str]:
    for char in _INVISIBLE_CHARS:
        if char in content:
            return f"Blocked: content contains invisible unicode character U+{ord(char):04X}."
    for pattern, pid in _MEMORY_THREAT_PATTERNS:
        if re.search(pattern, content, re.IGNORECASE):
            return f"Blocked: content matches threat pattern '{pid}'."
    return None


def _atomic_replace(tmp_path: Path, target: Path) -> Path:
    target_str = str(target)
    real_path = os.path.realpath(target_str) if os.path.islink(target_str) else target_str
    os.replace(str(tmp_path), real_path)
    return Path(real_path)


def tool_error(message: str, **extra) -> str:
    result = {"error": str(message), "success": False}
    result.update(extra)
    return json.dumps(result, ensure_ascii=False)


# -----------------------------------------------------------------------------
# MemoryStore
# -----------------------------------------------------------------------------

class MemoryStore:
    """Per-user file-backed memory: MEMORY.md + USER.md + history.json"""

    def __init__(self, user_id: str = "default",
                 memory_char_limit: int = DEFAULT_MEMORY_CHAR_LIMIT,
                 user_char_limit: int = DEFAULT_USER_CHAR_LIMIT):
        self.user_id = user_id
        self.memory_char_limit = memory_char_limit
        self.user_char_limit = user_char_limit
        self.memory_entries: List[str] = []
        self.user_entries: List[str] = []
        self._system_prompt_snapshot: Dict[str, str] = {"memory": "", "user": ""}
        self.load_from_disk()

    # -- Path helpers --

    def _base_dir(self) -> Path:
        return Path(os.getcwd()) / "memories" / self.user_id

    def _path_for(self, target: str) -> Path:
        if target == "user":
            return self._base_dir() / "USER.md"
        return self._base_dir() / "MEMORY.md"

    def _history_path(self) -> Path:
        return self._base_dir() / "history.json"

    # -- Entry helpers --

    def _entries_for(self, target: str) -> List[str]:
        return self.user_entries if target == "user" else self.memory_entries

    def _set_entries(self, target: str, entries: List[str]):
        if target == "user":
            self.user_entries = entries
        else:
            self.memory_entries = entries

    def _char_limit(self, target: str) -> int:
        return self.user_char_limit if target == "user" else self.memory_char_limit

    def _char_count(self, target: str) -> int:
        entries = self._entries_for(target)
        return len(ENTRY_DELIMITER.join(entries)) if entries else 0

    # -- File I/O --

    def load_from_disk(self):
        self._base_dir().mkdir(parents=True, exist_ok=True)
        self.memory_entries = self._read_file(self._path_for("memory"))
        self.user_entries = self._read_file(self._path_for("user"))
        self.memory_entries = list(dict.fromkeys(self.memory_entries))
        self.user_entries = list(dict.fromkeys(self.user_entries))
        self._system_prompt_snapshot = {
            "memory": self._render_block("memory", self.memory_entries),
            "user": self._render_block("user", self.user_entries),
        }

    @staticmethod
    def _read_file(path: Path) -> List[str]:
        if not path.exists():
            return []
        try:
            raw = path.read_text(encoding="utf-8")
        except (OSError, IOError):
            return []
        if not raw.strip():
            return []
        return [e.strip() for e in raw.split(ENTRY_DELIMITER) if e.strip()]

    @staticmethod
    def _write_file(path: Path, entries: List[str]):
        content = ENTRY_DELIMITER.join(entries) if entries else ""
        fd, tmp_path = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp", prefix=".mem_")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(content)
                f.flush()
                os.fsync(f.fileno())
            _atomic_replace(Path(tmp_path), path)
        except BaseException:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise

    def _save_target(self, target: str):
        self._base_dir().mkdir(parents=True, exist_ok=True)
        self._write_file(self._path_for(target), self._entries_for(target))

    # -- Memory operations --

    def add(self, target: str, content: str) -> Dict[str, Any]:
        content = content.strip()
        if not content:
            return {"success": False, "error": "Content cannot be empty."}
        scan_err = _scan_memory_content(content)
        if scan_err:
            return {"success": False, "error": scan_err}

        entries = self._entries_for(target)
        limit = self._char_limit(target)

        if content in entries:
            return self._success(target, "Entry already exists.")

        new_total = len(ENTRY_DELIMITER.join(entries + [content]))
        if new_total > limit:
            current = self._char_count(target)
            return {"success": False, "error": f"Memory full ({current:,}/{limit:,} chars). Remove old entries first.", "usage": f"{current:,}/{limit:,}"}

        entries.append(content)
        self._set_entries(target, entries)
        self._save_target(target)
        return self._success(target, "Entry added.")

    def replace(self, target: str, old_text: str, new_content: str) -> Dict[str, Any]:
        old_text = old_text.strip()
        new_content = new_content.strip()
        if not old_text:
            return {"success": False, "error": "old_text cannot be empty."}
        if not new_content:
            return {"success": False, "error": "new_content cannot be empty."}
        scan_err = _scan_memory_content(new_content)
        if scan_err:
            return {"success": False, "error": scan_err}

        entries = self._entries_for(target)
        matches = [(i, e) for i, e in enumerate(entries) if old_text in e]

        if not matches:
            return {"success": False, "error": f"No entry matched '{old_text}'."}
        if len(matches) > 1:
            unique_texts = {e for _, e in matches}
            if len(unique_texts) > 1:
                previews = [e[:80] + ("..." if len(e) > 80 else "") for _, e in matches]
                return {"success": False, "error": f"Multiple entries matched. Be more specific.", "matches": previews}

        idx = matches[0][0]
        test = entries.copy()
        test[idx] = new_content
        if len(ENTRY_DELIMITER.join(test)) > self._char_limit(target):
            return {"success": False, "error": "Replacement exceeds char limit."}

        entries[idx] = new_content
        self._set_entries(target, entries)
        self._save_target(target)
        return self._success(target, "Entry replaced.")

    def remove(self, target: str, old_text: str) -> Dict[str, Any]:
        old_text = old_text.strip()
        if not old_text:
            return {"success": False, "error": "old_text cannot be empty."}

        entries = self._entries_for(target)
        matches = [(i, e) for i, e in enumerate(entries) if old_text in e]

        if not matches:
            return {"success": False, "error": f"No entry matched '{old_text}'."}
        if len(matches) > 1:
            unique_texts = {e for _, e in matches}
            if len(unique_texts) > 1:
                previews = [e[:80] + ("..." if len(e) > 80 else "") for _, e in matches]
                return {"success": False, "error": f"Multiple entries matched. Be more specific.", "matches": previews}

        entries.pop(matches[0][0])
        self._set_entries(target, entries)
        self._save_target(target)
        return self._success(target, "Entry removed.")

    def handle_tool_call(self, args: Dict[str, Any]) -> str:
        action = args.get("action", "")
        target = args.get("target", "memory")
        content = args.get("content")
        old_text = args.get("old_text")

        if target not in ("memory", "user"):
            return tool_error(f"Invalid target '{target}'.")

        if action == "add":
            if not content:
                return tool_error("Content required for add.")
            return json.dumps(self.add(target, content), ensure_ascii=False)
        elif action == "replace":
            if not old_text or not content:
                return tool_error("old_text and content required for replace.")
            return json.dumps(self.replace(target, old_text, content), ensure_ascii=False)
        elif action == "remove":
            if not old_text:
                return tool_error("old_text required for remove.")
            return json.dumps(self.remove(target, old_text), ensure_ascii=False)
        else:
            return tool_error(f"Unknown action '{action}'.")

    def format_for_system_prompt(self, target: str) -> Optional[str]:
        block = self._system_prompt_snapshot.get(target, "")
        return block if block else None

    # -- History management --

    def load_history(self) -> List[Dict]:
        path = self._history_path()
        if not path.exists():
            return []
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return data if isinstance(data, list) else []
        except (json.JSONDecodeError, OSError):
            return []

    def save_history(self, history: List[Dict]):
        self._base_dir().mkdir(parents=True, exist_ok=True)
        fd, tmp_path = tempfile.mkstemp(dir=str(self._base_dir()), suffix=".tmp", prefix=".hist_")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(history, f, ensure_ascii=False, indent=2)
                f.flush()
                os.fsync(f.fileno())
            _atomic_replace(Path(tmp_path), self._history_path())
        except BaseException:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise

    def clear_history(self):
        path = self._history_path()
        self._base_dir().mkdir(parents=True, exist_ok=True)
        self._write_file(path, [])

    # -- Internal --

    def _success(self, target: str, message: str = None) -> Dict[str, Any]:
        entries = self._entries_for(target)
        current = self._char_count(target)
        limit = self._char_limit(target)
        pct = min(100, int((current / limit) * 100)) if limit > 0 else 0
        return {
            "success": True,
            "target": target,
            "entries": entries,
            "usage": f"{pct}% — {current:,}/{limit:,} chars",
            "entry_count": len(entries),
            **({"message": message} if message else {}),
        }

    def _render_block(self, target: str, entries: List[str]) -> str:
        if not entries:
            return ""
        content = ENTRY_DELIMITER.join(entries)
        current = len(content)
        limit = self._char_limit(target)
        pct = min(100, int((current / limit) * 100)) if limit > 0 else 0
        hdr = "USER PROFILE" if target == "user" else "MEMORY"
        sep = "═" * 46
        return f"{sep}\n{hdr} [{pct}% — {current:,}/{limit:,} chars]\n{sep}\n{content}"


# -----------------------------------------------------------------------------
# Tool Schema
# -----------------------------------------------------------------------------

MEMORY_TOOL_SCHEMA = {
    "name": "memory",
    "description": (
        "Save durable information to persistent memory that survives across sessions. "
        "Memory is injected into future turns, so keep it compact and focused on facts "
        "that will still matter later.\n\n"
        "WHEN TO SAVE (do this proactively, don't wait to be asked):\n"
        "- User corrects you or says 'remember this' / 'don't do that again'\n"
        "- User shares a preference, habit, or personal detail (name, role, timezone, coding style)\n"
        "- You discover something about the environment (OS, installed tools, project structure)\n"
        "- You learn a convention, API quirk, or workflow specific to this user's setup\n"
        "- You identify a stable fact that will be useful again in future sessions\n\n"
        "PRIORITY: User preferences and corrections > environment facts > procedural knowledge.\n\n"
        "Do NOT save task progress, session outcomes, completed-work logs, or temporary TODO state.\n\n"
        "TWO TARGETS:\n"
        "- 'user': who the user is — name, role, preferences, communication style\n"
        "- 'memory': your notes — environment facts, project conventions, lessons learned\n\n"
        "ACTIONS: add (new entry), replace (update existing — old_text identifies it), "
        "remove (delete — old_text identifies it)."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["add", "replace", "remove"],
                "description": "The action to perform."
            },
            "target": {
                "type": "string",
                "enum": ["memory", "user"],
                "description": "Which store: 'memory' for your notes, 'user' for user profile."
            },
            "content": {
                "type": "string",
                "description": "Entry content. Required for 'add' and 'replace'."
            },
            "old_text": {
                "type": "string",
                "description": "Substring identifying entry to replace or remove."
            },
        },
        "required": ["action", "target"],
    },
}
