#!/usr/bin/env python

import requests
from dotenv import load_dotenv
import sys
import os
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Generator, Union
import uuid

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

# Import audit log module
from audit_log import (
    log_user_question as audit_log_user_question,
    log_api_request as audit_log_api_request,
    log_api_response as audit_log_api_response,
    log_tool_call as audit_log_tool_call,
    log_agent_response as audit_log_agent_response,
    log_error as audit_log_error
)

# Import RAG retriever
from rag.retriever import get_retriever
from rag.document_loader import DocumentLoader

# Configuration
MAX_CONTEXT_ROUNDS = int(os.getenv("MAX_CONTEXT_ROUNDS", "40"))
MAX_TOOL_ITERATIONS = int(os.getenv("MAX_TOOL_ITERATIONS", "8"))
DEBUG = os.getenv("DEBUG", "").lower() in ("1", "true", "yes", "on")

# Logging configuration from environment
LOG_LEVEL = os.getenv("LOG_LEVEL", "DEBUG" if DEBUG else "INFO")
LOG_FILE = os.getenv("LOG_FILE", "true").lower() in ("1", "true", "yes", "on")

# Create logs directory
logs_dir = Path(os.getcwd()) / "logs"
logs_dir.mkdir(exist_ok=True)

# Generate log filename with date
log_filename = logs_dir / f"hermes-{datetime.now().strftime('%Y-%m-%d')}.log"


def setup_logging():
    """Configure logging with file and console output."""
    # Define TRACE level (more verbose than DEBUG)
    TRACE_LEVEL = 5
    logging.addLevelName(TRACE_LEVEL, "TRACE")

    def trace(self, message, *args, **kwargs):
        if self.isEnabledFor(TRACE_LEVEL):
            self._log(TRACE_LEVEL, message, args, **kwargs)

    logging.Logger.trace = trace

    # Always use TRACE level for maximum detail
    log_level = TRACE_LEVEL
    log_format = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    root_logger.handlers.clear()

    file_handler = logging.FileHandler(log_filename, encoding='utf-8')
    file_handler.setLevel(log_level)
    file_formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    file_handler.setFormatter(file_formatter)
    root_logger.addHandler(file_handler)

    # Console handler - simplified
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_formatter = logging.Formatter(
        "%(levelname)s: %(message)s"
    )
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)

    return logging.getLogger("hermes")


logger = setup_logging()


def log_request_trace(request_id: str, user_id: str, prompt: str, system_prompt_length: int,
                      history_length: int, model: str):
    """Log incoming request details."""
    logger.info(f"[{request_id}] REQUEST START")
    logger.info(f"[{request_id}] User: {user_id}")
    logger.info(f"[{request_id}] Model: {model}")
    logger.info(f"[{request_id}] Prompt length: {len(prompt)} chars")
    logger.info(f"[{request_id}] System prompt length: {system_prompt_length} chars")
    logger.info(f"[{request_id}] History messages: {history_length}")
    logger.debug(f"[{request_id}] Prompt preview: {prompt[:100]}...")


def log_api_call(request_id: str, endpoint: str, payload_size: int, tool_count: int):
    """Log API call details."""
    logger.info(f"[{request_id}] API CALL -> {endpoint}")
    logger.info(f"[{request_id}] Payload size: {payload_size} bytes")
    logger.info(f"[{request_id}] Tools: {tool_count}")


def log_api_response(request_id: str, status_code: int, response_size: int,
                     has_tool_calls: bool, finish_reason: str):
    """Log API response details."""
    logger.info(f"[{request_id}] API RESPONSE <- Status: {status_code}")
    logger.info(f"[{request_id}] Response size: {response_size} bytes")
    logger.info(f"[{request_id}] Tool calls: {has_tool_calls}")
    logger.info(f"[{request_id}] Finish reason: {finish_reason}")


def log_tool_execution(request_id: str, tool_name: str, action: str, target: str, result: str):
    """Log tool execution details."""
    logger.info(f"[{request_id}] TOOL EXECUTION: {tool_name}")
    logger.info(f"[{request_id}]   Action: {action}, Target: {target}")
    logger.debug(f"[{request_id}]   Result: {result[:200]}...")


def log_response_trace(request_id: str, response_length: int, duration_ms: float):
    """Log response details."""
    logger.info(f"[{request_id}] REQUEST COMPLETE")
    logger.info(f"[{request_id}] Response length: {response_length} chars")
    logger.info(f"[{request_id}] Duration: {duration_ms:.0f}ms")


