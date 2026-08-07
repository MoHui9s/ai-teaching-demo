"""每日任务端点"""

import os
import json
import logging
from datetime import date, datetime
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from database.database import get_db, get_db_session
from database.models import DailyTask as DailyTaskModel, User
from api.schemas import (
    TaskItem,
    DailyTaskResponse,
    TaskCompleteRequest,
    DiagnosisRequest,
    DiagnosisResponse,
    APIResponse,
)
from api._user_sync import ensure_orm_user

logger = logging.getLogger("edulingua-tasks")

router = APIRouter(prefix="/api/tasks", tags=["Tasks"])


def _generate_tasks_with_llm(level: str, user_id: str = "") -> Optional[List[dict]]:
    """使用 LLM 动态生成每日任务，失败返回 None"""
    try:
        import requests

        api_key = os.getenv("OPENAI_API_KEY")
        base_url = os.getenv("OPENAI_BASE_URL", "https://api.deepseek.com")
        model = os.getenv("MODEL", "deepseek-v4-flash")

        if not api_key:
            logger.warning("未配置 LLM API Key，跳过动态任务生成")
            return None

        base_url = base_url.rstrip("/")
        chat_url = base_url + "/chat/completions" if not base_url.endswith("/v1") else base_url + "/chat/completions"
        if "/chat/completions" not in chat_url:
            chat_url = base_url.rstrip("/") + "/chat/completions"

        prompt = f"""基于以下学生信息生成今日 3 个英语学习任务：
- 英语等级：{level}（beginner=初级/intermediate=中级/advanced=高级）
- 学生 ID：{user_id}

要求：
1. 每个任务包含 title（中文描述，具体有趣）、type（vocab/speaking/listening/reading）、duration_min（整数分钟）
2. 针对 {level} 级别调整任务难度
3. 总时长控制在 15-30 分钟
4. 只返回纯 JSON 数组，格式：[{{"title":"...", "type":"...", "duration_min":N}}, ...]"""

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": "你是一个专业的AI英语教学助手。只返回要求的JSON格式，不要添加任何额外说明。"},
                {"role": "user", "content": prompt}
            ],
            "max_tokens": 1024,
            "temperature": 0.7,
        }

        response = requests.post(chat_url, headers=headers, json=payload, timeout=60)
        response.raise_for_status()
        data = response.json()
        content = data["choices"][0]["message"]["content"].strip()

        # 清理 markdown 代码块
        if content.startswith("```"):
            lines = content.split("\n")
            content = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])

        tasks = json.loads(content)
        if isinstance(tasks, list) and len(tasks) > 0:
            logger.info(f"LLM 动态生成 {len(tasks)} 个任务: user={user_id}, level={level}")
            return tasks
    except Exception as e:
        logger.warning(f"LLM 任务生成失败，将使用模板: {e}")

    return None

