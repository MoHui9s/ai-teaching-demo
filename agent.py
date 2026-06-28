#!/usr/bin/env python

import requests
from dotenv import load_dotenv
import sys
import os
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Generator, Union, Any

# Import logging configuration
from logging_config import (
    setup_logging, get_logger, log_request, log_response,
    log_error, log_user_action, log_tool_call
)

# Windows 编码修复：在导入其他模块后立即设置
if sys.platform == "win32":
    try:
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    except Exception:
        pass

# 安全打印函数：处理编码问题
def safe_print(text):
    """安全打印，处理 Unicode 编码错误"""
    if text is None:
        return
    try:
        print(text)
    except UnicodeEncodeError:
        print(text.encode('ascii', 'replace').decode('ascii'))

load_dotenv(override=True)

# Import memory module
from memory import MemoryStore, MEMORY_TOOL_SCHEMA

# Configuration
MAX_CONTEXT_ROUNDS = int(os.getenv("MAX_CONTEXT_ROUNDS", "40"))
DEBUG = os.getenv("DEBUG", "").lower() in ("1", "true", "yes", "on")

# Logging configuration from environment
LOG_LEVEL = os.getenv("LOG_LEVEL", "DEBUG" if DEBUG else "INFO")
LOG_FILE = os.getenv("LOG_FILE", "true").lower() in ("1", "true", "yes", "on")

# Setup logging
logger = setup_logging(log_level=LOG_LEVEL, log_file=LOG_FILE)

# API Configuration
api_key = os.getenv("OPENAI_API_KEY") or os.getenv("ANTHROPIC_API_KEY")
base_url = os.getenv("OPENAI_BASE_URL") or os.getenv("ANTHROPIC_BASE_URL", "https://api.openai.com/v1")
MODEL = os.getenv("MODEL", os.getenv("MODEL_ID", "gpt-4o"))

# Ensure base_url ends with /chat/completions endpoint
if not base_url.endswith("/chat/completions"):
    if base_url.endswith("/"):
        chat_url = base_url + "chat/completions"
    elif base_url.endswith("/v3") or base_url.endswith("/v1"):
        chat_url = base_url + "/chat/completions"
    else:
        chat_url = base_url.rstrip("/") + "/chat/completions"
else:
    chat_url = base_url

# Tools
MEMORY_TOOL = {
    "type": "function",
    "function": MEMORY_TOOL_SCHEMA
}
TOOL = [MEMORY_TOOL]


# =============================================================================
# System prompt building
# =============================================================================

def get_base_personality():
    """基础人设（硬编码，极简抽象）"""
    return """你是一个通用人工智能助手，可以帮助用户完成各种任务。"""


def load_soul_md():
    """加载 SOUL.md（可选，用户自定义人格）"""
    soul_path = Path(os.getcwd()) / "SOUL.md"
    if soul_path.exists():
        try:
            content = soul_path.read_text(encoding="utf-8").strip()
            if content:
                return content
        except Exception:
            pass
    return None


def get_tools_guide():
    """工具使用说明（硬编码）"""
    return """## 可用工具

### memory
跨会话持久化信息，供未来参考。

**何时保存（主动进行，不要等用户要求）：**
- 用户纠正或说"记住这个"/"不要再那样做"
- 用户偏好、习惯或个人信息（姓名、角色、时区、编程风格）
- 环境发现（操作系统、已安装工具、项目结构）
- 约定、API 特点或工作流特定模式
- 对未来会话有用的稳定事实

**不要保存：**
- 任务进度、会话结果或临时待办状态
- 容易重新发现的琐碎/明显信息
- 原始数据

**目标：**
- user：用户是谁（偏好、沟通风格）
- memory：你的笔记（环境事实、项目约定、经验教训）"""


def get_working_directory():
    """工作目录信息（动态）"""
    return f"""## 工作目录

当前工作目录：`{os.getcwd()}`"""


def build_system_prompt(memory_store=None):
    """构建完整的系统提示"""
    parts = []
    parts.append(get_base_personality())

    soul_content = load_soul_md()
    if soul_content:
        parts.append(f"\n# 用户定义人格\n\n{soul_content}")

    parts.append(get_tools_guide())
    parts.append(get_working_directory())

    if memory_store:
        memory_block = memory_store.format_for_system_prompt("memory")
        if memory_block:
            parts.append(f"\n# 记忆\n\n{memory_block}")

        user_block = memory_store.format_for_system_prompt("user")
        if user_block:
            parts.append(f"\n{user_block}")

    return "\n\n".join(parts)


# =============================================================================
# History management
# =============================================================================

