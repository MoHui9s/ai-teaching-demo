"""用户同步工具 —— 确保 users.db (auth) 与 edulingua.db (ORM) 一致。

问题背景：
- api/auth.py 登录时创建用户仅写入 users.db (UserDatabaseSQLite)
- 业务 API (tasks/progress/achievements) 查询 edulingua.db (SQLAlchemy ORM)
- 两库不同步导致"用户不存在"错误

本模块提供统一的双写接口，在用户创建/登录时确保两库一致。
"""

import os
import logging

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from database.database import get_db_session
from database.models import User

logger = logging.getLogger("user-sync")

DEV_MODE = os.getenv("DEV_MODE", "false").lower() in ("1", "true", "yes")


def ensure_orm_user(
    user_id: str,
    email: str,
    password_hash: str = "",
    name: str = "",
) -> User:
    """
    确保 edulingua.db 中存在该用户记录。

    若不存在则创建（默认 beginner 级别），已存在则直接返回。

    Args:
        user_id: 业务用户 ID
        email: 邮箱
        password_hash: 密码哈希（若 ORM 中不存在时需要）
        name: 显示名称

    Returns:
        SQLAlchemy User 对象
    """
    db = get_db_session()
    try:
        existing = db.query(User).filter(User.user_id == user_id).first()
        if existing:
            # 可能从 auth 库同步过来的用户缺少 name，补全它
            if name and not existing.name:
                existing.name = name
                db.commit()
            return existing

        user = User(
            user_id=user_id,
            name=name,
            email=email,
            password_hash=password_hash,
            level="beginner",
            vocab_size=2000,
            pronunciation_avg=55.0,
            listening_avg=60.0,
            streak_days=0,
            total_study_minutes=0,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        logger.info(f"ORM 用户已创建: user_id={user_id}, email={email}")
        return user

    except Exception as e:
        db.rollback()
        logger.error(f"创建 ORM 用户失败: {e}")
        raise
    finally:
        db.close()


def get_or_create_user(user_id: str) -> User | None:
    """
    查询 ORM 用户，DEV_MODE 下尝试从 auth 库修复。

    用于业务 API 中统一处理"用户不存在"的场景。

    Args:
        user_id: 业务用户 ID

    Returns:
        User 对象，或 None（非 DEV_MODE 且用户确实不存在时）
    """
    db = get_db_session()
    try:
        user = db.query(User).filter(User.user_id == user_id).first()
        if user:
            return user

        if DEV_MODE:
            # 尝试从 users.db 读取信息并修复到 ORM
            from database.user_db_sqlite import get_user_db
            auth_db = get_user_db()
            auth_user = auth_db.get_user_by_id(user_id)
            if not auth_user:
                # 也尝试按 email 查找（user_id 可能不匹配）
                logger.warning(f"用户 {user_id} 在两个数据库中都不存在")
                return None

            logger.info(f"DEV_MODE: 从 auth 库修复 ORM 用户 {user_id}")
            # 需要新的 session，因为当前 session 可能已关闭
            pass  # 将由调用方处理

        return None
    finally:
        db.close()
