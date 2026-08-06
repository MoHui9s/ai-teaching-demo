"""TTS Cache Service — SQLite 实现（替代 LevelDB/plyvel）"""

import hashlib
import logging
import sqlite3
from typing import Optional, Dict, Any
from pathlib import Path
from datetime import datetime
from threading import Lock

logger = logging.getLogger("tts-cache")


class TTSCacheServiceLevelDB:
    """
    TTS 缓存服务，使用 SQLite 作为 KV 存储（替代 LevelDB/plyvel）。

    API 兼容原 LevelDB 接口。
    """

    META_PREFIX = b"__meta__:"

    def __init__(self, db_path: str = "./data/tts_cache.leveldb"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # 使用 SQLite 文件替代 LevelDB（文件名保持不变以兼容）
        sqlite_path = str(self.db_path).replace(".leveldb", ".sqlite")
        if sqlite_path == str(self.db_path):
            sqlite_path = str(self.db_path) + ".sqlite"
        self.sqlite_path = sqlite_path
        self._lock = Lock()

        self.conn = sqlite3.connect(self.sqlite_path, check_same_thread=False)
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS cache (
                key BLOB PRIMARY KEY,
                value BLOB NOT NULL
            )
        """)
        self.conn.commit()

        # 为兼容 api/tts.py 中的 db.get() 直接调用，保存对文件的引用
        self._sqlite_path_ref = sqlite_path

        logger.info(f"TTS 缓存初始化完成 (SQLite): {self.sqlite_path}")

    # --- 兼容原 LevelDB 的 db.get() 接口 ---
    class _DBCompat:
        """模拟 plyvel.DB 的 get 方法"""
        def __init__(self, conn, lock):
            self._conn = conn
            self._lock = lock

        def get(self, key: bytes):
            with self._lock:
                cur = self._conn.execute("SELECT value FROM cache WHERE key = ?", (key,))
                row = cur.fetchone()
                return row[0] if row else None

        def put(self, key: bytes, value: bytes):
            with self._lock:
                self._conn.execute(
                    "INSERT OR REPLACE INTO cache (key, value) VALUES (?, ?)",
                    (key, value)
                )
                self._conn.commit()

        def delete(self, key: bytes):
            with self._lock:
                self._conn.execute("DELETE FROM cache WHERE key = ?", (key,))
                self._conn.commit()

        def iterator(self, include_value=True):
            with self._lock:
                cur = self._conn.execute("SELECT key, value FROM cache")
                for row in cur:
                    if include_value:
                        yield (row[0], row[1])
                    else:
                        yield (row[0],)

        def close(self):
            pass

    @property
    def db(self):
        """兼容 api/tts.py 中 cache_service.db.get(key_bytes) 调用"""
        if not hasattr(self, '_db_compat'):
            self._db_compat = self._DBCompat(self.conn, self._lock)
        return self._db_compat

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
        """获取缓存"""
        cache_key = self._generate_key(text, voice)

        audio_data = self.db.get(cache_key)
        if audio_data is None:
            return None

        meta_key = self.META_PREFIX + cache_key
        meta_bytes = self.db.get(meta_key)
        if meta_bytes is None:
            return {
                'data': audio_data,
                'duration': None,
                'voice': voice
            }

        meta = self._decode_meta(meta_bytes)
        return {
            'data': audio_data,
            'duration': meta.get('duration'),
            'voice': meta.get('voice', voice)
        }

    def set(self, text: str, voice: str, audio_data: bytes, duration: float) -> None:
        """设置缓存"""
        cache_key = self._generate_key(text, voice)
        meta_key = self.META_PREFIX + cache_key

        self.db.put(cache_key, audio_data)
        self.db.put(meta_key, self._encode_meta(text, voice, duration))
        logger.debug(f"缓存已保存: {cache_key.decode()} ({len(audio_data)} bytes)")

    def delete(self, text: str, voice: str) -> bool:
        """删除缓存"""
        cache_key = self._generate_key(text, voice)
        meta_key = self.META_PREFIX + cache_key

        if self.db.get(cache_key) is None:
            return False

        self.db.delete(cache_key)
        self.db.delete(meta_key)
        return True

    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计"""
        total_entries = 0
        total_size = 0

        for key, value in self.db.iterator():
            if not key.startswith(self.META_PREFIX):
                total_entries += 1
                total_size += len(value)

        return {
            'total_entries': total_entries,
            'total_size_bytes': total_size,
            'total_size_mb': round(total_size / (1024 * 1024), 2),
        }

    def clear_all(self) -> int:
        """清空所有缓存"""
        with self._lock:
            cur = self.conn.execute("SELECT COUNT(*) FROM cache WHERE key NOT LIKE ?", (b'__meta__:%',))
            count = cur.fetchone()[0]
            self.conn.execute("DELETE FROM cache")
            self.conn.commit()
        logger.info(f"已清空所有缓存，共 {count} 条")
        return count

    def close(self):
        """关闭数据库连接"""
        if hasattr(self, 'conn') and self.conn:
            self.conn.close()
            logger.info("TTS 缓存数据库已关闭")

    def __del__(self):
        self.close()


# 全局缓存实例
_cache_instance: Optional[TTSCacheServiceLevelDB] = None


def get_cache_service() -> TTSCacheServiceLevelDB:
    """获取全局缓存服务实例"""
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = TTSCacheServiceLevelDB()
    return _cache_instance
