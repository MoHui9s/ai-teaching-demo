"""TTS Cache Service using LevelDB as KV storage."""

import hashlib
import logging
from typing import Optional, Dict, Any
from pathlib import Path
from datetime import datetime

logger = logging.getLogger("tts-cache")

try:
    import plyvel
except ImportError:
    plyvel = None
    logger.warning("plyvel not installed. LevelDB cache service unavailable.")


class TTSCacheServiceLevelDB:
    """
    TTS缓存服务，使用LevelDB作为KV存储。

    特性：
    - 使用MD5(text|voice)作为缓存键
    - 存储音频数据（原始二进制）和元数据
    - 不设置过期时间，永久缓存
    - 支持压缩（LevelDB内置Snappy）
    """

    # 元数据键前缀
    META_PREFIX = b"__meta__:"
    STATS_KEY = b"__stats__"

    def __init__(self, db_path: str = "./data/tts_cache.leveldb"):
        """初始化缓存服务"""
        if plyvel is None:
            raise RuntimeError("plyvel is required. Install: pip install plyvel")

        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # 打开或创建 LevelDB
        self.db = plyvel.DB(str(self.db_path), create_if_missing=True, error_if_exists=False)

        logger.info(f"TTS缓存初始化完成: {self.db_path}")

    def _generate_key(self, text: str, voice: str) -> bytes:
        """生成缓存键：MD5(text|voice)"""
        content = f"{text}|{voice}"
        return hashlib.md5(content.encode('utf-8')).hexdigest().encode('utf-8')

    def _encode_meta(self, text: str, voice: str, duration: float) -> bytes:
        """编码元数据"""
        import json
        return json.dumps({
            "text": text,
            "voice": voice,
            "duration": duration,
            "created_at": datetime.utcnow().isoformat()
        }).encode('utf-8')

    def _decode_meta(self, meta_bytes: bytes) -> Dict[str, Any]:
        """解码元数据"""
        import json
        return json.loads(meta_bytes.decode('utf-8'))

    def get(self, text: str, voice: str) -> Optional[Dict[str, Any]]:
        """
        获取缓存

        Args:
            text: 文本内容
            voice: 声音类型

        Returns:
            包含data, duration, voice的字典，如果未找到返回None
        """
        cache_key = self._generate_key(text, voice)

        # 获取音频数据
        audio_data = self.db.get(cache_key)
        if audio_data is None:
            return None

        # 获取元数据
        meta_key = self.META_PREFIX + cache_key
        meta_bytes = self.db.get(meta_key)
        if meta_bytes is None:
            # 兼容旧数据：没有元数据的情况
            return {
                'data': audio_data,
                'duration': None,
                'voice': voice
            }

        meta = self._decode_meta(meta_bytes)

        # 更新访问时间（元数据中添加访问时间）
        meta['accessed_at'] = datetime.utcnow().isoformat()
        self.db.put(meta_key, self._encode_meta(
            meta.get('text', text),
            meta.get('voice', voice),
            meta.get('duration', 0)
        ))

        return {
            'data': audio_data,
            'duration': meta.get('duration'),
            'voice': meta.get('voice', voice)
        }

    def set(self, text: str, voice: str, audio_data: bytes, duration: float) -> None:
        """
        设置缓存

        Args:
            text: 文本内容
            voice: 声音类型
            audio_data: 音频二进制数据
            duration: 音频时长(秒)
        """
        cache_key = self._generate_key(text, voice)
        meta_key = self.META_PREFIX + cache_key

        # 存储音频数据
        self.db.put(cache_key, audio_data)

        # 存储元数据
        self.db.put(meta_key, self._encode_meta(text, voice, duration))

        logger.debug(f"缓存已保存: {cache_key.decode()} ({len(audio_data)} bytes)")

    def delete(self, text: str, voice: str) -> bool:
        """
        删除缓存

        Returns:
            是否删除成功
        """
        cache_key = self._generate_key(text, voice)
        meta_key = self.META_PREFIX + cache_key

        # 检查是否存在
        if self.db.get(cache_key) is None:
            return False

        # 删除数据和元数据
        self.db.delete(cache_key)
        self.db.delete(meta_key)

        return True

    def get_stats(self) -> Dict[str, Any]:
        """
        获取缓存统计信息

        Returns:
            包含total_entries, total_size_mb等的字典
        """
        total_entries = 0
        total_size = 0
        latest_created = None

        # 遍历数据库（只统计音频键，跳过元数据）
        for key, value in self.db.iterator():
            if not key.startswith(self.META_PREFIX):
                total_entries += 1
                total_size += len(value)

                # 获取创建时间
                meta_key = self.META_PREFIX + key
                meta_bytes = self.db.get(meta_key)
                if meta_bytes:
                    meta = self._decode_meta(meta_bytes)
                    created = meta.get('created_at')
                    if created:
                        if latest_created is None or created > latest_created:
                            latest_created = created

        return {
            'total_entries': total_entries,
            'total_size_bytes': total_size,
            'total_size_mb': round(total_size / (1024 * 1024), 2),
            'latest_cache': latest_created
        }

    def clear_all(self) -> int:
        """
        清空所有缓存

        Returns:
            清除的条目数
        """
        count = 0
        keys_to_delete = []

        # 收集所有键
        for key in self.db.iterator(include_value=False):
            keys_to_delete.append(key)
            count += 1

        # 批量删除
        for key in keys_to_delete:
            self.db.delete(key)

        logger.info(f"已清空所有缓存，共 {count // 2} 条（元数据+数据）")
        return count // 2

    def close(self):
        """关闭数据库连接"""
        if hasattr(self, 'db'):
            self.db.close()
            logger.info("TTS缓存数据库已关闭")

    def __del__(self):
        """析构函数，确保数据库关闭"""
        self.close()


# 全局缓存实例
_cache_instance: Optional[TTSCacheServiceLevelDB] = None


def get_cache_service() -> TTSCacheServiceLevelDB:
    """获取全局缓存服务实例"""
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = TTSCacheServiceLevelDB()
    return _cache_instance
