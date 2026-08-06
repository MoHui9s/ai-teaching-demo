"""API Schemas —— Tan同学-AI英语助教"""

from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any
from datetime import date, datetime


# =============================================================================
# 聊天（兼容 OpenAI 格式）
# =============================================================================

class ChatMessage(BaseModel):
    """聊天消息"""
    role: str = Field(..., description="消息角色: user / assistant / system")
    content: str = Field(..., description="消息内容")


class ChatRequest(BaseModel):
    """聊天请求（OpenAI 兼容）"""
    model: str = Field(default="tan-english-tutor", description="模型名称")
    messages: List[ChatMessage] = Field(..., description="对话消息列表")
    user_id: str = Field(default="default", description="用户标识")
    stream: bool = Field(default=False, description="是否流式输出")
    temperature: Optional[float] = Field(default=None)
    max_tokens: Optional[int] = Field(default=None)
    tools: Optional[List[Dict[str, Any]]] = Field(default=None)


class ChatCompletion(BaseModel):
    """聊天完成响应"""
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: List[Dict[str, Any]]
    usage: Dict[str, int]


class ErrorResponse(BaseModel):
    """错误响应"""
    error: Dict[str, Any]


# =============================================================================
# 用户认证
# =============================================================================

class LoginRequest(BaseModel):
    """登录请求"""
    email: str
    password: str


class RegisterRequest(BaseModel):
    """注册请求"""
    email: str
    password: str
    name: str = ""


class LoginResponse(BaseModel):
    """登录响应"""
    access_token: str
    user_id: str
    email: str
    name: str = ""


class UserProfile(BaseModel):
    """用户档案"""
    user_id: str
    name: str
    email: str
    level: str
    vocab_size: int
    pronunciation_avg: float
    listening_avg: float
    streak_days: int
    total_study_minutes: int
    created_at: Optional[datetime] = None


# =============================================================================
# 每日任务
# =============================================================================

class TaskItem(BaseModel):
    """单个任务项"""
    title: str
    type: str  # vocab / speaking / listening / reading / writing
    duration_min: int
    status: str = "pending"  # pending / in_progress / done


class DailyTaskResponse(BaseModel):
    """每日任务响应"""
    id: int
    date: str
    task_content: List[TaskItem]
    status: str
    time_spent: int


class TaskCompleteRequest(BaseModel):
    """完成任务请求"""
    task_index: int  # 完成第几个子任务
    time_spent_min: int = 0


class DiagnosisRequest(BaseModel):
    """能力诊断请求"""
    # 诊断结果（简单填空 + 选择）
    vocab_answers: List[str] = []  # 单词填空答案
    pronunciation_text: str = ""  # 朗读文本
    listening_answers: List[str] = []  # 听力选择答案


class DiagnosisResponse(BaseModel):
    """能力诊断响应"""
    level: str  # beginner / intermediate / advanced
    vocab_estimate: int
    pronunciation_estimate: int
    listening_estimate: int
    suggested_tasks: List[TaskItem]
    message: str


# =============================================================================
# 场景对话
# =============================================================================

class ScenarioInfo(BaseModel):
    """场景信息"""
    id: str
    name: str
    description: str
    difficulty: str  # easy / medium / hard
    roles: List[str]  # NPC 角色列表
    learning_goals: List[str]


class DialogRequest(BaseModel):
    """对话请求"""
    scene_type: str = "restaurant"  # 场景类型
    difficulty: str = "easy"


class DialogMessage(BaseModel):
    """对话消息"""
    role: str  # user / assistant / system
    content: str


class DialogResponse(BaseModel):
    """对话响应"""
    messages: List[DialogMessage]
    grammar_feedback: Optional[Dict] = None  # 对话结束后的语法反馈
    scene: ScenarioInfo


# =============================================================================
# 学习进度
# =============================================================================

class ProgressOverview(BaseModel):
    """学习进度概览"""
    streak_days: int
    week_total_minutes: int
    month_total_minutes: int
    vocab_growth: List[Dict[str, Any]]  # [{"date": "...", "count": 100}]
    pronunciation_trend: List[Dict[str, Any]]  # [{"date": "...", "score": 75}]
    recent_activities: List[Dict[str, Any]]
    heatmap_data: Dict[str, int]  # {"2026-08-06": 25} 分钟


class WeeklyReportResponse(BaseModel):
    """周报响应"""
    week_start: str
    week_end: str
    highlights: List[str]
    weaknesses: List[str]
    next_week_suggestions: List[str]
    report_content: str


# =============================================================================
# 成就系统
# =============================================================================

class AchievementInfo(BaseModel):
    """成就信息"""
    type: str
    name: str
    description: str
    unlocked: bool
    unlocked_at: Optional[str] = None
    progress: Optional[Dict[str, Any]] = None  # {"current": 3, "target": 7}


class AchievementListResponse(BaseModel):
    """成就列表响应"""
    achievements: List[AchievementInfo]
    total_unlocked: int
    total_count: int


# =============================================================================
# TTS
# =============================================================================

class TTSRequest(BaseModel):
    """TTS 请求"""
    text: str
    voice: Optional[str] = "en-US-AriaNeural"
    rate: Optional[str] = "+0%"  # 语速，如 "+10%" / "-20%"
    volume: Optional[str] = "+0%"


class TTSResponse(BaseModel):
    """TTS 响应"""
    audio_url: str
    cached: bool
    duration: float
    voice: str


# =============================================================================
# 通用
# =============================================================================

class APIResponse(BaseModel):
    """通用 API 响应"""
    success: bool = True
    message: str = ""
    data: Optional[Any] = None
