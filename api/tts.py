"""TTS API routes for Hermes Agent."""

import logging
import hashlib
from fastapi import APIRouter, HTTPException, Response
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from services.edge_tts_service import get_tts_service
from services.cache_service_leveldb import get_cache_service

logger = logging.getLogger("hermes-tts")

router = APIRouter(prefix="/api/tts", tags=["TTS"])


class TTSRequest(BaseModel):
    """TTS请求模型"""
    text: str
    voice: Optional[str] = "en-US-AriaNeural"
    rate: Optional[str] = "+0%"
    volume: Optional[str] = "+0%"


class TTSResponse(BaseModel):
    """TTS响应模型"""
    audio_url: str
    cached: bool
    duration: float
    voice: str


class VoicesResponse(BaseModel):
    """声音列表响应"""
    voices: dict


@router.post("/audio", response_model=TTSResponse)
async def get_tts_audio(request: TTSRequest):
    """
    获取TTS音频

    - 如果缓存命中，直接返回缓存URL
    - 如果缓存未命中，调用Edge TTS生成并缓存

    Args:
        request: TTS请求，包含text、voice等参数

    Returns:
        TTS响应，包含audio_url、cached、duration等信息
    """
    if not request.text or not request.text.strip():
        raise HTTPException(status_code=400, detail="文本不能为空")

    # 验证声音类型
    tts_service = get_tts_service()
    if not tts_service.validate_voice(request.voice):
        logger.warning(f"不支持的声音: {request.voice}，使用默认声音")
        request.voice = tts_service.DEFAULT_VOICE

    # 获取缓存服务
    cache_service = get_cache_service()

    # 生成缓存键（用于URL）
    cache_key = hashlib.md5(f"{request.text}|{request.voice}".encode()).hexdigest()

    # 检查缓存
    cached_audio = cache_service.get(request.text, request.voice)
    if cached_audio:
        logger.debug(f"缓存命中: {request.text[:30]}...")
        return TTSResponse(
            audio_url=f"/api/tts/file/{cache_key}",
            cached=True,
            duration=cached_audio['duration'],
            voice=request.voice
        )

    # 调用Edge TTS生成音频
    try:
        audio_data, duration = await tts_service.synthesize(
            text=request.text,
            voice=request.voice,
            rate=request.rate,
            volume=request.volume
        )

        # 存入缓存
        cache_service.set(request.text, request.voice, audio_data, duration)

        return TTSResponse(
            audio_url=f"/api/tts/file/{cache_key}",
            cached=False,
            duration=duration,
            voice=request.voice
        )

    except Exception as e:
        logger.error(f"TTS合成失败: {e}")
        raise HTTPException(status_code=500, detail=f"TTS合成失败: {str(e)}")


@router.get("/file/{cache_key}")
async def get_audio_file(cache_key: str):
    """
    返回音频文件

    Args:
        cache_key: 缓存键（MD5哈希）

    Returns:
        音频文件响应（MP3格式）
    """
    cache_service = get_cache_service()

    # cache_key 就是 MD5(text|voice)，也是 LevelDB 中的键
    # 直接用它来查找
    key_bytes = cache_key.encode('utf-8')

    # 获取音频数据
    audio_data = cache_service.db.get(key_bytes)
    if audio_data is None:
        raise HTTPException(status_code=404, detail="音频未找到")

    # 获取元数据
    meta_key = cache_service.META_PREFIX + key_bytes
    meta_bytes = cache_service.db.get(meta_key)

    return Response(
        content=audio_data,
        media_type="audio/mpeg",
        headers={
            "Content-Disposition": f"inline; filename={cache_key}.mp3",
            "Cache-Control": "public, max-age=31536000"  # 缓存一年
        }
    )


@router.get("/voices", response_model=VoicesResponse)
async def get_voices():
    """
    获取支持的声音列表

    Returns:
        声音代码和名称的字典
    """
    tts_service = get_tts_service()
    return VoicesResponse(voices=tts_service.get_supported_voices())


@router.get("/stats")
async def get_cache_stats():
    """
    获取缓存统计信息

    Returns:
        缓存统计，包括条目数、总大小等
    """
    cache_service = get_cache_service()
    return cache_service.get_stats()


@router.delete("/cache")
async def clear_cache():
    """
    清空TTS缓存

    Returns:
        操作结果
    """
    cache_service = get_cache_service()
    count = cache_service.clear_all()
    return {
        "status": "success",
        "message": f"已清空 {count} 条缓存"
    }
