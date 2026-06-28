#!/usr/bin/env python

import requests
from dotenv import load_dotenv
import sys
import os
import json
import logging
from pathlib import Path
from datetime import datetime

# Windows 编码修复：在导入其他模块后立即设置
if sys.platform == "win32":
    try:
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    except Exception:
        pass  # 如果设置失败，继续使用默认编码

# 安全打印函数：处理编码问题
def safe_print(text):
    """安全打印，处理 Unicode 编码错误"""
    if text is None:
        return
    try:
        print(text)
    except UnicodeEncodeError:
        # Fallback: 替换无法编码的字符
        print(text.encode('ascii', 'replace').decode('ascii'))

load_dotenv(override=True)

# Import memory module
from memory import MemoryStore, MEMORY_TOOL_SCHEMA

# Configuration
MAX_CONTEXT_ROUNDS = int(os.getenv("MAX_CONTEXT_ROUNDS", "40"))  # 上下文保留轮数
CONVERSATION_FILE = os.getenv("CONVERSATION_FILE", "conversations.jsonl")  # 对话历史文件
DEBUG = os.getenv("DEBUG", "").lower() in ("1", "true", "yes", "on")  # 调试模式

# -----------------------------------------------------------------------------
# Logging setup
# -----------------------------------------------------------------------------

def setup_logging():
    """Configure logging based on DEBUG flag."""
    if DEBUG:
        log_level = logging.DEBUG
        log_format = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    else:
        log_level = logging.WARNING
        log_format = "%(levelname)s: %(message)s"

    logging.basicConfig(
        level=log_level,
        format=log_format,
        datefmt="%H:%M:%S"
    )
    return logging.getLogger("hermes")

logger = setup_logging()

# API Configuration for OpenAI-compatible endpoints
# Uses OPENAI_API_KEY (or ANTHROPIC_API_KEY for compatibility) and OPENAI_BASE_URL
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

# The tools that the agent can use
# OpenAI format: tools is a list of objects with "type" and "function" keys
MEMORY_TOOL = {
    "type": "function",
    "function": MEMORY_TOOL_SCHEMA
}

TOOL = [MEMORY_TOOL]


# =============================================================================
# 系统提示构建
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
    """
    构建完整的系统提示

    组成部分（按顺序）：
    1. 基础人设（硬编码）
    2. SOUL.md（可选，用户自定义）
    3. 工具说明（硬编码）
    4. 工作目录（动态）
    5. 记忆内容（如果存在）
    """
    parts = []

    # 1. 基础人设
    parts.append(get_base_personality())

    # 2. SOUL.md（用户自定义人格）
    soul_content = load_soul_md()
    if soul_content:
        parts.append(f"\n# 用户定义人格\n\n{soul_content}")

    # 3. 工具说明
    parts.append(get_tools_guide())

    # 4. 工作目录
    parts.append(get_working_directory())

    # 5. 记忆内容
    if memory_store:
        memory_block = memory_store.format_for_system_prompt("memory")
        if memory_block:
            parts.append(f"\n# 记忆\n\n{memory_block}")

        user_block = memory_store.format_for_system_prompt("user")
        if user_block:
            parts.append(f"\n{user_block}")

    return "\n\n".join(parts)


# 兼容性：保留 SYSTEM 变量（现在使用 build_system_prompt 代替）
SYSTEM = None  # 已废弃，使用 build_system_prompt() 函数


# =============================================================================
# 对话历史管理
# =============================================================================

def save_message(message):
    """
    保存单条消息到文件（OpenAI messages 格式，直接兼容）

    Args:
        message: OpenAI 格式的单条消息
    """
    try:
        with open(CONVERSATION_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(message, ensure_ascii=False) + "\n")
    except Exception as e:
        print(f"# Warning: Failed to save message: {e}")


