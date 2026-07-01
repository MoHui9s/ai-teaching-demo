"""SQLite-based User Database Module for Hermes Agent."""

import sqlite3
import os
import uuid
import bcrypt
from pathlib import Path
from typing import Dict, Optional, List
from threading import Lock
from datetime import datetime


class UserDatabaseSQLite:
    """
    SQLite-based user database.

    Stores user accounts with email, password_hash, and user_id mapping.
    Supports transactions and concurrent access.
    """

    def __init__(self, db_path: str = None):
        if db_path is None:
            db_path = Path(os.getcwd()) / "data" / "users.db"
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = Lock()
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        """获取数据库连接"""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA journal_mode = WAL")
        return conn

    def _init_db(self):
        """初始化数据库表"""
        conn = self._get_connection()
        cursor = conn.cursor()

        # 用户表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id TEXT PRIMARY KEY,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT 1
            )
        """)

        # 用户会话表（可选，用于管理 JWT/会话）
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                token_hash TEXT NOT NULL,
                expires_at TIMESTAMP NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
            )
        """)

        # 用户配置/偏好表（可选）
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_preferences (
                user_id TEXT PRIMARY KEY,
                theme TEXT DEFAULT 'auto',
                language TEXT DEFAULT 'en',
                FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
            )
        """)

        # 索引
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_users_email
            ON users(email)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_sessions_user
            ON user_sessions(user_id)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_sessions_expires
            ON user_sessions(expires_at)
        """)

        conn.commit()
        conn.close()

    def create_user(self, user_id: str, email: str, password_hash: str) -> Dict:
        """
        创建新用户

        Args:
            user_id: 用户标识符
            email: 用户邮箱
            password_hash: 密码哈希

        Returns:
            创建的用户数据

        Raises:
            ValueError: 邮箱或用户ID已存在
        """
        with self._lock:
            conn = self._get_connection()
            cursor = conn.cursor()

            try:
                cursor.execute("""
                    INSERT INTO users (user_id, email, password_hash)
                    VALUES (?, ?, ?)
                """, (user_id, email, password_hash))

                conn.commit()
            except sqlite3.IntegrityError as e:
                conn.close()
                if "email" in str(e):
                    raise ValueError(f"Email already registered: {email}")
                raise ValueError(f"User ID already exists: {user_id}")

            # 获取创建的用户
            user = self.get_user_by_id(user_id)
            conn.close()
            return user

    def get_user_by_email(self, email: str) -> Optional[Dict]:
        """
        按邮箱获取用户

        Args:
            email: 用户邮箱

        Returns:
            用户数据或None
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT user_id, email, password_hash, created_at, updated_at, is_active
            FROM users
            WHERE email = ?
        """, (email,))

        row = cursor.fetchone()
        conn.close()

        if row:
            return dict(row)
        return None

    def get_user_by_id(self, user_id: str) -> Optional[Dict]:
        """
        按用户ID获取用户

        Args:
            user_id: 用户标识符

        Returns:
            用户数据或None
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT user_id, email, password_hash, created_at, updated_at, is_active
            FROM users
            WHERE user_id = ?
        """, (user_id,))

        row = cursor.fetchone()
        conn.close()

        if row:
            return dict(row)
        return None

    def list_users(self) -> List[Dict]:
        """
        列出所有用户

        Returns:
            用户数据列表（不包含密码哈希）
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT user_id, email, created_at, updated_at, is_active
            FROM users
            ORDER BY created_at DESC
        """)

        users = [dict(row) for row in cursor.fetchall()]
        conn.close()

        return users

    def update_password(self, user_id: str, new_password_hash: str) -> bool:
        """
        更新用户密码

        Args:
            user_id: 用户标识符
            new_password_hash: 新密码哈希

        Returns:
            是否更新成功
        """
        with self._lock:
            conn = self._get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                UPDATE users
                SET password_hash = ?, updated_at = CURRENT_TIMESTAMP
                WHERE user_id = ?
            """, (new_password_hash, user_id))

            updated = cursor.rowcount > 0
            conn.commit()
            conn.close()

            return updated

    def delete_user(self, user_id: str) -> bool:
        """
        删除用户

        Args:
            user_id: 用户标识符

        Returns:
            是否删除成功
        """
        with self._lock:
            conn = self._get_connection()
            cursor = conn.cursor()

            cursor.execute("DELETE FROM users WHERE user_id = ?", (user_id,))

            deleted = cursor.rowcount > 0
            conn.commit()
            conn.close()

            return deleted

    def set_preference(self, user_id: str, key: str, value: str) -> bool:
        """
        设置用户偏好

        Args:
            user_id: 用户标识符
            key: 偏好键（theme, language等）
            value: 偏好值

        Returns:
            是否设置成功
        """
        with self._lock:
            conn = self._get_connection()
            cursor = conn.cursor()

            # 检查用户是否存在
            if not self.get_user_by_id(user_id):
                conn.close()
                return False

            # 使用 UPSERT
            cursor.execute("""
                INSERT INTO user_preferences (user_id, theme, language)
                VALUES (?, NULL, NULL)
                ON CONFLICT(user_id) DO UPDATE SET theme = NULL, language = NULL
            """, (user_id,))

            # 更新特定字段
            if key == "theme":
                cursor.execute("""
                    UPDATE user_preferences SET theme = ? WHERE user_id = ?
                """, (value, user_id))
            elif key == "language":
                cursor.execute("""
                    UPDATE user_preferences SET language = ? WHERE user_id = ?
                """, (value, user_id))
            else:
                conn.close()
                return False

            conn.commit()
            conn.close()
            return True

    def get_preference(self, user_id: str, key: str) -> Optional[str]:
        """
        获取用户偏好

        Args:
            user_id: 用户标识符
            key: 偏好键

        Returns:
            偏好值或None
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT theme, language FROM user_preferences WHERE user_id = ?
        """, (user_id,))

        row = cursor.fetchone()
        conn.close()

        if row:
            return row[key] if key in row.keys() else None
        return None

    def get_stats(self) -> Dict:
        """
        获取数据库统计信息

        Returns:
            统计数据
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        # 用户总数
        cursor.execute("SELECT COUNT(*) FROM users")
        total_users = cursor.fetchone()[0]

        # 活跃用户数
        cursor.execute("SELECT COUNT(*) FROM users WHERE is_active = 1")
        active_users = cursor.fetchone()[0]

        # 最新用户
        cursor.execute("""
            SELECT email, created_at FROM users
            ORDER BY created_at DESC LIMIT 1
        """)
        latest = cursor.fetchone()

        conn.close()

        return {
            'total_users': total_users,
            'active_users': active_users,
            'latest_user': dict(latest) if latest else None
        }

    def close(self):
        """关闭数据库连接（LevelDB兼容接口）"""
        pass


# 全局实例
_user_db: Optional[UserDatabaseSQLite] = None
_user_db_lock = Lock()


def get_user_db() -> UserDatabaseSQLite:
    """获取或创建全局用户数据库实例"""
    global _user_db

    with _user_db_lock:
        if _user_db is None:
            _user_db = UserDatabaseSQLite()
        return _user_db