def limit_history_rounds(history: List[Dict], max_rounds: int) -> List[Dict]:
    """限制对话历史轮数"""
    if max_rounds <= 0:
        return history

    max_messages = max_rounds * 2
    if len(history) <= max_messages:
        return history

    result = []
    round_count = 0
    i = len(history) - 1

    while i >= 0 and round_count < max_rounds:
        if history[i].get("role") == "assistant":
            j = i
            while j >= 0:
                if history[j].get("role") in ["user", "system"]:
                    break
                j -= 1

            round_messages = history[j:i+1]
            for msg in reversed(round_messages):
                result.insert(0, msg)

            round_count += 1
            i = j - 1
        else:
            i -= 1

    return result


# =============================================================================
# HermesAgent class
# =============================================================================

class HermesAgent:
    """
    Hermes AI Agent with multi-user support and persistent memory.

    Each agent instance represents one user with:
    - Long-term memory (MEMORY.md, USER.md)
    - Short-term memory (history.json)
    """

    def __init__(self, user_id: str = "default"):
        """
        Initialize agent for a specific user.

        Args:
            user_id: User identifier for memory isolation
        """
        self.user_id = user_id
        self.memory_store = MemoryStore(user_id)
        self.memory_store.load_from_disk()
        self.history = self.memory_store.load_history()
        logger.debug(f"Initialized HermesAgent for user '{user_id}' with {len(self.history)} history messages")

    def _prepare_request(self, prompt: str, messages: List[Dict] = None):
        """
        Prepare API request for a user message.

        Args:
            prompt: User's input message
            messages: Optional custom messages list (for streaming reuse)

        Returns:
            Tuple of (headers, payload, messages_with_system)
        """
        if messages is None:
            # Add user message to history
            user_msg = {"role": "user", "content": prompt}
            self.history.append(user_msg)
            logger.debug(f"Added user message. Total history: {len(self.history)} messages")

        # Build system prompt
        system_content = build_system_prompt(self.memory_store)

        # Limit history rounds
        limited_history = limit_history_rounds(self.history, MAX_CONTEXT_ROUNDS)

        # Build messages for API
        messages_with_system = [
            {"role": "system", "content": system_content}
        ] + limited_history

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": MODEL,
            "messages": messages_with_system,
            "tools": TOOL,
            "max_tokens": 8000
        }

        logger.debug(f"API Request to {chat_url}")

        return headers, payload, messages_with_system

    def _handle_response_message(self, message: Dict[str, Any]) -> tuple[str, bool]:
        """
        Handle the assistant response message.

        Args:
            message: The assistant message from the API

        Returns:
            Tuple of (response_text, had_tool_calls)
        """
        # Build assistant message
        content_value = message.get("content")
        if content_value is None:
            content_value = ""
            logger.warning("Model returned null content")

        assistant_msg = {"role": "assistant", "content": content_value}

        if "tool_calls" in message and message["tool_calls"]:
            assistant_msg["tool_calls"] = []
            for tc in message["tool_calls"]:
                assistant_msg["tool_calls"].append({
                    "id": tc["id"],
                    "type": tc["type"],
                    "function": {
                        "name": tc["function"]["name"],
                        "arguments": tc["function"]["arguments"]
                    }
                })

        self.history.append(assistant_msg)

        # Handle tool calls
        if "tool_calls" in message and message["tool_calls"]:
            results = []
            for tc in message["tool_calls"]:
                func_name = tc["function"]["name"]
                func_args = json.loads(tc["function"]["arguments"])

                if func_name == "memory":
                    print(f"\033[35mMemory: {func_args.get('action', 'unknown')} -> {func_args.get('target', 'memory')}\033[0m")
                    result = self.memory_store.handle_tool_call(func_args)
                    print(result)
                    results.append({
                        "role": "tool",
                        "tool_call_id": tc["id"],
                        "content": result
                    })
                else:
                    error = json.dumps({"error": f"Unknown tool: {func_name}"})
                    print(f"\033[31m{error}\033[0m")
                    results.append({
                        "role": "tool",
                        "tool_call_id": tc["id"],
                        "content": error
                    })

            self.history.extend(results)
            # Continue loop for tool responses
            return self._continue_after_tools(), True

        # No tool calls, save and return
        self.memory_store.save_history(self.history)

        response_content = message.get("content") or ""
        if not response_content:
            return "# 注意：模型返回了空响应，请重试或检查 API 配置", False

        return response_content, False

    def chat(self, prompt: str) -> str:
        """
        Process a user message and return the assistant's response.

        Args:
            prompt: User's input message

        Returns:
            Assistant's text response
        """
        headers, payload, _ = self._prepare_request(prompt)

        try:
            response = requests.post(chat_url, headers=headers, json=payload, timeout=120)
            response.raise_for_status()
            data = response.json()

        except requests.exceptions.Timeout:
            return "# 错误：请求超时（超过120秒）"
        except requests.exceptions.HTTPError as e:
            return f"# 错误：HTTP {e.response.status_code} - {e.response.text[:200]}"
        except requests.exceptions.RequestException as e:
            return f"# 错误：请求失败 - {str(e)}"
        except Exception as e:
            return f"# 错误：未知错误 - {str(e)}"

        # Extract message from response
        try:
            message = data["choices"][0]["message"]
        except (KeyError, IndexError) as e:
            return f"# 错误：API 响应格式异常 - {str(e)}"

        text, _ = self._handle_response_message(message)
        return text

    def _continue_after_tools(self) -> str:
        """Continue conversation after tool calls."""
        system_content = build_system_prompt(self.memory_store)
        limited_history = limit_history_rounds(self.history, MAX_CONTEXT_ROUNDS)
        messages_with_system = [
            {"role": "system", "content": system_content}
        ] + limited_history

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": MODEL,
            "messages": messages_with_system,
            "tools": TOOL,
            "max_tokens": 8000
        }

        try:
            response = requests.post(chat_url, headers=headers, json=payload, timeout=120)
            response.raise_for_status()
            data = response.json()
        except Exception as e:
            return f"# 错误：工具响应后请求失败 - {str(e)}"

        try:
            message = data["choices"][0]["message"]
        except (KeyError, IndexError) as e:
            return f"# 错误：API 响应格式异常 - {str(e)}"

        content_value = message.get("content") or ""
        assistant_msg = {"role": "assistant", "content": content_value}
        self.history.append(assistant_msg)

        self.memory_store.save_history(self.history)

        return content_value

    def clear_history(self) -> None:
        """Clear conversation history for this user."""
        self.history = []
        self.memory_store.clear_history()
        logger.debug(f"Cleared history for user '{self.user_id}'")