def limit_history_rounds(history, max_rounds):
    """
    限制对话历史轮数

    Args:
        history: 完整对话历史
        max_rounds: 最大保留轮数

    Returns:
        限制后的历史记录
    """
    if max_rounds <= 0:
        return history

    # 计算需要保留的消息数
    # 一轮 = 1个 user 消息 + 1个 assistant 消息
    # 所以 max_rounds * 2 个消息
    max_messages = max_rounds * 2

    if len(history) <= max_messages:
        return history

    # 从末尾保留最近的消息
    # 注意：我们需要确保保留完整的轮次（成对的 user + assistant）
    # 所以从后往前数，保留完整的轮次
    result = []
    round_count = 0
    i = len(history) - 1

    while i >= 0 and round_count < max_rounds:
        # 先找 assistant 消息
        if history[i].get("role") == "assistant":
            # 检查前面是否有对应的 user 消息或 tool 消息
            j = i
            # 向前找到这轮的起始位置（包括所有相关的 tool 消息）
            while j >= 0:
                if history[j].get("role") in ["user", "system"]:
                    break
                j -= 1

            # 提取这轮的所有消息
            round_messages = history[j:i+1]
            # 倒序插入结果
            for msg in reversed(round_messages):
                result.insert(0, msg)

            round_count += 1
            i = j - 1
        else:
            i -= 1

    return result


# =============================================================================
# 核心代理逻辑
# =============================================================================

