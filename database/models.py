"""SQLAlchemy ORM 模型 —— Tan同学-AI英语助教"""

from datetime import datetime
from sqlalchemy import (
    Column, String, Integer, Float, Boolean, DateTime, Date,
    Text, JSON, ForeignKey, create_engine
)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker

Base = declarative_base()


class User(Base):
    """用户档案"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(64), unique=True, nullable=False, index=True)
    name = Column(String(128), default="")
    email = Column(String(256), unique=True, nullable=False)
    password_hash = Column(String(256), nullable=False)
    level = Column(String(16), default="beginner")  # beginner/intermediate/advanced
    vocab_size = Column(Integer, default=2000)
    pronunciation_avg = Column(Float, default=55.0)
    listening_avg = Column(Float, default=60.0)
    streak_days = Column(Integer, default=0)
    total_study_minutes = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关系
    daily_tasks = relationship("DailyTask", back_populates="user", cascade="all, delete-orphan")
    pronunciation_records = relationship("PronunciationRecord", back_populates="user", cascade="all, delete-orphan")
    dialogs = relationship("DialogHistory", back_populates="user", cascade="all, delete-orphan")
    progress = relationship("DailyProgress", back_populates="user", cascade="all, delete-orphan")
    achievements = relationship("Achievement", back_populates="user", cascade="all, delete-orphan")


class DailyTask(Base):
    """每日任务记录"""
    __tablename__ = "daily_tasks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    date = Column(Date, nullable=False, index=True)
    task_content = Column(JSON, nullable=False)  # [{"title": "...", "type": "vocab/speaking/listening", "duration_min": 10, "status": "pending/done"}]
    status = Column(String(16), default="pending")  # pending/in_progress/completed
    time_spent = Column(Integer, default=0)  # 实际用时（分钟）
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="daily_tasks")


class PronunciationRecord(Base):
    """发音练习记录"""
    __tablename__ = "pronunciation_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    input_text = Column(Text, nullable=False)  # 目标文本
    user_audio_url = Column(String(512), default="")  # 用户录音 URL
    score = Column(Float, default=0.0)  # 整体评分 0-100
    word_scores = Column(JSON, default=dict)  # {"word": score, ...}
    wrong_phonemes = Column(JSON, default=list)  # [{"phoneme": "th", "word": "think", "suggestion": "..."}]
    fluency_score = Column(Float, default=0.0)
    accuracy_score = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="pronunciation_records")


class DialogHistory(Base):
    """对话历史"""
    __tablename__ = "dialog_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    scene_type = Column(String(64), nullable=False)  # restaurant/interview/classroom/...
    difficulty = Column(String(16), default="easy")  # easy/medium/hard
    messages = Column(JSON, nullable=False)  # [{"role": "user/assistant", "content": "..."}]
    grammar_feedback = Column(JSON, default=dict)  # AI 语法纠错结果
    duration_seconds = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="dialogs")


class DailyProgress(Base):
    """学习进度快照（每日汇总）"""
    __tablename__ = "daily_progress"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    date = Column(Date, nullable=False, index=True)
    total_minutes = Column(Integer, default=0)
    new_words = Column(Integer, default=0)
    avg_pronounce_score = Column(Float, default=0.0)
    tasks_completed = Column(Integer, default=0)
    dialogs_count = Column(Integer, default=0)
    streak_days = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="progress")


class Achievement(Base):
    """成就徽章"""
    __tablename__ = "achievements"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    achievement_type = Column(String(64), nullable=False)  # streak_7/pronounce_20/study_10h/...
    achievement_name = Column(String(128), default="")
    description = Column(String(256), default="")
    unlocked_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="achievements")


class WeeklyReport(Base):
    """周报记录"""
    __tablename__ = "weekly_reports"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    week_start = Column(Date, nullable=False)
    week_end = Column(Date, nullable=False)
    report_content = Column(Text, default="")  # AI 生成的周报
    highlights = Column(JSON, default=list)  # 本周亮点
    weaknesses = Column(JSON, default=list)  # 薄弱环节
    next_week_suggestions = Column(JSON, default=list)  # 下周建议
    created_at = Column(DateTime, default=datetime.utcnow)


class VocabProgress(Base):
    """词汇学习进度"""
    __tablename__ = "vocab_progress"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    word = Column(String(100), nullable=False)
    level = Column(String(20), nullable=False)  # beginner / intermediate / advanced
    known = Column(Boolean, default=False)       # True=认识, False=不认识
    created_at = Column(DateTime, default=datetime.utcnow)


# 预置成就列表
PRESET_ACHIEVEMENTS = [
    {"type": "streak_3", "name": "初露锋芒", "description": "连续学习 3 天"},
    {"type": "streak_7", "name": "坚持不懈", "description": "连续学习 7 天"},
    {"type": "streak_30", "name": "学习达人", "description": "连续学习 30 天"},
    {"type": "pronounce_20", "name": "口语新星", "description": "完成 20 次发音练习"},
    {"type": "pronounce_100", "name": "发音大师", "description": "完成 100 次发音练习"},
    {"type": "study_10h", "name": "勤学苦练", "description": "累计学习 10 小时"},
    {"type": "study_50h", "name": "学霸本霸", "description": "累计学习 50 小时"},
    {"type": "vocab_100", "name": "词汇达人", "description": "累计学习 100 个新词"},
    {"type": "vocab_500", "name": "单词狂魔", "description": "累计学习 500 个新词"},
    {"type": "dialog_10", "name": "社交能手", "description": "完成 10 次场景对话"},
    {"type": "score_80", "name": "发音突破", "description": "发音平均分达到 80 分"},
    {"type": "first_task", "name": "初次启程", "description": "完成第一个每日任务"},
]
