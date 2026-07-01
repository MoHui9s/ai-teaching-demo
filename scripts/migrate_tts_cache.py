#!/usr/bin/env python3
"""TTS Cache Migration Script: SQLite → LevelDB"""

import sys
import logging
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


def migrate_tts_cache():
    """迁移 TTS 缓存从 SQLite 到 LevelDB"""
    # 导入旧版本
    from services.cache_service import TTSCacheService as OldCacheService
    # 导入新版本
    from services.cache_service_leveldb import TTSCacheServiceLevelDB as NewCacheService

    old_db_path = Path("./data/tts_cache.db")
    new_db_path = Path("./data/tts_cache.leveldb")

    if not old_db_path.exists():
        logger.info(f"旧缓存不存在: {old_db_path}")
        return

    logger.info("开始迁移 TTS 缓存...")

    # 初始化服务
    old_cache = OldCacheService(str(old_db_path))
    new_cache = NewCacheService(str(new_db_path))

    # 从 SQLite 读取数据
    import sqlite3
    conn = sqlite3.connect(str(old_db_path))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("SELECT text, voice, audio_data, duration FROM tts_cache")
    rows = cursor.fetchall()

    logger.info(f"找到 {len(rows)} 条缓存记录")

    migrated = 0
    failed = 0

    for row in rows:
        try:
            text = row['text']
            voice = row['voice']
            audio_data = row['audio_data']
            duration = row['duration']

            new_cache.set(text, voice, audio_data, duration)
            migrated += 1

            if migrated % 10 == 0:
                logger.info(f"已迁移 {migrated}/{len(rows)} 条...")

        except Exception as e:
            logger.error(f"迁移失败: {e}")
            failed += 1

    conn.close()
    new_cache.close()

    logger.info(f"迁移完成: {migrated} 成功, {failed} 失败")

    # 显示新旧统计对比
    old_stats = old_cache.get_stats()
    new_stats = new_cache.get_stats()

    logger.info(f"SQLite: {old_stats['total_entries']} 条, {old_stats['total_size_mb']} MB")
    logger.info(f"LevelDB: {new_stats['total_entries']} 条, {new_stats['total_size_mb']} MB")

    # 询问是否备份旧文件
    print("\n是否备份旧的 SQLite 数据库？")
    backup_path = old_db_path.with_suffix('.db.backup')
    if input(f"重命名为 {backup_path} ？输入 yes 确认: ").strip().lower() == 'yes':
        old_db_path.rename(backup_path)
        logger.info(f"旧数据库已备份到: {backup_path}")


if __name__ == "__main__":
    migrate_tts_cache()
