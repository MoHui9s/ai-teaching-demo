"""TTS Cache Service using SQLite3 as KV storage."""

import sqlite3
import hashlib
import json
import logging
from typing import Optional, Dict, Any
from pathlib import Path
from datetime import datetime

logger = logging.getLogger("tts-cache")


class TTSCacheService:
    """
    TTS缓存服务，使用SQLite3作为KV存储。

    特性：
    - 使用MD5(text|voice)作为缓存键
    - 存储音频数据（base64编码）和元数据
    - 不设置过期时间，永久缓存
    """

    def __init__(self, db_path: str = "./data/tts_cache.db"):
        """初始化缓存服务"""
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
        logger.info(f"TTS缓存初始化完成: {self.db_path}")

    def _init_db(self):
        """初始化数据库表"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # 创建缓存表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tts_cache (
                cache_key TEXT PRIMARY KEY,
                text TEXT NOT NULL,
                voice TEXT NOT NULL,
                audio_data BLOB NOT NULL,
                duration REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                accessed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 创建访问时间索引
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_accessed_at
            ON tts_cache(accessed_at)
        """)

        conn.commit()
        conn.close()

    def _generate_key(self, text: str, voice: str) -> str:
        """生成缓存键：MD5(text|voice)"""
        content = f"{text}|{voice}"
        return hashlib.md5(content.encode('utf-8')).hexdigest()

    def get(self, text: str, voice: str) -> Optional[Dict[str, Any]]:
        """
        获取缓存

        Args:
            text: 文本内容
            voice: 声音类型

        Returns:
            包含audio_data, duration的字典，如果未找到返回None
        """
        cache_key = self._generate_key(text, voice)

        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT audio_data, duration, voice
            FROM tts_cache
            WHERE cache_key = ?
        """, (cache_key,))

        row = cursor.fetchone()

        if row:
            # 更新访问时间
            cursor.execute("""
                UPDATE tts_cache
                SET accessed_at = CURRENT_TIMESTAMP
                WHERE cache_key = ?
            """, (cache_key,))
            conn.commit()
            conn.close()

            return {
                'data': bytes(row['audio_data']),
                'duration': row['duration'],
                'voice': row['voice']
            }

        conn.close()
        return None

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

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT OR REPLACE INTO tts_cache
            (cache_key, text, voice, audio_data, duration)
            VALUES (?, ?, ?, ?, ?)
        """, (cache_key, text, voice, audio_data, duration))

        conn.commit()
        conn.close()
        logger.debug(f"缓存已保存: {cache_key} ({len(audio_data)} bytes)")

    def delete(self, text: str, voice: str) -> bool:
        """
        删除缓存

        Returns:
            是否删除成功
        """
        cache_key = self._generate_key(text, voice)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("DELETE FROM tts_cache WHERE cache_key = ?", (cache_key,))
        deleted = cursor.rowcount > 0

        conn.commit()
        conn.close()

        return deleted

    def get_stats(self) -> Dict[str, Any]:
        """
        获取缓存统计信息

        Returns:
            包含total_entries, total_size_mb等的字典
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # 获取条目数
        cursor.execute("SELECT COUNT(*) FROM tts_cache")
        total_entries = cursor.fetchone()[0]

        # 获取总大小（音频数据）
        cursor.execute("SELECT SUM(LENGTH(audio_data)) FROM tts_cache")
        total_size = cursor.fetchone()[0] or 0

        # 获取最新缓存
        cursor.execute("""
            SELECT created_at FROM tts_cache
            ORDER BY created_at DESC LIMIT 1
        """)
        latest = cursor.fetchone()

        conn.close()

        return {
            'total_entries': total_entries,
            'total_size_bytes': total_size,
            'total_size_mb': round(total_size / (1024 * 1024), 2),
            'latest_cache': latest[0] if latest else None
        }

    def clear_all(self) -> int:
        """
        清空所有缓存

        Returns:
            清除的条目数
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM tts_cache")
        count = cursor.fetchone()[0]

        cursor.execute("DELETE FROM tts_cache")
        conn.commit()
        conn.close()

        logger.info(f"已清空所有缓存，共 {count} 条")
        return count


# 全局缓存实例
_cache_instance: Optional[TTSCacheService] = None


def get_cache_service() -> TTSCacheService:
    """获取全局缓存服务实例"""
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = TTSCacheService()
    return _cache_instance
