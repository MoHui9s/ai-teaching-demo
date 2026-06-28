"""
语音服务 API 路由
"""

from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from fastapi.responses import Response, FileResponse
import logging
import tempfile
import os
from typing import Optional

# Add parent directory to path for imports
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from voice import WhisperSTT, KokoroTTS, VoiceProfileManager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/voice", tags=["voice"])

# 全局实例
_stt_engine = None
_tts_engine = None
_profile_manager = None


def get_stt():
    """获取 STT 引擎"""
    global _stt_engine
    if _stt_engine is None:
        _stt_engine = WhisperSTT()
    return _stt_engine


def get_tts():
    """获取 TTS 引擎"""
    global _tts_engine
    if _tts_engine is None:
        _tts_engine = KokoroTTS()
    return _tts_engine


def get_profiles():
    """获取配置管理器"""
    global _profile_manager
    if _profile_manager is None:
        _profile_manager = VoiceProfileManager()
    return _profile_manager


@router.post("/transcribe")
async def transcribe(
    audio: UploadFile = File(...),
    language: str = "en",
    model: str = "medium"
):
    """
    音频转文字

    将音频文件转录为文字。
    """
    stt = get_stt()

    # 验证音频格式
    allowed_extensions = {".wav", ".mp3", ".ogg", ".m4a", ".flac"}
    file_ext = Path(audio.filename).suffix.lower() if audio.filename else ""
    if file_ext and file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported audio format. Allowed: {', '.join(allowed_extensions)}"
        )

    # 保存上传的音频
    with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext or ".wav") as f:
        content = await audio.read()
        f.write(content)
        temp_path = f.name

    try:
        result = stt.transcribe(temp_path, language=language)
        return {"success": True, "data": result}
    except Exception as e:
        logger.error(f"Transcription error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        os.unlink(temp_path)


@router.post("/synthesize")
async def synthesize(request: dict):
    """
    文字转音频

    将文字合成为语音。
    """
    tts = get_tts()

    text = request.get("text")
    voice = request.get("voice", "amanda")
    emotion = request.get("emotion", "neutral")
    profile_id = request.get("profile")
    speed = request.get("speed", 1.0)
    format_type = request.get("format", "wav")

    if not text:
        raise HTTPException(status_code=400, detail="Text is required")

    # 验证文本长度
    if len(text) > 5000:
        raise HTTPException(
            status_code=400,
            detail="Text too long. Maximum 5000 characters."
        )

    try:
        # 如果指定了 profile，从配置获取参数
        if profile_id:
            profiles = get_profiles()
            profile = profiles.load(profile_id)
            if profile:
                # 应用情感参数
                params = profiles.apply_emotion(profile, emotion)
                voice = profile.get("voice_id", voice)
                speed = params.get("speed", speed)
            else:
                logger.warning(f"Profile '{profile_id}' not found, using defaults")

        # 验证 speed 范围
        speed = max(0.5, min(2.0, speed))

        # 生成音频
        audio_bytes = tts.to_bytes(text, voice=voice, speed=speed)

        # 确定媒体类型
        media_type = "audio/mpeg" if format_type == "mp3" else "audio/wav"

        return Response(content=audio_bytes, media_type=media_type)

    except Exception as e:
        logger.error(f"Synthesis error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chat")
async def voice_chat(
    audio: UploadFile = File(...),
    profile: str = "lee",
    history_id: Optional[str] = None
):
    """
    语音对话（一体化）

    自动处理语音识别、AI 处理、语音合成的完整流程。
    """
    stt = get_stt()
    tts = get_tts()
    profiles = get_profiles()

    # 保存上传的音频
    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as f:
        content = await audio.read()
        f.write(content)
        temp_path = f.name

    try:
        # 1. 语音识别
        transcript_result = stt.transcribe(temp_path, language="en")
        transcript = transcript_result["text"]

        # 2. 获取角色配置
        profile_data = profiles.load(profile)
        if not profile_data:
            profile_data = profiles.get_default_profile() or {}

        # 3. TODO: AI 处理 - 这里需要集成 Hermes Agent
        # 目前返回简单响应
        response_text = f"You said: {transcript}"

        # 4. 语音合成
        voice_id = profile_data.get("voice_id", "amanda")
        audio_bytes = tts.to_bytes(response_text, voice=voice_id)

        # 5. 保存音频文件
        import uuid
        audio_id = f"{uuid.uuid4()}.wav"
        audio_dir = Path(__file__).parent.parent / "static" / "audio"
        audio_dir.mkdir(parents=True, exist_ok=True)
        audio_path = audio_dir / audio_id

        with open(audio_path, "wb") as f:
            f.write(audio_bytes)

        return {
            "success": True,
            "data": {
                "transcript": transcript,
                "response": response_text,
                "audio_url": f"/static/audio/{audio_id}",
                "voice_id": voice_id
            }
        }

    except Exception as e:
        logger.error(f"Voice chat error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        os.unlink(temp_path)


@router.get("/voices")
async def list_voices():
    """
    获取可用音色列表

    返回所有可用的音色及其详细信息。
    """
    tts = get_tts()

    voices = []
    for voice_id in tts.list_voices():
        info = tts.get_voice_info(voice_id)
        voices.append({
            "id": info["id"],
            "name": info["id"].capitalize(),
            "gender": info.get("gender", "unknown"),
            "category": info.get("category", "general"),
            "available": info["available"]
        })

    return {"success": True, "data": {"voices": voices}}


@router.get("/profiles")
async def list_profiles():
    """
    获取角色列表

    返回所有可用的角色配置。
    """
    profiles = get_profiles()
    profile_list = profiles.list_all()

    return {"success": True, "data": {"profiles": profile_list}}


@router.get("/profiles/{profile_id}")
async def get_profile(profile_id: str):
    """
    获取角色详情

    返回指定角色的完整配置信息。
    """
    profiles = get_profiles()
    profile = profiles.load(profile_id)

    if not profile:
        raise HTTPException(status_code=404, detail=f"Profile '{profile_id}' not found")

    return {"success": True, "data": profile}


@router.post("/profiles")
async def create_profile(request: dict):
    """
    创建/更新角色

    创建新的角色配置或更新现有角色。
    """
    profiles = get_profiles()

    # 验证配置
    is_valid, errors = profiles.validate_profile(request)
    if not is_valid:
        raise HTTPException(status_code=400, detail={"errors": errors})

    success = profiles.save(request)

    if not success:
        raise HTTPException(status_code=400, detail="Failed to save profile")

    profile_id = request.get("id")
    return {
        "success": True,
        "data": {
            "id": profile_id,
            "created": True
        }
    }


@router.delete("/profiles/{profile_id}")
async def delete_profile(profile_id: str):
    """
    删除角色

    删除指定的角色配置。
    """
    profiles = get_profiles()

    success = profiles.delete(profile_id)

    if not success:
        raise HTTPException(status_code=404, detail=f"Profile '{profile_id}' not found")

    return {"success": True, "data": {"deleted": True}}


@router.get("/audio/{audio_id}")
async def get_audio(audio_id: str):
    """
    获取音频文件

    返回之前生成的音频文件。
    """
    audio_path = Path(__file__).parent.parent / "static" / "audio" / audio_id

    if not audio_path.exists():
        raise HTTPException(status_code=404, detail="Audio file not found")

    return FileResponse(
        path=str(audio_path),
        media_type="audio/wav",
        filename=audio_id
    )


@router.get("/health")
async def health_check():
    """
    健康检查

    检查语音服务是否正常运行。
    """
    status = {
        "stt": _stt_engine is not None,
        "tts": _tts_engine is not None,
        "profiles": _profile_manager is not None
    }

    return {
        "status": "healthy" if all(status.values()) else "degraded",
        "components": status
    }
