"""成就系统端点"""

import logging
from fastapi import APIRouter
from sqlalchemy.orm import Session

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from database.database import get_db_session
from database.models import User, Achievement, DailyTask, PronunciationRecord, DialogHistory, DailyProgress, PRESET_ACHIEVEMENTS
from api.schemas import AchievementInfo, APIResponse

logger = logging.getLogger("edulingua-achievements")

router = APIRouter(prefix="/api/achievements", tags=["Achievements"])


@router.get("/list", response_model=APIResponse)
async def get_achievements(user_id: str = "default"):
    """获取成就列表（含解锁状态和进度）"""
    db = get_db_session()

    try:
        user = db.query(User).filter(User.user_id == user_id).first()
        if not user:
            return APIResponse(success=True, data={"achievements": [], "total_unlocked": 0, "total_count": len(PRESET_ACHIEVEMENTS)})

        # 已解锁的成就
        unlocked = {
            a.achievement_type: a
            for a in db.query(Achievement).filter(Achievement.user_id == user.id).all()
        }

        # 计算进度
        total_tasks = db.query(DailyTask).filter(DailyTask.user_id == user.id).count()
        total_pronounce = db.query(PronunciationRecord).filter(PronunciationRecord.user_id == user.id).count()
        total_dialogs = db.query(DialogHistory).filter(DialogHistory.user_id == user.id).count()

        achievements = []
        for preset in PRESET_ACHIEVEMENTS:
            is_unlocked = preset["type"] in unlocked
            progress = _get_progress(
                preset["type"],
                user=user,
                total_tasks=total_tasks,
                total_pronounce=total_pronounce,
                total_dialogs=total_dialogs
            )
            achievements.append({
                "type": preset["type"],
                "name": preset["name"],
                "description": preset["description"],
                "unlocked": is_unlocked,
                "unlocked_at": unlocked[preset["type"]].unlocked_at.isoformat()
                if is_unlocked and unlocked[preset["type"]].unlocked_at else None,
                "progress": progress,
            })

        total_unlocked = len(unlocked)

        return APIResponse(
            success=True,
            data={
                "achievements": achievements,
                "total_unlocked": total_unlocked,
                "total_count": len(PRESET_ACHIEVEMENTS),
            }
        )

    finally:
        db.close()


@router.post("/check", response_model=APIResponse)
async def check_and_unlock_achievements(user_id: str = "default"):
    """检查并解锁新成就"""
    db = get_db_session()

    try:
        user = db.query(User).filter(User.user_id == user_id).first()
        if not user:
            return APIResponse(success=False, message="用户不存在")

        total_tasks = db.query(DailyTask).filter(DailyTask.user_id == user.id).count()
        total_pronounce = db.query(PronunciationRecord).filter(PronunciationRecord.user_id == user.id).count()
        total_dialogs = db.query(DialogHistory).filter(DialogHistory.user_id == user.id).count()

        # 已解锁列表
        unlocked_types = {
            a.achievement_type
            for a in db.query(Achievement).filter(Achievement.user_id == user.id).all()
        }

        new_unlocks = []

        # 检查各类成就条件
        checks = {
            "streak_3": user.streak_days >= 3,
            "streak_7": user.streak_days >= 7,
            "streak_30": user.streak_days >= 30,
            "pronounce_20": total_pronounce >= 20,
            "pronounce_100": total_pronounce >= 100,
            "study_10h": user.total_study_minutes >= 600,  # 10 小时 = 600 分钟
            "study_50h": user.total_study_minutes >= 3000,
            "vocab_100": user.vocab_size >= 2100,  # 初始 2000 + 100
            "vocab_500": user.vocab_size >= 2500,
            "dialog_10": total_dialogs >= 10,
            "score_80": user.pronunciation_avg >= 80,
            "first_task": total_tasks >= 1,
        }

        for achievement_type, condition in checks.items():
            if condition and achievement_type not in unlocked_types:
                preset = next((a for a in PRESET_ACHIEVEMENTS if a["type"] == achievement_type), None)
                if preset:
                    new_achievement = Achievement(
                        user_id=user.id,
                        achievement_type=achievement_type,
                        achievement_name=preset["name"],
                        description=preset["description"],
                    )
                    db.add(new_achievement)
                    new_unlocks.append(preset)
                    logger.info(f"解锁成就: {user_id} -> {preset['name']}")

        db.commit()

        return APIResponse(
            success=True,
            message=f"解锁了 {len(new_unlocks)} 个新成就！" if new_unlocks else "暂无新成就",
            data={
                "new_unlocks": [
                    {"type": a["type"], "name": a["name"], "description": a["description"]}
                    for a in new_unlocks
                ]
            }
        )

    finally:
        db.close()


def _get_progress(achievement_type: str, user, total_tasks: int, total_pronounce: int, total_dialogs: int):
    """计算成就进度"""
    progress_map = {
        "streak_3": {"current": user.streak_days, "target": 3},
        "streak_7": {"current": user.streak_days, "target": 7},
        "streak_30": {"current": user.streak_days, "target": 30},
        "pronounce_20": {"current": total_pronounce, "target": 20},
        "pronounce_100": {"current": total_pronounce, "target": 100},
        "study_10h": {"current": user.total_study_minutes // 60, "target": 10},
        "study_50h": {"current": user.total_study_minutes // 60, "target": 50},
        "vocab_100": {"current": max(0, user.vocab_size - 2000), "target": 100},
        "vocab_500": {"current": max(0, user.vocab_size - 2000), "target": 500},
        "dialog_10": {"current": total_dialogs, "target": 10},
        "score_80": {"current": round(user.pronunciation_avg, 0), "target": 80},
        "first_task": {"current": min(total_tasks, 1), "target": 1},
    }
    return progress_map.get(achievement_type)