def log_error_trace(request_id: str, error_type: str, error_message: str):
    """Log error details."""
    logger.error(f"[{request_id}] ERROR: {error_type}")
    logger.error(f"[{request_id}] Message: {error_message}")

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

# --- Tan同学-AI英语助教 新增工具 ---

TASK_TOOL = {
    "type": "function",
    "function": {
        "name": "generate_daily_task",
        "description": "基于用户英语水平和近期学习数据，动态生成今日学习任务清单(“今日三件事”)。",
        "parameters": {
            "type": "object",
            "properties": {
                "user_level": {
                    "type": "string",
                    "enum": ["beginner", "intermediate", "advanced"],
                    "description": "用户英语水平等级"
                },
                "focus_areas": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "需要重点加强的领域，如 ['pronunciation', 'vocabulary', 'listening']"
                },
                "history_summary": {
                    "type": "string",
                    "description": "用户近期学习数据摘要（如：最近3天学习了45分钟，发音分65分）"
                }
            },
            "required": ["user_level"]
        }
    }
}

SCENARIO_TOOL = {
    "type": "function",
    "function": {
        "name": "start_scenario",
        "description": "启动场景对话——AI 扮演对话伙伴，学生自由对话练习口语。支持餐厅、问路、面试等 10+ 场景。",
        "parameters": {
            "type": "object",
            "properties": {
                "scene_type": {
                    "type": "string",
                    "enum": ["restaurant", "directions", "classroom", "interview", "travel", "shopping", "hospital", "phone_call", "study_group", "presentation"],
                    "description": "场景类型"
                },
                "difficulty": {
                    "type": "string",
                    "enum": ["easy", "medium", "hard"],
                    "description": "难度级别"
                }
            },
            "required": ["scene_type", "difficulty"]
        }
    }
}

RAG_TOOL = {
    "type": "function",
    "function": {
        "name": "search_knowledge",
        "description": "从英语知识库中检索语法规则、词汇解释或发音技巧。当学生询问语法、词义或发音规则时使用。",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "检索查询，如 'present perfect tense' 或 'th sound pronunciation'"
                },
                "topic": {
                    "type": "string",
                    "enum": ["grammar", "vocabulary", "pronunciation"],
                    "description": "知识主题"
                }
            },
            "required": ["query", "topic"]
        }
    }
}

TOOL = [MEMORY_TOOL, TASK_TOOL, SCENARIO_TOOL, RAG_TOOL]


# =============================================================================
# System prompt building
# =============================================================================

def get_base_personality():
    """基础人设：严格限定为英语教学专用"""
    return """你是一个英语教学专用AI助手，只负责英语学习相关的教学辅导。

## 核心边界（最高优先级，不可违反）
你**只回答**与英语学习直接相关的问题，包括但不限于：
- 英语词汇、语法、发音、阅读、写作、听力
- 英语考试（四级、六级、考研英语、雅思、托福等）
- 英语学习方法、学习计划、每日任务
- 英语场景对话、口语练习
- 英语文化背景知识

你**必须拒绝**所有与英语学习无关的请求，包括但不限于：
- 数学、物理、化学、编程等其他学科的教学辅导
- 通用知识问答（历史、地理、政治等）
- 写作代笔（非英语类文章、论文、报告等）
- 编程、代码调试、技术方案设计
- 翻译服务（非英语翻译到英语的除外）
- 闲聊、心理咨询、情感陪伴

## 拒绝话术
当用户提出非英语学习请求时，用以下方式礼貌拒绝：
"抱歉，我是专为英语学习设计的AI助教，只能辅导英语相关的内容。如果你有英语学习方面的问题，我很乐意帮你！"

如果用户连续3次提出非英语请求，除了拒绝外，可以主动引导：
"发现你似乎想了解其他领域的内容。不如我们回到英语学习上？比如我可以帮你：1）生成今日学习任务 2）练习场景对话 3）检查你的发音。你对哪个感兴趣？"

## 特殊说明
- 用户可以用中文提问英语学习问题，这是正常的（如"这个单词什么意思"），不算越界
- 用户问"如何学英语"、"怎么提高口语"等学习方法问题，属于正常范围
- 场景对话中AI扮演的NPC角色，也可以偶尔涉及日常话题（天气、爱好等），因为这属于英语口语练习的一部分"""