def chat(prompt, history=None, memory_store=None):
    """
    The complete agent loop in ONE function.

    This is the core pattern that ALL coding agents share:
        while not done:
            response = model(messages, tools)
            if no tool calls: return
            execute tools, append results

    Args:
        prompt: User's request
        history: Conversation history (mutable, shared across calls in interactive mode)
        memory_store: Optional MemoryStore instance for persistent memory

    Returns:
        Final text response from the model
    """
    if history is None:
        history = []

    # Initialize memory store if not provided
    if memory_store is None:
        memory_store = MemoryStore()
        try:
            memory_store.load_from_disk()
        except Exception as e:
            print(f"# Warning: Could not load memory: {e}")

    # 添加用户消息到历史并保存
    user_msg = {"role": "user", "content": prompt}
    history.append(user_msg)
    save_message(user_msg)
    logger.debug(f"Added user message to history. Total history: {len(history)} messages")

    while True:
        # 1. Call the model with tools (OpenAI format via requests)
        # 构建系统提示（包含基础人设、SOUL.md、工具说明、记忆）
        system_content = build_system_prompt(memory_store)

        # 限制上下文轮数
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

        logger.debug(f"API Request: {chat_url}")
        logger.debug(f"Model: {MODEL}")
        logger.debug(f"Messages count: {len(messages_with_system)}")
        logger.debug(f"System prompt length: {len(system_content)} chars")

        # 打印最后几条消息（用于调试）
        if DEBUG:
            for i, msg in enumerate(messages_with_system[-3:]):
                logger.debug(f"Message {i+1}: role={msg.get('role')}, content_preview={msg.get('content','')[:100]}")

        try:
            response = requests.post(chat_url, headers=headers, json=payload, timeout=120)
            logger.debug(f"Response status: {response.status_code}")

            response.raise_for_status()
            data = response.json()

            logger.debug(f"Response keys: {list(data.keys())}")
            if "choices" in data:
                logger.debug(f"Choices count: {len(data['choices'])}")
                if data['choices']:
                    logger.debug(f"First choice keys: {list(data['choices'][0].keys())}")

        except requests.exceptions.Timeout:
            logger.error("Request timeout (120s)")
            return "# 错误：请求超时（超过120秒）"
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP error: {e.response.status_code} - {e.response.text[:500]}")
            return f"# 错误：HTTP {e.response.status_code} - {e.response.text[:200]}"
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {e}")
            return f"# 错误：请求失败 - {str(e)}"
        except (KeyError, IndexError, ValueError) as e:
            logger.error(f"Response parsing failed: {e}")
            return f"# 错误：响应解析失败 - {str(e)}"
        except Exception as e:
            logger.error(f"Unknown error: {e}", exc_info=True)
            return f"# 错误：未知错误 - {str(e)}"

        # 2. Extract message from OpenAI response
        try:
            message = data["choices"][0]["message"]
            logger.debug(f"Message keys: {list(message.keys())}")
            logger.debug(f"Content type: {type(message.get('content'))}")
            logger.debug(f"Tool calls: {message.get('tool_calls')}")
        except (KeyError, IndexError) as e:
            logger.error(f"API response format error: {e}")
            logger.debug(f"Response data: {data}")
            return f"# 错误：API 响应格式异常 - {str(e)}"

        # 3. Build assistant message content
        # Handle both None and missing content
        content_value = message.get("content")
        if content_value is None:
            content_value = ""
            logger.warning("Model returned null content, using empty string")

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
        # 保存助手消息
        save_message(assistant_msg)

        # 4. If model didn't call tools, we're done
        if "tool_calls" not in message or not message["tool_calls"]:
            raw_content = message.get("content")
            logger.debug(f"Raw content from API: {repr(raw_content)}")

            response_content = raw_content or ""
            logger.debug(f"Processed content: {repr(response_content)}")

            if not response_content:
                logger.warning("Empty response from model (no content, no tool calls)")
                logger.debug(f"Full message: {message}")
                return f"# 注意：模型返回了空响应，请重试或检查 API 配置 (DEBUG: content={repr(raw_content)})"
            logger.debug(f"Returning response content: {len(response_content)} chars")
            return response_content

        # 5. Execute each tool call and collect results
        results = []
        for tc in message["tool_calls"]:
            func_name = tc["function"]["name"]
            func_args = json.loads(tc["function"]["arguments"])

            if func_name == "memory":
                # Handle memory tool
                print(f"\033[35mMemory: {func_args.get('action', 'unknown')} -> {func_args.get('target', 'memory')}\033[0m")
                if memory_store:
                    result = memory_store.handle_tool_call(func_args)
                    print(result)
                    results.append({
                        "role": "tool",
                        "tool_call_id": tc["id"],
                        "content": result
                    })
                    # 保存工具结果消息
                    save_message(results[-1])
                else:
                    error = json.dumps({"error": "Memory store not available"})
                    print(error)
                    results.append({
                        "role": "tool",
                        "tool_call_id": tc["id"],
                        "content": error
                    })
                    # 保存工具结果消息
                    save_message(results[-1])

            else:
                # Unknown tool
                error = json.dumps({"error": f"Unknown tool: {func_name}"})
                print(f"\033[31m{error}\033[0m")
                results.append({
                    "role": "tool",
                    "tool_call_id": tc["id"],
                    "content": error
                })
                # 保存工具结果消息
                save_message(results[-1])

        # 6. Append results and continue the loop
        history.extend(results)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        # Subagent mode: execute task and print result
        # This is how parent agents spawn children via bash
        # Create a temporary memory store for this subagent
        memory_store = MemoryStore()
        try:
            memory_store.load_from_disk()
        except Exception:
            pass  # Continue without memory if loading fails
        result = chat(sys.argv[1], memory_store=memory_store)
        if result:
            safe_print(result)
    else:
        # Interactive REPL mode - share memory store across all turns
        memory_store = MemoryStore()
        try:
            memory_store.load_from_disk()
        except Exception as e:
            print(f"# Warning: Could not load memory: {e}")

        history = []
        while True:
            try:
                query = input("\033[36m>> \033[0m")  # Cyan prompt
            except (EOFError, KeyboardInterrupt):
                break
            if query in ("q", "exit", ""):
                break
            try:
                result = chat(query, history, memory_store=memory_store)
                if result:
                    print(result)
            except Exception as e:
                print(f"# Error: {e}")
