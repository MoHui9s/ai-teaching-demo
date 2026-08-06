"""
ASR 语音识别 API 路由（阿里云百炼 DashScope）

通过 OpenAI 兼容的多模态接口调用 qwen3-asr-flash 模型，
支持上传音频文件返回转写文本。

API 文档：https://help.aliyun.com/zh/model-studio/qwen-asr-api-reference
"""

import os
import base64
import logging
import tempfile
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse

from openai import OpenAI

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/asr", tags=["asr"])

# 允许的音频格式
ALLOWED_AUDIO_TYPES = {
    "audio/wav", "audio/mpeg", "audio/mp3", "audio/mp4",
    "audio/ogg", "audio/flac", "audio/webm", "audio/x-wav",
    "audio/wave", "audio/m4a", "audio/x-m4a",
}

# 文件扩展名 fallback
ALLOWED_EXTENSIONS = {".wav", ".mp3", ".ogg", ".m4a", ".flac", ".webm", ".opus", ".aac"}


def get_asr_client() -> OpenAI:
    """获取百炼 ASR 客户端"""
    api_key = os.getenv("OPENAI_API_KEY", "")
    base_url = os.getenv("OPENAI_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")

    if not api_key:
        raise HTTPException(
            status_code=503,
            detail="ASR 服务未配置：请在 .env 中设置 OPENAI_API_KEY（百炼 API Key）"
        )

    return OpenAI(api_key=api_key, base_url=base_url)


@router.post("/transcribe")
async def transcribe(
    audio: UploadFile = File(...),
    language: str = "en",
    prompt: Optional[str] = None,
):
    """
    音频转文字（ASR）

    上传音频文件，返回转写文本。

    - **audio**: 音频文件（wav / mp3 / ogg / flac / webm / m4a）
    - **language**: 音频语言代码，默认 "en"（英语），也支持 "zh"（中文）、"ja"（日语）等
    - **prompt**: 可选提示词，提供上下文有助于提升识别准确率

    支持的语言代码：
    zh, en, ja, ko, de, fr, es, pt, ar, it, ru, hi, id, th, tr, uk, vi, yue（粤语）
    """
    # 验证文件类型
    content_type = audio.content_type or ""
    file_ext = Path(audio.filename).suffix.lower() if audio.filename else ""

    if content_type and content_type not in ALLOWED_AUDIO_TYPES:
        if file_ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=415,
                detail=f"不支持的音频格式。允许的格式：{', '.join(ALLOWED_EXTENSIONS)}"
            )

    # 读取并编码音频
    try:
        audio_bytes = await audio.read()
        if not audio_bytes:
            raise HTTPException(status_code=400, detail="音频文件为空")

        audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")

        # 确定 MIME 类型
        if content_type and content_type in ALLOWED_AUDIO_TYPES:
            mime_type = content_type
        elif file_ext == ".mp3":
            mime_type = "audio/mpeg"
        elif file_ext == ".ogg":
            mime_type = "audio/ogg"
        elif file_ext == ".flac":
            mime_type = "audio/flac"
        elif file_ext == ".webm":
            mime_type = "audio/webm"
        elif file_ext in (".m4a", ".aac"):
            mime_type = "audio/mp4"
        else:
            mime_type = "audio/wav"

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"读取音频文件失败: {e}")
        raise HTTPException(status_code=500, detail=f"读取音频文件失败: {str(e)}")

    # 调用百炼 ASR
    model = os.getenv("ASR_MODEL", "qwen3-asr-flash")

    # 构建提示消息
    user_prompt = "请将这段音频转写为文字，只返回转写文本，不要添加任何额外说明。"
    if prompt:
        user_prompt = f"参考以下上下文转写音频——{prompt}。请只返回转写文本。"

    try:
        client = get_asr_client()

        response = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_audio",
                            "input_audio": {
                                "data": audio_b64,
                                "format": mime_type.split("/")[-1],
                            },
                        },
                        {"type": "text", "text": user_prompt},
                    ],
                }
            ],
            max_tokens=1024,
        )

        transcript = response.choices[0].message.content or ""

        return JSONResponse({
            "success": True,
            "data": {
                "text": transcript.strip(),
                "language": language,
                "model": model,
            }
        })

    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        logger.error(f"ASR 调用失败: {error_msg}")

        # 提供更友好的错误提示
        if "api_key" in error_msg.lower() or "authentication" in error_msg.lower():
            raise HTTPException(
                status_code=401,
                detail="百炼 API Key 无效或已过期，请检查 .env 中的 OPENAI_API_KEY"
            )
        elif "model" in error_msg.lower() or "not found" in error_msg.lower():
            raise HTTPException(
                status_code=503,
                detail=f"ASR 模型 {model} 不可用，请检查 ASR_MODEL 配置或模型是否已开通"
            )

        raise HTTPException(status_code=500, detail=f"语音识别失败: {error_msg}")


@router.get("/health")
async def asr_health():
    """ASR 服务健康检查"""
    api_key = os.getenv("OPENAI_API_KEY", "")
    model = os.getenv("ASR_MODEL", "qwen3-asr-flash")

    return {
        "status": "available" if api_key else "unconfigured",
        "model": model,
        "provider": "阿里云百炼 DashScope",
        "formats": list(ALLOWED_EXTENSIONS),
    }
