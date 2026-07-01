#!/usr/bin/env python3
"""User Database Migration Script: JSON → SQLite"""

import sys
import logging
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


def migrate_users():
    """迁移用户数据从 JSON 到 SQLite"""
    # 导入旧版本
    from database.user_db import UserDatabase as OldUserDB
    # 导入新版本
    from database.user_db_sqlite import UserDatabaseSQLite as NewUserDB

    old_db_path = Path("./data/users.json")
    new_db_path = Path("./data/users.db")

    logger.info("开始迁移用户数据...")

    # 初始化服务
    try:
        old_db = OldUserDB(str(old_db_path))
    except Exception as e:
        logger.info(f"旧 JSON 数据库不存在或为空: {e}")
        logger.info("跳过迁移，直接使用新的 SQLite 数据库")
        return

    new_db = NewUserDB(str(new_db_path))

    # 从 JSON 读取数据
    old_users = old_db.list_users()

    logger.info(f"找到 {len(old_users)} 个用户")

    migrated = 0
    skipped = 0

    for user_data in old_users:
        try:
            user_id = user_data['user_id']
            email = user_data['email']

            # 检查是否已存在
            if new_db.get_user_by_email(email):
                logger.info(f"用户已存在，跳过: {email}")
                skipped += 1
                continue

            # 获取完整用户数据（包括密码哈希）
            full_user = old_db.get_user_by_id(user_id)
            if not full_user:
                logger.warning(f"无法获取用户详情: {user_id}")
                continue

            # 创建新用户
            new_db.create_user(
                user_id=full_user['user_id'],
                email=full_user['email'],
                password_hash=full_user['password_hash']
            )
            migrated += 1
            logger.info(f"迁移用户: {email}")

        except Exception as e:
            logger.error(f"迁移失败: {e}")

    logger.info(f"迁移完成: {migrated} 成功, {skipped} 跳过")

    # 显示新旧统计对比
    new_users = new_db.list_users()
    logger.info(f"SQLite 用户总数: {len(new_users)}")

    # 询问是否备份旧文件
    print("\n是否备份旧的 JSON 文件？")
    backup_path = old_db_path.with_suffix('.json.backup')
    if input(f"重命名为 {backup_path} ？输入 yes 确认: ").strip().lower() == 'yes':
        old_db_path.rename(backup_path)
        logger.info(f"旧 JSON 文件已备份到: {backup_path}")


if __name__ == "__main__":
    migrate_users()
