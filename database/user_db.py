"""User database module for Hermes Agent."""

import json
import os
import uuid
from pathlib import Path
from typing import Dict, Optional, List
from threading import Lock


class UserDatabase:
    """
    Simple JSON file-based user database.

    Stores user accounts with email, password_hash, and user_id mapping.
    """

    def __init__(self, db_path: str = None):
        if db_path is None:
            db_path = Path(os.getcwd()) / "data" / "users.json"
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = Lock()
        self._data = self._load()

    def _load(self) -> Dict:
        """Load database from file."""
        if not self.db_path.exists():
            return {"users": {}, "email_to_user": {}}

        try:
            with open(self.db_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return {"users": {}, "email_to_user": {}}

    def _save(self) -> None:
        """Save database to file."""
        import tempfile
        try:
            fd, tmp_path = tempfile.mkstemp(
                dir=str(self.db_path.parent), suffix=".tmp", prefix=".users_"
            )
            try:
                with os.fdopen(fd, "w", encoding='utf-8') as f:
                    json.dump(self._data, f, ensure_ascii=False, indent=2)
                os.replace(tmp_path, self.db_path)
            except BaseException:
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass
                raise
        except (OSError, IOError) as e:
            raise RuntimeError(f"Failed to write database {self.db_path}: {e}")

    def create_user(self, user_id: str, email: str, password_hash: str) -> Dict:
        """
        Create a new user.

        Args:
            user_id: User identifier
            email: User email
            password_hash: Hashed password

        Returns:
            Created user data
        """
        with self._lock:
            # Check if email already exists
            if email in self._data["email_to_user"]:
                raise ValueError(f"Email already registered: {email}")

            # Check if user_id already exists
            if user_id in self._data["users"]:
                raise ValueError(f"User ID already exists: {user_id}")

            # Create user
            user_data = {
                "user_id": user_id,
                "email": email,
                "password_hash": password_hash,
                "created_at": None  # Will be set by _save
            }

            self._data["users"][user_id] = user_data
            self._data["email_to_user"][email] = user_id

            self._save()

            return user_data

    def get_user_by_email(self, email: str) -> Optional[Dict]:
        """
        Get user by email.

        Args:
            email: User email

        Returns:
            User data or None
        """
        user_id = self._data["email_to_user"].get(email)
        if not user_id:
            return None
        return self._data["users"].get(user_id)

    def get_user_by_id(self, user_id: str) -> Optional[Dict]:
        """
        Get user by ID.

        Args:
            user_id: User identifier

        Returns:
            User data or None
        """
        return self._data["users"].get(user_id)

    def list_users(self) -> List[Dict]:
        """
        List all users.

        Returns:
            List of user data (without password_hash)
        """
        with self._lock:
            users = []
            for user_data in self._data["users"].values():
                users.append({
                    "user_id": user_data["user_id"],
                    "email": user_data["email"],
                    "created_at": user_data.get("created_at")
                })
            return users

    def update_password(self, user_id: str, new_password_hash: str) -> bool:
        """
        Update user password.

        Args:
            user_id: User identifier
            new_password_hash: New hashed password

        Returns:
            True if updated, False if user not found
        """
        with self._lock:
            user = self._data["users"].get(user_id)
            if not user:
                return False

            user["password_hash"] = new_password_hash
            self._save()
            return True

    def delete_user(self, user_id: str) -> bool:
        """
        Delete a user.

        Args:
            user_id: User identifier

        Returns:
            True if deleted, False if user not found
        """
        with self._lock:
            user = self._data["users"].get(user_id)
            if not user:
                return False

            email = user["email"]
            del self._data["users"][user_id]
            del self._data["email_to_user"][email]

            self._save()
            return True


# Global instance
_user_db: Optional[UserDatabase] = None
_user_db_lock = Lock()


def get_user_db() -> UserDatabase:
    """Get or create global user database instance."""
    global _user_db

    with _user_db_lock:
        if _user_db is None:
            _user_db = UserDatabase()
        return _user_db
