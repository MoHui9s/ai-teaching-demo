"""发音评估端点"""

import logging
import base64
from fastapi import APIRouter, HTTPException

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from services.azure_speech_service import get_azure_speech
from services.edge_tts_service import get_tts_service
from services.cache_service_leveldb import get_cache_service
from api.schemas import (
    PronunciationRequest,
    WordScore,
    PronunciationResponse,
)

import hashlib

logger = logging.getLogger("edulingua-pronunciation")

router = APIRouter(prefix="/api/pronunciation", tags=["Pronunciation"])


@router.post("/evaluate", response_model=PronunciationResponse)
async def evaluate_pronunciation(request: PronunciationRequest):
    """
    发音评估（跟读模式）

    将用户朗读音频与目标文本对齐，逐词评分并标出发音问题。

    Args:
        request: 包含目标文本和音频数据

    Returns:
        逐词评分、整体分、问题音素、示范音频 URL
    """
    if not request.text:
        raise HTTPException(status_code=400, detail="目标文本不能为空")

    if not request.audio_data:
        raise HTTPException(status_code=400, detail="音频数据不能为空")

    try:
        audio_bytes = base64.b64decode(request.audio_data)
    except Exception:
        raise HTTPException(status_code=400, detail="音频数据 Base64 解码失败")

    azure_speech = get_azure_speech()
    result = await azure_speech.evaluate_pronunciation(audio_bytes, request.text)

    # 获取示范音频 URL
    demo_audio_url = ""
    if request.mode == "evaluate" or request.mode == "demo":
        cache_service = get_cache_service()
        tts_service = get_tts_service()
        cache_key = hashlib.md5(f"{request.text}|{tts_service.DEFAULT_VOICE}".encode()).hexdigest()

        # 检查缓存
        if not cache_service.get(request.text, tts_service.DEFAULT_VOICE):
            try:
                audio_data, duration = await tts_service.synthesize(
                    text=request.text,
                    voice=tts_service.DEFAULT_VOICE,
                    rate="-10%"  # 略慢速方便跟读
                )
                cache_service.set(request.text, tts_service.DEFAULT_VOICE, audio_data, duration)
            except Exception as e:
                logger.warning(f"生成示范音频失败: {e}")

        demo_audio_url = f"/api/tts/file/{cache_key}"

    # 生成鼓励语
    overall = result["overall_score"]
    if overall >= 85:
        encouragement = "太棒了！你的发音非常标准，接近母语水平！继续保持！🎉"
    elif overall >= 70:
        encouragement = "很不错！发音基本准确，再注意一下标记的音素就能更上一层楼！💪"
    elif overall >= 55:
        encouragement = "还有进步空间哦！多听示范音频，重点练习标记的发音部位。你可以的！🌟"
    else:
        encouragement = "别灰心！发音是需要大量练习的技能。先放慢语速，一个词一个词来，我陪着你进步！📖"

    # 构建逐词评分
    word_scores = [
        WordScore(
            word=w["word"],
            score=w["score"],
            phonemes=w.get("phonemes", [])
        )
        for w in result.get("word_scores", [])
    ]

    logger.info(f"发音评估完成: score={overall:.0f}, text='{request.text[:30]}...'")

    return PronunciationResponse(
        overall_score=overall,
        accuracy_score=result.get("accuracy_score", overall),
        fluency_score=result.get("fluency_score", overall),
        word_scores=word_scores,
        wrong_phonemes=result.get("wrong_phonemes", []),
        demo_audio_url=demo_audio_url,
        encouragement=encouragement,
    )


@router.get("/tips")
async def get_pronunciation_tips():
    """获取常见发音技巧"""
    return {
        "tips": [
            {
                "phoneme": "th",
                "name": "清齿擦音 /θ/",
                "description": "舌尖放在上下齿之间，气流从缝隙中挤出，声带不振动",
                "example": "think, three, thank",
                "common_error": "常被发成 /s/ 或 /f/",
                "practice_words": ["think", "three", "thank", "both", "mouth"],
            },
            {
                "phoneme": "dh",
                "name": "浊齿擦音 /ð/",
                "description": "与 th 相同口型，但声带振动",
                "example": "this, that, the, they",
                "common_error": "常被发成 /z/ 或 /d/",
                "practice_words": ["this", "that", "the", "they", "mother"],
            },
            {
                "phoneme": "r",
                "name": "卷舌近音 /ɹ/",
                "description": "舌尖卷起靠近上颚，但不接触，嘴唇微微收圆",
                "example": "red, right, run",
                "common_error": "常被发成类似'l'的音，或与中文'r'混淆",
                "practice_words": ["red", "right", "run", "river", "around"],
            },
            {
                "phoneme": "l",
                "name": "齿龈边音 /l/",
                "description": "舌尖抵住上齿龈，气流从舌两侧流出",
                "example": "light, let, like",
                "common_error": "词尾的 dark l 常被省略（如 'well' 发成 'weh'）",
                "practice_words": ["light", "let", "like", "well", "call"],
            },
            {
                "phoneme": "v",
                "name": "唇齿擦音 /v/",
                "description": "上齿轻咬下唇，声带振动",
                "example": "very, five, live",
                "common_error": "常被发成 /w/（双唇音）",
                "practice_words": ["very", "five", "live", "voice", "every"],
            },
        ]
    }
