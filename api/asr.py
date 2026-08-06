"""ASR 语音识别端点"""

import logging
import base64
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from services.azure_speech_service import get_azure_speech
from services.edge_tts_service import get_tts_service

logger = logging.getLogger("edulingua-asr")

router = APIRouter(prefix="/api/asr", tags=["ASR"])


class ASRRequest(BaseModel):
    """ASR 请求"""
    audio_data: str = ""  # Base64 编码的 WAV 音频
    language: str = "en-US"


class ASRResponse(BaseModel):
    """ASR 响应"""
    text: str
    confidence: float
    language: str


@router.post("/transcribe", response_model=ASRResponse)
async def transcribe_audio(request: ASRRequest):
    """
    语音识别转写

    将录制的语音转为文本，供后续发音评估或对话使用。

    Args:
        request: 包含 base64 音频数据的请求

    Returns:
        转写文本和置信度
    """
    if not request.audio_data:
        raise HTTPException(status_code=400, detail="音频数据不能为空")

    try:
        audio_bytes = base64.b64decode(request.audio_data)
    except Exception:
        raise HTTPException(status_code=400, detail="音频数据 Base64 解码失败")

    azure_speech = get_azure_speech()
    text, confidence = await azure_speech.speech_to_text(audio_bytes, request.language)

    if not text:
        return ASRResponse(
            text="[未识别到语音，请重试]",
            confidence=0.0,
            language=request.language
        )

    logger.info(f"ASR 转写完成: text='{text[:50]}...', confidence={confidence:.2f}")

    return ASRResponse(
        text=text,
        confidence=round(confidence, 2),
        language=request.language
    )


@router.get("/languages")
async def get_supported_languages():
    """获取支持的识别语言"""
    return {
        "languages": [
            {"code": "en-US", "name": "美式英语"},
            {"code": "en-GB", "name": "英式英语"},
            {"code": "zh-CN", "name": "中文普通话"},
        ],
        "default": "en-US"
    }
