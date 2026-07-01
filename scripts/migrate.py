#!/usr/bin/env python3
"""Database Migration Entry Point

Usage:
    python scripts/migrate.py [--all] [--tts] [--users]

Options:
    --all      Migrate both TTS cache and users
    --tts      Migrate TTS cache only
    --users    Migrate users only
"""

import sys
import argparse
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))


def migrate_tts():
    """迁移 TTS 缓存"""
    print("=" * 50)
    print("迁移 TTS 缓存: SQLite → LevelDB")
    print("=" * 50)
    from scripts.migrate_tts_cache import migrate_tts_cache
    migrate_tts_cache()


def migrate_users():
    """迁移用户数据"""
    print("=" * 50)
    print("迁移用户数据: JSON → SQLite")
    print("=" * 50)
    from scripts.migrate_users import migrate_users
    migrate_users()


def main():
    parser = argparse.ArgumentParser(description="数据库迁移脚本")
    parser.add_argument('--all', action='store_true', help='迁移所有数据')
    parser.add_argument('--tts', action='store_true', help='仅迁移 TTS 缓存')
    parser.add_argument('--users', action='store_true', help='仅迁移用户数据')

    args = parser.parse_args()

    if args.all or (not args.tts and not args.users):
        # 默认迁移所有
        migrate_users()
        print()
        migrate_tts()
    elif args.tts:
        migrate_tts()
    elif args.users:
        migrate_users()


if __name__ == "__main__":
    main()
