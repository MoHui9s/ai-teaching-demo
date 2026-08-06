"""每日任务端点"""

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

logger = logging.getLogger("edulingua-tasks")

router = APIRouter(prefix="/api/tasks", tags=["Tasks"])

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

        # 未生成任务：根据用户水平自动生成
        user = db.query(User).filter(User.user_id == user_id).first()
        level = user.level if user else "beginner"
        tasks = DEFAULT_TASKS.get(level, DEFAULT_TASKS["beginner"])

        new_task = DailyTaskModel(
            user_id=user.id if user else 1,
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
