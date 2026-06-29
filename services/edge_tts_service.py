"""Edge TTS Service - Microsoft Edge Text-to-Speech wrapper."""

import edge_tts
import logging
import io
from typing import Tuple, List, Dict, Any

logger = logging.getLogger("edge-tts")


class EdgeTTSService:
    """
    Microsoft Edge TTS 服务封装

    支持多种英语声音和语速、音量调节。
    """

    # 支持的声音列表
    VOICES = {
        'en-US-AriaNeural': {'name': '美式英语 - 女声 (Aria)', 'lang': 'en-US'},
        'en-US-GuyNeural': {'name': '美式英语 - 男声 (Guy)', 'lang': 'en-US'},
        'en-US-JennyNeural': {'name': '美式英语 - 女声 (Jenny)', 'lang': 'en-US'},
        'en-GB-SoniaNeural': {'name': '英式英语 - 女声 (Sonia)', 'lang': 'en-GB'},
        'en-GB-RyanNeural': {'name': '英式英语 - 男声 (Ryan)', 'lang': 'en-GB'},
        'en-GB-LibbyNeural': {'name': '英式英语 - 女声 (Libby)', 'lang': 'en-GB'},
    }

    DEFAULT_VOICE = 'en-US-AriaNeural'

    def __init__(self):
        """初始化Edge TTS服务"""
        self._available_voices = None
        logger.info("Edge TTS服务初始化完成")

    async def get_available_voices(self) -> List[Dict[str, Any]]:
        """
        获取所有可用声音列表

        Returns:
            声音信息列表
        """
        try:
            if self._available_voices is None:
                voices = await edge_tts.list_voices()
                # 只保留英语声音
                self._available_voices = [
                    v for v in voices
                    if v.get('Locale', '').startswith('en-')
                ]
            return self._available_voices
        except Exception as e:
            logger.error(f"获取声音列表失败: {e}")
            return []

    async def synthesize(
        self,
        text: str,
        voice: str = None,
        rate: str = "+0%",
        volume: str = "+0%"
    ) -> Tuple[bytes, float]:
        """
        合成语音

        Args:
            text: 要合成的文本
            voice: 声音类型，默认使用美式英语Aria
            rate: 语速调节，如 "+10%" (加速), "-10%" (减速)
            volume: 音量调节，如 "+10%" (增大), "-10%" (减小)

        Returns:
            (audio_bytes, duration_seconds) 音频数据和时长
        """
        if voice is None:
            voice = self.DEFAULT_VOICE

        if voice not in self.VOICES:
            logger.warning(f"未知的声音: {voice}，使用默认声音")
            voice = self.DEFAULT_VOICE

        logger.debug(f"合成语音: text='{text[:50]}...', voice={voice}")

        try:
            communicate = edge_tts.Communicate(
                text,
                voice,
                rate=rate,
                volume=volume
            )

            # 收集音频数据
            audio_buffer = io.BytesIO()
            total_bytes = 0

            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    audio_data = chunk["data"]
                    audio_buffer.write(audio_data)
                    total_bytes += len(audio_data)

            audio_data = audio_buffer.getvalue()

            # 计算时长 (MP3 128kbps: 128kb/s = 16KB/s)
            # 这是一个粗略估算，实际时长可能略有不同
            duration = total_bytes / (128 * 1024 / 8)

            logger.debug(f"合成完成: {len(audio_data)} bytes, ~{duration:.2f}s")

            return audio_data, duration

        except Exception as e:
            logger.error(f"语音合成失败: {e}")
            raise

    async def synthesize_with_cache(
        self,
        text: str,
        voice: str = None,
        rate: str = "+0%",
        volume: str = "+0%",
        cache_service=None
    ) -> Tuple[bytes, float]:
        """
        合成语音（带缓存）

        Args:
            text: 要合成的文本
            voice: 声音类型
            rate: 语速调节
            volume: 音量调节
            cache_service: 缓存服务实例

        Returns:
            (audio_bytes, duration_seconds)
        """
        if voice is None:
            voice = self.DEFAULT_VOICE

        # 检查缓存
        if cache_service:
            cached = cache_service.get(text, voice)
            if cached:
                logger.debug(f"缓存命中: {text[:30]}...")
                return cached['data'], cached['duration']

        # 合成新音频
        audio_data, duration = await self.synthesize(text, voice, rate, volume)

        # 存入缓存
        if cache_service:
            cache_service.set(text, voice, audio_data, duration)

        return audio_data, duration

    def get_supported_voices(self) -> Dict[str, str]:
        """
        获取支持的声音列表

        Returns:
            {voice_code: voice_name} 字典
        """
        return {
            code: info['name']
            for code, info in self.VOICES.items()
        }

    def validate_voice(self, voice: str) -> bool:
        """
        验证声音是否支持

        Args:
            voice: 声音代码

        Returns:
            是否支持
        """
        return voice in self.VOICES


# 全局TTS服务实例
_tts_instance: EdgeTTSService = None


def get_tts_service() -> EdgeTTSService:
    """获取全局TTS服务实例"""
    global _tts_instance
    if _tts_instance is None:
        _tts_instance = EdgeTTSService()
    return _tts_instance