# 默认每日任务模板（按级别）
DEFAULT_TASKS = {
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


@router.get("/daily", response_model=APIResponse)
async def get_daily_tasks(user_id: str = "default"):
    """
    获取今日任务

    Args:
        user_id: 用户标识

    Returns:
        今日任务清单
    """
    today = date.today()
    db = get_db_session()

    try:
        # 查找今天的任务
        task = db.query(DailyTaskModel).filter(
            DailyTaskModel.user.has(user_id=user_id),
            DailyTaskModel.date == today
        ).first()

        if task:
            return APIResponse(
                success=True,
                message="今日任务已生成",
                data={
                    "id": task.id,
                    "date": task.date.isoformat(),
                    "task_content": task.task_content,
                    "status": task.status,
                    "time_spent": task.time_spent,
                }
            )

        # 未生成任务：LLM 动态生成，失败则 fallback 模板
        user = db.query(User).filter(User.user_id == user_id).first()
        if not user:
            # 用户不存在于 ORM，尝试从 auth 库修复（DEV_MODE）或返回错误
            import os
            dev_mode = os.getenv("DEV_MODE", "false").lower() in ("1", "true", "yes")
            if dev_mode:
                from database.user_db_sqlite import get_user_db
                auth_db = get_user_db()
                auth_user = auth_db.get_user_by_id(user_id)
                if auth_user:
                    user = ensure_orm_user(
                        user_id, auth_user["email"],
                        auth_user.get("password_hash", "")
                    )
            if not user:
                return APIResponse(
                    success=False,
                    message="用户不存在，请先注册",
                    data=None
                )

        level = user.level if user else "beginner"
        tasks = _generate_tasks_with_llm(level, user_id) or DEFAULT_TASKS.get(level, DEFAULT_TASKS["beginner"])
        # 检测是否为新用户（无历史任务）
        task_history_count = db.query(DailyTaskModel).filter(
            DailyTaskModel.user_id == user.id
        ).count()
        is_new_user = task_history_count == 0

        new_task = DailyTaskModel(
            user_id=user.id,
            date=today,
            task_content=tasks,
            status="pending",
        )
        db.add(new_task)
        db.commit()
        db.refresh(new_task)

        return APIResponse(
            success=True,
            message=f"已自动生成今日任务（难度：{level}）",
            data={
                "id": new_task.id,
                "date": new_task.date.isoformat(),
                "task_content": new_task.task_content,
                "status": new_task.status,
                "time_spent": new_task.time_spent,
                "onboarding": is_new_user,
                "suggested_action": "diagnosis" if is_new_user else None,
            }
        )

    finally:
        db.close()


@router.post("/daily/complete", response_model=APIResponse)
async def complete_task(request: TaskCompleteRequest, user_id: str = "default"):
    """
    完成子任务

    Args:
        request: 完成的子任务索引和耗时
        user_id: 用户标识

    Returns:
        更新后的任务状态
    """
    today = date.today()
    db = get_db_session()

    try:
        task = db.query(DailyTaskModel).filter(
            DailyTaskModel.user.has(user_id=user_id),
            DailyTaskModel.date == today
        ).first()

        if not task:
            return APIResponse(success=False, message="今日任务尚未生成")

        task_content = list(task.task_content)  # 深拷贝
        if request.task_index >= len(task_content):
            return APIResponse(success=False, message="任务索引超出范围")

        task_content[request.task_index]["status"] = "done"
        task.task_content = task_content
        task.time_spent += request.time_spent_min

        # 所有任务完成
        if all(t.get("status") == "done" for t in task_content):
            task.status = "completed"

        db.commit()

        return APIResponse(
            success=True,
            message="任务完成！",
            data={
                "task_content": task_content,
                "status": task.status,
                "time_spent": task.time_spent,
            }
        )

    finally:
        db.close()


@router.post("/diagnosis", response_model=DiagnosisResponse)
async def diagnose_ability(request: DiagnosisRequest, user_id: str = "default"):
    """
    初始能力诊断

    基于简单的填空、朗读、听力测试评估用户水平。

    Args:
        request: 诊断答案
        user_id: 用户标识

    Returns:
        诊断等级和建议任务
    """
    # 简化的诊断逻辑
    vocab_score = min(len(request.vocab_answers), 10) * 10  # 假设 10 个单词填空
    listening_score = min(len(request.listening_answers), 5) * 20  # 假设 5 个听力题

    # 综合评分
    overall = (vocab_score + listening_score) / 2

    if overall >= 75:
        level = "advanced"
        vocab_estimate = 4000
        pronunciation_estimate = 75
        listening_estimate = 80
    elif overall >= 50:
        level = "intermediate"
        vocab_estimate = 3000
        pronunciation_estimate = 60
        listening_estimate = 65
    else:
        level = "beginner"
        vocab_estimate = 2000
        pronunciation_estimate = 45
        listening_estimate = 50

    suggested_tasks = DEFAULT_TASKS[level]

    # 保存诊断结果更新用户档案
    db = get_db_session()
    try:
        user = db.query(User).filter(User.user_id == user_id).first()
        if not user:
            # 用户不存在，尝试自动创建（DEV_MODE）
            import os
            dev_mode = os.getenv("DEV_MODE", "false").lower() in ("1", "true", "yes")
            if dev_mode:
                from database.user_db_sqlite import get_user_db
                auth_db = get_user_db()
                auth_user = auth_db.get_user_by_id(user_id)
                if auth_user:
                    user = ensure_orm_user(
                        user_id, auth_user["email"],
                        auth_user.get("password_hash", "")
                    )
        if user:
            user.level = level
            user.vocab_size = vocab_estimate
            user.pronunciation_avg = pronunciation_estimate
            user.listening_avg = listening_estimate
            db.commit()
    finally:
        db.close()

    logger.info(f"能力诊断完成: user={user_id}, level={level}, vocab={vocab_estimate}")

    return DiagnosisResponse(
        level=level,
        vocab_estimate=vocab_estimate,
        pronunciation_estimate=pronunciation_estimate,
        listening_estimate=listening_estimate,
        suggested_tasks=[
            TaskItem(title=t["title"], type=t["type"], duration_min=t["duration_min"])
            for t in suggested_tasks
        ],
        message=f"诊断完成！你的英语水平为 {level} 级，已为你准备好今日任务，开始你的学习之旅吧！🚀"
    )


@router.get("/history", response_model=APIResponse)
async def get_task_history(user_id: str = "default", days: int = 7):
    """获取近期任务历史"""
    from datetime import timedelta

    start_date = date.today() - timedelta(days=days)
    db = get_db_session()

    try:
        user = db.query(User).filter(User.user_id == user_id).first()
        if not user:
            return APIResponse(success=True, data={"tasks": []})

        tasks = db.query(DailyTaskModel).filter(
            DailyTaskModel.user_id == user.id,
            DailyTaskModel.date >= start_date
        ).order_by(DailyTaskModel.date.desc()).all()

        return APIResponse(
            success=True,
            data={
                "tasks": [
                    {
                        "id": t.id,
                        "date": t.date.isoformat(),
                        "task_content": t.task_content,
                        "status": t.status,
                        "time_spent": t.time_spent,
                    }
                    for t in tasks
                ]
            }
        )

    finally:
        db.close()