def load_soul_md():
    """加载 SOUL.md（必需——定义智能体核心人格）"""
    soul_path = Path(os.getcwd()) / "SOUL.md"
    if not soul_path.exists():
        raise RuntimeError(
            f"致命错误：SOUL.md 未找到！\n"
            f"期望路径：{soul_path}\n"
            f"当前工作目录：{os.getcwd()}\n"
            f"请确保从项目根目录启动服务，且 SOUL.md 文件存在。"
        )
    try:
        content = soul_path.read_text(encoding="utf-8").strip()
        if not content:
            raise RuntimeError(f"致命错误：SOUL.md 文件为空！路径：{soul_path}")
        return content
    except RuntimeError:
        raise
    except Exception as e:
        raise RuntimeError(f"致命错误：无法读取 SOUL.md ({soul_path})：{e}")


def get_tools_guide():
    """工具使用说明（硬编码）"""
    return """## 可用工具

### memory
跨会话持久化信息，供未来参考。

**何时保存（主动进行，不要等用户要求）：**
- 学生纠正你的发音或教学方法
- 学生的学习偏好、薄弱领域、学习习惯
- 学生提到的重要个人信息（考试日期、目标分数等）
- 教学过程中发现的规律性错误

### generate_daily_task
基于学生英语水平和近期学习数据，动态生成今日学习任务清单。
- 首次使用或新的一天开始时使用
- 学生请求"今天学什么"时使用
- 根据学生薄弱项动态调整任务类型和难度

### start_scenario
启动场景对话——AI 扮演对话伙伴，学生自由对话练习口语。
- 支持餐厅、问路、面试等 10+ 场景
- 三个难度级别：easy（适合初学者）、medium（有一定基础）、hard（进阶挑战）
- 启动后按 SOUL.md 教学流程进行 NPC 对话

### search_knowledge
从英语知识库中检索语法规则、词汇解释或发音技巧。
- 当学生询问语法规则时（topic=grammar）
- 当学生查询单词含义时（topic=vocabulary）
- 当学生询问发音技巧时（topic=pronunciation）"""


