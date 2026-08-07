"""学习进度与看板端点"""

import logging
from datetime import date, datetime, timedelta
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from database.database import get_db_session
from database.models import (
    User, DailyTask, PronunciationRecord, DialogHistory,
    DailyProgress, WeeklyReport,
)
from api.schemas import ProgressOverview, WeeklyReportResponse, APIResponse
from api._user_sync import ensure_orm_user

logger = logging.getLogger("edulingua-progress")

router = APIRouter(prefix="/api/progress", tags=["Progress"])


@router.get("/overview", response_model=APIResponse)
async def get_progress_overview(user_id: str = "default"):
    """获取学习进度概览（热力图 + 趋势数据）"""
    db = get_db_session()
    today = date.today()

    try:
        user = db.query(User).filter(User.user_id == user_id).first()
        if not user:
            return APIResponse(success=True, data={})

        # 连续打卡天数
        streak = _calculate_streak(db, user.id)

        # 本周学习时长
        week_start = today - timedelta(days=today.weekday())
        week_progress = db.query(func.sum(DailyProgress.total_minutes)).filter(
            DailyProgress.user_id == user.id,
            DailyProgress.date >= week_start
        ).scalar() or 0

        # 本月学习时长
        month_start = today.replace(day=1)
        month_progress = db.query(func.sum(DailyProgress.total_minutes)).filter(
            DailyProgress.user_id == user.id,
            DailyProgress.date >= month_start
        ).scalar() or 0

        # 词汇量增长趋势（近 30 天）
        vocab_growth = []
        for i in range(30, -1, -1):
            d = today - timedelta(days=i)
            progress = db.query(DailyProgress).filter(
                DailyProgress.user_id == user.id,
                DailyProgress.date == d
            ).first()
            vocab_growth.append({
                "date": d.isoformat(),
                "count": progress.new_words if progress else 0,
            })

        # 发音分趋势（近 30 天）
        pronunciation_trend = []
        for i in range(30, -1, -1):
            d = today - timedelta(days=i)
            records = db.query(PronunciationRecord).filter(
                PronunciationRecord.user_id == user.id,
                func.date(PronunciationRecord.created_at) == d
            ).all()
            if records:
                avg = sum(r.score for r in records) / len(records)
            else:
                avg = 0
            pronunciation_trend.append({
                "date": d.isoformat(),
                "score": round(avg, 1),
            })

        # 热力图数据（近 90 天）
        heatmap_data = {}
        for i in range(90):
            d = today - timedelta(days=i)
            progress = db.query(DailyProgress).filter(
                DailyProgress.user_id == user.id,
                DailyProgress.date == d
            ).first()
            heatmap_data[d.isoformat()] = progress.total_minutes if progress else 0

        # 最近活动
        recent_tasks = db.query(DailyTask).filter(
            DailyTask.user_id == user.id
        ).order_by(DailyTask.date.desc()).limit(5).all()

        recent_activities = [
            {
                "type": "task",
                "date": t.date.isoformat(),
                "summary": f"完成 {sum(1 for item in t.task_content if item.get('status') == 'done')}/{len(t.task_content)} 项任务",
                "time_spent": t.time_spent,
            }
            for t in recent_tasks
        ]

        return APIResponse(
            success=True,
            data={
                "streak_days": streak,
                "week_total_minutes": week_progress,
                "month_total_minutes": month_progress,
                "vocab_growth": vocab_growth,
                "pronunciation_trend": pronunciation_trend,
                "heatmap_data": heatmap_data,
                "recent_activities": recent_activities,
            }
        )

    finally:
        db.close()


@router.get("/weekly-report", response_model=APIResponse)
async def get_weekly_report(
    user_id: str = "default",
    week_start: Optional[str] = None
):
    """获取周报"""
    from services.report_service import get_report_service

    db = get_db_session()
    today = date.today()

    if week_start:
        ws = date.fromisoformat(week_start)
    else:
        ws = today - timedelta(days=today.weekday())  # 本周一

    we = ws + timedelta(days=6)

    try:
        user = db.query(User).filter(User.user_id == user_id).first()
        if not user:
            return APIResponse(
                success=True,
                message="请先完成能力诊断，解锁周报功能",
                data=None
            )

        # 获取本周进度
        progress_records = db.query(DailyProgress).filter(
            DailyProgress.user_id == user.id,
            DailyProgress.date >= ws,
            DailyProgress.date <= we
        ).all()

        # 获取发音记录
        pronunciation_records = db.query(PronunciationRecord).filter(
            PronunciationRecord.user_id == user.id,
            func.date(PronunciationRecord.created_at) >= ws,
            func.date(PronunciationRecord.created_at) <= we
        ).all()

        # 获取对话记录
        dialog_records = db.query(DialogHistory).filter(
            DialogHistory.user_id == user.id,
            func.date(DialogHistory.created_at) >= ws,
            func.date(DialogHistory.created_at) <= we
        ).all()

        # 获取任务记录
        task_records = db.query(DailyTask).filter(
            DailyTask.user_id == user.id,
            DailyTask.date >= ws,
            DailyTask.date <= we
        ).all()

        report_service = get_report_service()

        report = report_service.generate_weekly_report(
            user_id=user_id,
            week_start=ws,
            week_end=we,
            daily_progress=[_row_to_dict(p) for p in progress_records],
            pronunciation_records=[_row_to_dict(p) for p in pronunciation_records],
            dialog_records=[_row_to_dict(d) for d in dialog_records],
            task_records=[_row_to_dict(t) for t in task_records],
        )

        return APIResponse(success=True, data=report)

    finally:
        db.close()


@router.get("/reports", response_model=APIResponse)
async def get_all_reports(user_id: str = "default"):
    """获取用户所有历史周报"""
    from services.report_service import get_report_service

    report_service = get_report_service()
    reports = report_service.load_all_reports(user_id)

    return APIResponse(
        success=True,
        data={"reports": reports}
    )


def _calculate_streak(db: Session, user_pk: int) -> int:
    """计算连续打卡天数"""
    today = date.today()
    streak = 0
    for i in range(365):
        d = today - timedelta(days=i)
        progress = db.query(DailyProgress).filter(
            DailyProgress.user_id == user_pk,
            DailyProgress.date == d,
            DailyProgress.total_minutes > 0
        ).first()
        if progress:
            streak += 1
        else:
            break
    return streak


def _row_to_dict(row) -> dict:
    """SQLAlchemy 行转字典"""
    if row is None:
        return {}
    if hasattr(row, '__dict__'):
        d = {k: v for k, v in row.__dict__.items() if not k.startswith('_')}
        for k, v in d.items():
            if isinstance(v, (date, datetime)):
                d[k] = v.isoformat()
        return d
    return dict(row)
