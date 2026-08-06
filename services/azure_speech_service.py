"""Azure 语音服务 —— ASR + 发音评估 + TTS"""

import os
import io
import logging
from typing import Optional, Tuple, Dict, Any, List
from pathlib import Path

logger = logging.getLogger("azure-speech")

# 尝试导入 Azure SDK（可选依赖，未配置时降级）
try:
    import azure.cognitiveservices.speech as speechsdk
    AZURE_SDK_AVAILABLE = True
except ImportError:
    AZURE_SDK_AVAILABLE = False
    logger.warning("Azure Speech SDK 未安装，语音服务将返回模拟数据")


class AzureSpeechService:
    """Azure 语音服务封装：ASR 语音识别 + 发音评估 + TTS"""

    def __init__(self):
        self.speech_key = os.getenv("AZURE_SPEECH_KEY", "")
        self.speech_region = os.getenv("AZURE_SPEECH_REGION", "eastasia")
        self.tts_key = os.getenv("AZURE_TTS_KEY", "") or self.speech_key
        self.tts_region = os.getenv("AZURE_TTS_REGION", "eastasia") or self.speech_region
        self.available = bool(self.speech_key) and AZURE_SDK_AVAILABLE

        if self.available:
            logger.info(f"Azure 语音服务已配置 (region={self.speech_region})")
        else:
            logger.warning("Azure 语音服务未配置密钥或 SDK 未安装，使用模拟模式")

    def _get_speech_config(self) -> Optional[Any]:
        """获取 Azure Speech 配置"""
        if not self.available:
            return None
        config = speechsdk.SpeechConfig(
            subscription=self.speech_key,
            region=self.speech_region
        )
        return config

    async def speech_to_text(self, audio_data: bytes, language: str = "en-US") -> Tuple[str, float]:
        """
        ASR 语音识别

        Args:
            audio_data: WAV 音频数据
            language: 识别语言

        Returns:
            (转写文本, 置信度 0-1)
        """
        config = self._get_speech_config()
        if not config:
            # 模拟模式：返回占位结果
            return "[模拟转写] This is a simulated transcription.", 0.85

        try:
            config.speech_recognition_language = language
            audio_stream = speechsdk.audio.PushAudioInputStream()
            audio_config = speechsdk.audio.AudioConfig(stream=audio_stream)
            recognizer = speechsdk.SpeechRecognizer(
                speech_config=config,
                audio_config=audio_config
            )

            audio_stream.write(audio_data)
            audio_stream.close()

            result = recognizer.recognize_once_async().get()

            if result.reason == speechsdk.ResultReason.RecognizedSpeech:
                confidence = result.properties.get(
                    speechsdk.PropertyId.SpeechServiceResponse_JsonResult
                )
                return result.text, 0.9
            elif result.reason == speechsdk.ResultReason.NoMatch:
                return "", 0.0
            else:
                logger.error(f"ASR 识别失败: {result.reason}")
                return "", 0.0

        except Exception as e:
            logger.error(f"ASR 异常: {e}")
            return "", 0.0

    async def evaluate_pronunciation(
        self,
        audio_data: bytes,
        reference_text: str,
        language: str = "en-US"
    ) -> Dict[str, Any]:
        """
        发音评估

        Args:
            audio_data: WAV 音频数据
            reference_text: 参考文本（标准答案）
            language: 语言

        Returns:
            {
                "overall_score": 85.0,
                "accuracy_score": 82.0,
                "fluency_score": 88.0,
                "completeness_score": 90.0,
                "word_scores": [
                    {"word": "think", "score": 60.0, "phonemes": ["th", "i", "ng", "k"]},
                    ...
                ],
                "wrong_phonemes": [
                    {"phoneme": "th", "word": "think", "suggestion": "舌尖放在上下齿之间"}
                ]
            }
        """
        config = self._get_speech_config()
        if not config or not reference_text:
            # 模拟模式：返回模拟评分
            return self._mock_pronunciation_evaluation(reference_text)

        try:
            # 创建发音评估配置
            pronunciation_config = speechsdk.PronunciationAssessmentConfig(
                reference_text=reference_text,
                grading_system=speechsdk.PronunciationAssessmentGradingSystem.HundredMark,
                granularity=speechsdk.PronunciationAssessmentGranularity.Word,
                enable_miscue=True
            )
            pronunciation_config.enable_prosody_assessment()

            audio_stream = speechsdk.audio.PushAudioInputStream()
            audio_config = speechsdk.audio.AudioConfig(stream=audio_stream)
            recognizer = speechsdk.SpeechRecognizer(
                speech_config=config,
                audio_config=audio_config,
                language=language
            )

            pronunciation_config.apply_to(recognizer)

            audio_stream.write(audio_data)
            audio_stream.close()

            result = recognizer.recognize_once_async().get()

            if result.reason == speechsdk.ResultReason.RecognizedSpeech:
                pronunciation_result = speechsdk.PronunciationAssessmentResult(result)

                word_scores = []
                wrong_phonemes = []

                # 逐词分析
                for word in pronunciation_result.words:
                    word_info = {
                        "word": word.word,
                        "score": word.accuracy_score,
                        "phonemes": []
                    }
                    if hasattr(word, 'phonemes'):
                        for p in word.phonemes:
                            word_info["phonemes"].append(p.phoneme)
                            if hasattr(p, 'accuracy_score') and p.accuracy_score < 60:
                                wrong_phonemes.append({
                                    "phoneme": p.phoneme,
                                    "word": word.word,
                                    "suggestion": self._get_phoneme_tip(p.phoneme),
                                    "score": p.accuracy_score
                                })
                    word_scores.append(word_info)

                return {
                    "overall_score": pronunciation_result.pronunciation_score,
                    "accuracy_score": pronunciation_result.accuracy_score,
                    "fluency_score": pronunciation_result.fluency_score,
                    "completeness_score": pronunciation_result.completeness_score,
                    "word_scores": word_scores,
                    "wrong_phonemes": wrong_phonemes,
                }
            else:
                return self._mock_pronunciation_evaluation(reference_text)

        except Exception as e:
            logger.error(f"发音评估异常: {e}")
            return self._mock_pronunciation_evaluation(reference_text)

    def _mock_pronunciation_evaluation(self, reference_text: str) -> Dict[str, Any]:
        """模拟发音评估（开发/无密钥时使用）"""
        import random
        random.seed(hash(reference_text) % (2**31))

        words = reference_text.split()
        word_scores = []
        wrong_phonemes = []

        # 常见中国学生发音错误音素
        common_errors = {
            "th": "舌尖轻触上齿，气流从舌齿间挤出",
            "r": "舌尖卷起靠近上颚，不要发成类似'l'的音",
            "l": "舌尖抵住上齿龈，不要与'r'混淆",
            "v": "上齿轻咬下唇，不要发成'w'",
            "w": "双唇收圆，不要发成'v'",
        }

        for word in words:
            score = random.uniform(50, 98)
            word_scores.append({
                "word": word,
                "score": round(score, 1),
                "phonemes": list(word.lower())[:3]
            })

            # 对包含常见错误音素的词随机生成纠错
            word_lower = word.lower()
            for phoneme, tip in common_errors.items():
                if phoneme in word_lower and random.random() < 0.3:
                    wrong_phonemes.append({
                        "phoneme": phoneme,
                        "word": word,
                        "suggestion": tip,
                        "score": round(random.uniform(30, 55), 1)
                    })

        overall = round(sum(w["score"] for w in word_scores) / max(len(word_scores), 1), 1)

        return {
            "overall_score": overall,
            "accuracy_score": round(overall * random.uniform(0.9, 1.05), 1),
            "fluency_score": round(overall * random.uniform(0.85, 1.1), 1),
            "completeness_score": round(random.uniform(85, 100), 1),
            "word_scores": word_scores,
            "wrong_phonemes": wrong_phonemes,
            "simulated": True,
        }

    def _get_phoneme_tip(self, phoneme: str) -> str:
        """获取发音提示"""
        tips = {
            "th": "舌尖轻触上齿，气流从舌齿间挤出（think/this）",
            "dh": "舌尖轻触上齿，声带振动（this/that）",
            "r": "舌尖卷起靠近上颚，不要发成类似'l'的音",
            "l": "舌尖抵住上齿龈，不要与'r'混淆",
            "v": "上齿轻咬下唇，声带振动，不要发成'w'",
            "w": "双唇收圆后迅速张开，不要发成'v'",
            "ae": "嘴巴张大，舌位放低（cat/bad）",
            "ih": "嘴巴微张，舌位放松（sit/big）",
            "iy": "嘴角向两边拉开，舌位抬高（see/eat）",
            "zh": "舌尖抬起靠近上颚，声带振动（measure/vision）",
        }
        return tips.get(phoneme.lower(), f"注意 '{phoneme}' 的发音")

    async def synthesize_speech(
        self,
        text: str,
        voice: str = "en-US-AriaNeural",
        rate: str = "+0%",
    ) -> Optional[bytes]:
        """
        Azure TTS 合成（高质量备用方案）

        Args:
            text: 要合成的文本
            voice: 声音名称
            rate: 语速

        Returns:
            MP3 音频数据
        """
        config = self._get_speech_config()
        if not config:
            return None

        try:
            config.speech_synthesis_voice_name = voice

            # 使用 SSML 控制语速
            ssml = f"""
            <speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="en-US">
                <voice name="{voice}">
                    <prosody rate="{rate}">
                        {text}
                    </prosody>
                </voice>
            </speak>
            """

            synthesizer = speechsdk.SpeechSynthesizer(
                speech_config=config,
                audio_config=None
            )

            result = synthesizer.speak_ssml_async(ssml).get()

            if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
                return result.audio_data
            else:
                logger.error(f"TTS 合成失败: {result.reason}")
                return None

        except Exception as e:
            logger.error(f"TTS 异常: {e}")
            return None


# 全局实例
_azure_speech: Optional[AzureSpeechService] = None


def get_azure_speech() -> AzureSpeechService:
    """获取 Azure 语音服务单例"""
    global _azure_speech
    if _azure_speech is None:
        _azure_speech = AzureSpeechService()
    return _azure_speech