def build_system_prompt(memory_store=None):
    """构建完整的系统提示"""
    parts = []
    parts.append(get_base_personality())

    soul_content = load_soul_md()
    if soul_content:
        parts.append(f"\n# 用户定义人格\n\n{soul_content}")

    parts.append(get_tools_guide())

    if memory_store:
        memory_block = memory_store.format_for_system_prompt("memory")
        if memory_block:
            parts.append(f"\n# 记忆\n\n{memory_block}")

        user_block = memory_store.format_for_system_prompt("user")
        if user_block:
            parts.append(f"\n{user_block}")

    return "\n\n".join(parts)


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
        # Generate unique request ID for tracing
        request_id = str(uuid.uuid4())[:8]
        start_time = datetime.now()

        # Add user message to history
        user_msg = {"role": "user", "content": prompt}
        self.history.append(user_msg)
        logger.debug(f"[{request_id}] Added user message. Total history: {len(self.history)} messages")

        # Build system prompt
        system_content = build_system_prompt(self.memory_store)

        # Limit history rounds
        limited_history = limit_history_rounds(self.history, MAX_CONTEXT_ROUNDS)

        # Log request trace
        log_request_trace(
            request_id=request_id,
            user_id=self.user_id,
            prompt=prompt,
            system_prompt_length=len(system_content),
            history_length=len(limited_history),
            model=MODEL
        )

        # Audit log: user question
        audit_log_user_question(
            user_id=self.user_id,
            request_id=request_id,
            question=prompt,
            system_prompt_length=len(system_content),
            history_length=len(limited_history)
        )

        # Build messages for API
        messages_with_system = [
            {"role": "system", "content": system_content}
        ] + limited_history

        # Start agent loop
        return self._agent_loop(request_id, start_time, messages_with_system)

    def _execute_tool_calls(self, request_id: str, tool_calls: list) -> list:
        """
        Execute tool calls and return results.

        Args:
            request_id: Request ID for tracing
            tool_calls: List of tool call objects from API response

        Returns:
            List of tool result messages to add to history
        """
        results = []
        for tc in tool_calls:
            func_name = tc["function"]["name"]
            raw_args = tc["function"]["arguments"]
            if isinstance(raw_args, dict):
                func_args = raw_args
            else:
                try:
                    func_args = json.loads(raw_args)
                except (json.JSONDecodeError, TypeError) as e:
                    logger.error(f"[{request_id}] Failed to parse tool arguments: {e}, raw={raw_args!r}")
                    results.append({
                        "role": "tool",
                        "tool_call_id": tc["id"],
                        "content": json.dumps({"error": f"Parse error: {str(e)}"})
                    })
                    continue

            if func_name == "memory":
                print(f"\033[35mMemory: {func_args.get('action', 'unknown')} -> {func_args.get('target', 'memory')}\033[0m")
                result = self.memory_store.handle_tool_call(func_args)
                print(result)

                # Log tool execution
                log_tool_execution(
                    request_id=request_id,
                    tool_name=func_name,
                    action=func_args.get('action', 'unknown'),
                    target=func_args.get('target', 'memory'),
                    result=result
                )

                # Audit log: tool call
                result_success = False
                try:
                    result_data = json.loads(result) if isinstance(result, str) else result
                    result_success = result_data.get("success", False)
                except:
                    pass

                audit_log_tool_call(
                    user_id=self.user_id,
                    request_id=request_id,
                    tool_name=func_name,
                    action=func_args.get('action', 'unknown'),
                    target=func_args.get('target', 'memory'),
                    arguments=func_args,
                    result=result,
                    success=result_success
                )

                results.append({
                    "role": "tool",
                    "tool_call_id": tc["id"],
                    "content": result
                })
            elif func_name == "generate_daily_task":
                print(f"\033[33mTask: generating for level={func_args.get('user_level', 'beginner')}\033[0m")
                result = self._handle_task_tool(func_args)
                safe_print(result[:200])

                log_tool_execution(request_id, func_name, "generate",
                                   func_args.get('user_level', ''), result[:200])
                audit_log_tool_call(self.user_id, request_id, func_name, "generate",
                                    func_args.get('user_level', ''), func_args, result[:200], True)

                results.append({"role": "tool", "tool_call_id": tc["id"], "content": result})

            elif func_name == "start_scenario":
                print(f"\033[32mScenario: {func_args.get('scene_type', 'unknown')}\033[0m")
                result = self._handle_scenario_tool(func_args)
                safe_print(result[:200])

                log_tool_execution(request_id, func_name, "start",
                                   func_args.get('scene_type', ''), result[:200])
                audit_log_tool_call(self.user_id, request_id, func_name, "start",
                                    func_args.get('scene_type', ''), func_args, result[:200], True)

                results.append({"role": "tool", "tool_call_id": tc["id"], "content": result})

            elif func_name == "search_knowledge":
                print(f"\033[34mRAG: searching {func_args.get('topic', '')} -> {func_args.get('query', '')[:50]}\033[0m")
                result = self._handle_rag_tool(func_args)
                safe_print(result[:200])

                log_tool_execution(request_id, func_name, "search",
                                   func_args.get('query', '')[:50], result[:200])
                audit_log_tool_call(self.user_id, request_id, func_name, "search",
                                    func_args.get('query', '')[:50], func_args, result[:200], True)

                results.append({"role": "tool", "tool_call_id": tc["id"], "content": result})

            else:
                error = json.dumps({"error": f"Unknown tool: {func_name}"})
                print(f"\033[31m{error}\033[0m")
                log_error_trace(request_id, f"ToolError:{func_name}", error)
                results.append({
                    "role": "tool",
                    "tool_call_id": tc["id"],
                    "content": error
                })

        return results

    def _call_llm_direct(self, prompt: str) -> str:
        """单次 LLM 调用（不走 tool loop），用于轻量内容生成"""
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": MODEL,
            "messages": [
                {"role": "system", "content": "你是一个专业的AI英语教学助手。只返回要求的JSON格式，不要添加任何额外说明。"},
                {"role": "user", "content": prompt}
            ],
            "max_tokens": 1024,
            "temperature": 0.7,
        }

        try:
            response = requests.post(chat_url, headers=headers, json=payload, timeout=60)
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"].strip()
        except Exception as e:
            logger.error(f"LLM 直接调用失败: {e}")
            raise

    def _handle_task_tool(self, args: dict) -> str:
        """处理每日任务生成工具调用（LLM 动态生成 + 模板 fallback）"""
        user_level = args.get("user_level", "beginner")
        focus_areas = args.get("focus_areas", [])
        history_summary = args.get("history_summary", "")

        # 模板 fallback
        task_templates = {
            "beginner": [
                {"title": "学习 5 个新单词（含发音跟读）", "type": "vocab", "duration_min": 8},
                {"title": "跟读 2 个常用句子", "type": "speaking", "duration_min": 5},
                {"title": "听力练习：听写 1 段短对话", "type": "listening", "duration_min": 7},
            ],
            "intermediate": [
                {"title": "学习 8 个新单词（含例句造句）", "type": "vocab", "duration_min": 10},
                {"title": "跟读 3 个长句（重点：连读、重音）", "type": "speaking", "duration_min": 8},
                {"title": "完成 1 次场景对话（自选场景）", "type": "speaking", "duration_min": 10},
            ],
            "advanced": [
                {"title": "阅读 1 篇英文短文并回答问题", "type": "reading", "duration_min": 12},
                {"title": "收听 1 段 3 分钟播客并复述大意", "type": "listening", "duration_min": 10},
                {"title": "自由对话：选择一个场景即兴交流", "type": "speaking", "duration_min": 8},
            ],
        }

        tasks = None
        total_minutes = 0
        generated = False

        # 尝试 LLM 动态生成
        try:
            focus_str = "、".join(focus_areas) if focus_areas else "综合提升"
            prompt = f"""基于以下学生信息生成今日 3 个英语学习任务：
- 英语等级：{user_level}（beginner=初级/intermediate=中级/advanced=高级）
- 重点提升领域：{focus_str}
- 近期学习摘要：{history_summary if history_summary else "新学生，暂无数据"}

要求：
1. 每个任务包含 title（中文描述，具体有趣）、type（vocab/speaking/listening/reading）、duration_min（整数分钟）
2. 根据薄弱领域调整任务类型比例
3. 总时长控制在 15-30 分钟
4. 只返回纯 JSON 数组，格式：[{{"title":"...", "type":"...", "duration_min":N}}, ...]"""

            llm_response = self._call_llm_direct(prompt)
            # 清理可能的 markdown 代码块包裹
            llm_response = llm_response.strip()
            if llm_response.startswith("```"):
                lines = llm_response.split("\n")
                llm_response = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
            tasks = json.loads(llm_response)
            if isinstance(tasks, list) and len(tasks) > 0:
                total_minutes = sum(t.get("duration_min", 0) for t in tasks)
                generated = True
                logger.info(f"LLM 动态生成 {len(tasks)} 个任务")
        except Exception as e:
            logger.warning(f"LLM 任务生成失败，使用模板: {e}")

        if not generated:
            tasks = task_templates.get(user_level, task_templates["beginner"])
            total_minutes = sum(t["duration_min"] for t in tasks)

        result = {
            "tool": "generate_daily_task",
            "user_level": user_level,
            "focus_areas": focus_areas,
            "tasks": tasks,
            "total_estimated_minutes": total_minutes,
            "generated_by": "llm" if generated else "template",
            "tip": "建议按顺序完成，每项任务完成后记得打卡哦！",
            "history_note": history_summary[:100] if history_summary else "",
        }
        return json.dumps(result, ensure_ascii=False, indent=2)

    def _handle_scenario_tool(self, args: dict) -> str:
        """处理场景对话工具调用"""
        scene_type = args.get("scene_type", "restaurant")
        difficulty = args.get("difficulty", "easy")

        from services.scenario_service import get_scenario_service
        service = get_scenario_service()
        scenario = service.get_scenario(scene_type)

        if not scenario:
            return json.dumps({"error": f"未知场景: {scene_type}"}, ensure_ascii=False)

        result = {
            "tool": "start_scenario",
            "scene_type": scene_type,
            "scene_name": scenario["name"],
            "difficulty": difficulty,
            "roles": scenario["roles"],
            "learning_goals": scenario["learning_goals"],
            "opening_prompt": scenario["opening_prompt"],
            "instruction": "请用 NPC 的角色开始对话。NPC 全程使用英文，教师提示使用中文。遵循 SOUL.md 中的教学流程。",
        }
        return json.dumps(result, ensure_ascii=False, indent=2)

    def _handle_rag_tool(self, args: dict) -> str:
        """处理知识检索工具调用"""
        query = args.get("query", "")
        topic = args.get("topic", "grammar")

        try:
            retriever = get_retriever()
            results = retriever.search(query, topic, k=3)

            if results:
                formatted = retriever.format_for_prompt(results, topic)
                return json.dumps({
                    "tool": "search_knowledge",
                    "query": query,
                    "topic": topic,
                    "results_count": len(results),
                    "knowledge": formatted,
                }, ensure_ascii=False, indent=2)
            else:
                # 回退：从预置规则中查找
                loader = DocumentLoader()
                if topic == "grammar":
                    rules = loader.get_grammar_rules()
                    matches = [r for r in rules if query.lower() in r["text"].lower()][:3]
                    return json.dumps({
                        "tool": "search_knowledge",
                        "query": query,
                        "topic": topic,
                        "results_count": len(matches),
                        "knowledge": "\n".join(m["text"] for m in matches),
                    }, ensure_ascii=False, indent=2)
                elif topic == "pronunciation":
                    tips = loader.get_pronunciation_tips()
                    matches = [t for t in tips if query.lower() in t["text"].lower()][:3]
                    return json.dumps({
                        "tool": "search_knowledge",
                        "query": query,
                        "topic": topic,
                        "results_count": len(matches),
                        "knowledge": "\n".join(m["text"] for m in matches),
                    }, ensure_ascii=False, indent=2)

                return json.dumps({
                    "tool": "search_knowledge",
                    "query": query,
                    "topic": topic,
                    "results_count": 0,
                    "knowledge": "未找到相关知识条目。建议使用通用英语知识回答。",
                }, ensure_ascii=False, indent=2)

        except Exception as e:
            logger.error(f"RAG 检索异常: {e}")
            return json.dumps({"error": f"知识检索失败: {str(e)}"}, ensure_ascii=False)

    def _make_api_call(self, request_id: str, messages: list) -> dict:
        """
        Make API call and return response data.

        Args:
            request_id: Request ID for tracing
            messages: List of messages to send

        Returns:
            Dictionary with response data or None if error
        """
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": MODEL,
            "messages": messages,
            "tools": TOOL,
            "max_tokens": 8000
        }

        # Log API call
        log_api_call(
            request_id=request_id,
            endpoint=chat_url,
            payload_size=len(json.dumps(payload)),
            tool_count=len(TOOL)
        )

        # Audit log: API request
        audit_log_api_request(
            user_id=self.user_id,
            request_id=request_id,
            endpoint=chat_url,
            payload_size=len(json.dumps(payload)),
            tool_count=len(TOOL),
            model=MODEL
        )

        try:
            response = requests.post(chat_url, headers=headers, json=payload, timeout=120)
            response.raise_for_status()
            data = response.json()

            # Audit log: API response
            api_duration_ms = (response.elapsed.total_seconds() * 1000) if hasattr(response, 'elapsed') else 0
            audit_log_api_response(
                user_id=self.user_id,
                request_id=request_id,
                status_code=response.status_code,
                response_size=len(response.content),
                has_tool_calls="tool_calls" in data["choices"][0]["message"],
                finish_reason=data["choices"][0].get("finish_reason", "unknown"),
                duration_ms=api_duration_ms
            )

            return data

        except requests.exceptions.Timeout:
            log_error_trace(request_id, "Timeout", "Request exceeded 120 seconds")
            audit_log_error(self.user_id, request_id, "Timeout", "Request exceeded 120 seconds")
            return {"error": "timeout"}
        except requests.exceptions.HTTPError as e:
            log_error_trace(request_id, "HTTPError", f"Status {e.response.status_code}")
            audit_log_error(self.user_id, request_id, "HTTPError", f"Status {e.response.status_code}")
            return {"error": f"http_{e.response.status_code}"}
        except requests.exceptions.RequestException as e:
            log_error_trace(request_id, "RequestException", str(e))
            audit_log_error(self.user_id, request_id, "RequestException", str(e))
            return {"error": "request_failed"}
        except Exception as e:
            log_error_trace(request_id, "UnknownError", str(e))
            audit_log_error(self.user_id, request_id, "UnknownError", str(e))
            return {"error": "unknown"}

    def _agent_loop(self, request_id: str, start_time: datetime, messages: list) -> str:
        """
        Main agent loop that handles tool calls iteratively.

        Args:
            request_id: Request ID for tracing
            start_time: Start time for duration tracking
            messages: List of messages to start with

        Returns:
            Final text response from the agent
        """
        iteration = 0
        tool_calls_count = 0
        accumulated_content = ""  # Accumulate content from all iterations

        while iteration < MAX_TOOL_ITERATIONS:
            iteration += 1
            logger.info(f"[{request_id}] Agent loop iteration {iteration}/{MAX_TOOL_ITERATIONS}")

            # Make API call
            data = self._make_api_call(request_id, messages)

            # Check for API errors
            if "error" in data:
                error_msg = f"# 错误：API调用失败 - {data['error']}"
                logger.error(f"[{request_id}] API error in loop: {data['error']}")
                return error_msg

            # Extract message from response
            try:
                message = data["choices"][0]["message"]
            except (KeyError, IndexError) as e:
                error_msg = f"# 错误：API 响应格式异常 - {str(e)}"
                log_error_trace(request_id, "ResponseParseError", str(e))
                return error_msg

            # Build assistant message
            content_value = message.get("content") or message.get('reasoning_content') or ''
            assistant_msg = {"role": "assistant", "content": content_value}

            # Check if there are tool calls
            if "tool_calls" in message and message["tool_calls"]:
                tool_calls_count += len(message["tool_calls"])
                logger.info(f"[{request_id}] Found {len(message['tool_calls'])} tool calls")

                # Log if content accompanies tool calls
                if content_value:
                    logger.info(f"[{request_id}] Content with tool calls: {content_value[:50]}...")
                    # Accumulate content from this iteration
                    accumulated_content += content_value + "\n\n"

                # Add tool_calls to assistant message
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

                # Add assistant message to history (includes both content and tool_calls)
                self.history.append(assistant_msg)

                # Execute tool calls
                tool_results = self._execute_tool_calls(request_id, message["tool_calls"])

                # Add tool results to history
                self.history.extend(tool_results)

                # Update messages for next iteration
                system_content = build_system_prompt(self.memory_store)
                limited_history = limit_history_rounds(self.history, MAX_CONTEXT_ROUNDS)
                messages = [
                    {"role": "system", "content": system_content}
                ] + limited_history

                # Continue loop for next iteration
                continue

            # No tool calls - this is the final response
            self.history.append(assistant_msg)
            self.memory_store.save_history(self.history)

            # Handle empty response - only use fallback if we have NO accumulated content
            if not content_value:
                if accumulated_content:
                    # We have accumulated content from tool call iterations, use that
                    logger.info(f"[{request_id}] Empty final response, using accumulated content ({len(accumulated_content)} chars)")
                    final_response = accumulated_content
                else:
                    # Truly empty response, provide fallback
                    logger.warning(f"[{request_id}] Empty response received, providing fallback")
                    final_response = "I've processed your request. How else can I help you?"
            else:
                # Combine accumulated content with final response
                final_response = accumulated_content + content_value

            # Log completion
            duration_ms = (datetime.now() - start_time).total_seconds() * 1000
            log_response_trace(request_id, len(final_response), duration_ms)

            # Audit log: agent response
            audit_log_agent_response(
                user_id=self.user_id,
                request_id=request_id,
                response=final_response,
                response_length=len(final_response),
                total_duration_ms=duration_ms,
                tool_calls_count=tool_calls_count
            )

            logger.info(f"[{request_id}] Agent loop completed with text response")
            return final_response

        # Max iterations reached - force termination
        logger.warning(f"[{request_id}] Max iterations ({MAX_TOOL_ITERATIONS}) reached, forcing termination")

        # Add a termination message
        termination_msg = "I've processed your request, but reached the maximum number of operations. How else can I help you?"
        self.history.append({"role": "assistant", "content": termination_msg})
        self.memory_store.save_history(self.history)

        # Combine accumulated content with termination message
        final_response = accumulated_content + termination_msg

        # Audit log: forced termination
        duration_ms = (datetime.now() - start_time).total_seconds() * 1000
        audit_log_agent_response(
            user_id=self.user_id,
            request_id=request_id,
            response=final_response,
            response_length=len(final_response),
            total_duration_ms=duration_ms,
            tool_calls_count=tool_calls_count
        )

        return final_response

    def chat(self, prompt: str, messages: List[Dict] = None) -> str:
        """
        Public interface to send a message and get a response.

        Args:
            prompt: User's input message
            messages: Optional custom messages list (for streaming reuse)

        Returns:
            Assistant's response text
        """
        return self._prepare_request(prompt, messages)

    def clear_history(self) -> None:
        """Clear conversation history for this user."""
        self.history = []
        self.memory_store.clear_history()
        logger.debug(f"Cleared history for user '{self.user_id}'")

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