# =============================================================================
# CLI interface (backward compatibility)
# =============================================================================

def chat(prompt: str, history: Optional[List[Dict]] = None, memory_store: Optional[MemoryStore] = None) -> str:
    """
    Legacy chat function for backward compatibility.

    Deprecated: Use HermesAgent class instead.
    """
    if history is None:
        history = []

    if memory_store is None:
        memory_store = MemoryStore("default")
        try:
            memory_store.load_from_disk()
        except Exception as e:
            print(f"# Warning: Could not load memory: {e}")

    # Add user message
    user_msg = {"role": "user", "content": prompt}
    history.append(user_msg)

    while True:
        system_content = build_system_prompt(memory_store)
        limited_history = limit_history_rounds(history, MAX_CONTEXT_ROUNDS)
        messages_with_system = [{"role": "system", "content": system_content}] + limited_history

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": MODEL,
            "messages": messages_with_system,
            "tools": TOOL,
            "max_tokens": 8000
        }

        try:
            response = requests.post(chat_url, headers=headers, json=payload, timeout=120)
            response.raise_for_status()
            data = response.json()
        except Exception as e:
            return f"# 错误：{str(e)}"

        try:
            message = data["choices"][0]["message"]
        except (KeyError, IndexError) as e:
            return f"# 错误：API 响应格式异常 - {str(e)}"

        content_value = message.get("content") or ""
        assistant_msg = {"role": "assistant", "content": content_value}

        if "tool_calls" in message and message["tool_calls"]:
            assistant_msg["tool_calls"] = []
            for tc in message["tool_calls"]:
                assistant_msg["tool_calls"].append({
                    "id": tc["id"],
                    "type": tc["type"],
                    "function": {
                        "name": tc["function"]["name"],
                        "arguments": tc["function"]["arguments"]
                    }
                })

        history.append(assistant_msg)

        if "tool_calls" not in message or not message["tool_calls"]:
            return content_value

        # Handle tool calls
        results = []
        for tc in message["tool_calls"]:
            func_name = tc["function"]["name"]
            func_args = json.loads(tc["function"]["arguments"])

            if func_name == "memory":
                result = memory_store.handle_tool_call(func_args)
                results.append({
                    "role": "tool",
                    "tool_call_id": tc["id"],
                    "content": result
                })

        history.extend(results)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        # Single command mode
        agent = HermesAgent()
        result = agent.chat(sys.argv[1])
        if result:
            safe_print(result)
    else:
        # Interactive REPL mode
        agent = HermesAgent()
        while True:
            try:
                query = input("\033[36m>> \033[0m")
            except (EOFError, KeyboardInterrupt):
                break
            if query in ("q", "exit", ""):
                break
            try:
                result = agent.chat(query)
                if result:
                    safe_print(result)
            except Exception as e:
                print(f"# Error: {e}")
