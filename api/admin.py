"""Admin endpoints for Hermes Agent API."""

import os
import bcrypt
import uuid
from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel
from typing import Optional, List

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from database.user_db_sqlite import get_user_db
from logging_config import log_user_action
import logging

logger = logging.getLogger("hermes-admin")

router = APIRouter(prefix="/api/admin", tags=["Admin"])

ADMIN_TOKEN = os.getenv("ADMIN_TOKEN")


def verify_admin_token(x_admin_token: str) -> bool:
    """验证管理员令牌"""
    if not ADMIN_TOKEN:
        raise HTTPException(status_code=401, detail="Admin interface not enabled")
    if x_admin_token != ADMIN_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid admin token")
    return True


# ============================================================================
# 管理员验证端点
# ============================================================================

@router.get("/status")
async def get_admin_status():
    """Check if admin interface is enabled."""
    return {
        "enabled": bool(ADMIN_TOKEN),
        "configured": bool(ADMIN_TOKEN and ADMIN_TOKEN.strip())
    }


@router.get("/verify")
async def verify_admin(x_admin_token: str = Header(None, alias="X-Admin-Token")):
    """Verify admin token."""
    verify_admin_token(x_admin_token)
    return {"success": True, "message": "Admin token verified"}


# ============================================================================
# 用户管理模型
# ============================================================================

class CreateUserRequest(BaseModel):
    """创建用户请求"""
    user_id: Optional[str] = None  # 可选，不提供则自动生成
    email: str
    password: str


class UpdateUserRequest(BaseModel):
    """更新用户请求"""
    email: Optional[str] = None
    is_active: Optional[bool] = None


class ResetPasswordRequest(BaseModel):
    """重置密码请求"""
    new_password: Optional[str] = None  # 可选，不提供则自动生成


class UserResponse(BaseModel):
    """用户响应"""
    user_id: str
    email: str
    created_at: str
    updated_at: str
    is_active: bool


class UserListResponse(BaseModel):
    """用户列表响应"""
    users: List[UserResponse]
    total: int


# ============================================================================
# 用户管理端点
# ============================================================================

@router.post("/users", response_model=dict)
async def create_user(
    request: CreateUserRequest,
    x_admin_token: str = Header(None, alias="X-Admin-Token")
):
    """
    创建新用户（管理员专用）

    Args:
        request: 创建请求（email, password, 可选 user_id）
        x_admin_token: 管理员令牌

    Returns:
        创建的用户信息（含生成的密码如果未提供 user_id）
    """
    verify_admin_token(x_admin_token)

    user_db = get_user_db()

    # 生成 user_id（如果未提供）
    user_id = request.user_id or f"user_{uuid.uuid4().hex[:12]}"

    # 哈希密码
    password_hash = bcrypt.hashpw(request.password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    try:
        user = user_db.create_user(user_id, request.email, password_hash)
        log_user_action(logger, user_id, "admin_create_user", email=request.email)
        logger.info(f"Admin created user: {user_id} ({request.email})")

        return {
            "success": True,
            "user": {
                "user_id": user["user_id"],
                "email": user["email"],
                "created_at": user.get("created_at"),
                "is_active": True
            },
            "message": f"User {request.email} created successfully"
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/users", response_model=dict)
async def list_users(
    x_admin_token: str = Header(None, alias="X-Admin-Token")
):
    """
    获取用户列表（管理员专用）

    Args:
        x_admin_token: 管理员令牌

    Returns:
        用户列表
    """
    verify_admin_token(x_admin_token)

    user_db = get_user_db()
    users = user_db.list_users()

    return {
        "users": users,
        "total": len(users)
    }


@router.get("/users/{user_id}", response_model=dict)
async def get_user(
    user_id: str,
    x_admin_token: str = Header(None, alias="X-Admin-Token")
):
    """
    获取用户详情（管理员专用）

    Args:
        user_id: 用户ID
        x_admin_token: 管理员令牌

    Returns:
        用户详情
    """
    verify_admin_token(x_admin_token)

    user_db = get_user_db()
    user = user_db.get_user_by_id(user_id)

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # 不返回密码哈希
    user.pop("password_hash", None)

    return {
        "user": user
    }


@router.put("/users/{user_id}", response_model=dict)
async def update_user(
    user_id: str,
    request: UpdateUserRequest,
    x_admin_token: str = Header(None, alias="X-Admin-Token")
):
    """
    更新用户（管理员专用）

    Args:
        user_id: 用户ID
        request: 更新请求（email, is_active）
        x_admin_token: 管理员令牌

    Returns:
        更新后的用户信息
    """
    verify_admin_token(x_admin_token)

    user_db = get_user_db()
    user = user_db.get_user_by_id(user_id)

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # 更新邮箱（如果提供）
    if request.email is not None and request.email != user["email"]:
        # 检查邮箱是否已被其他用户使用
        existing = user_db.get_user_by_email(request.email)
        if existing and existing["user_id"] != user_id:
            raise HTTPException(status_code=400, detail="Email already in use")

        # 需要直接修改数据库
        import sqlite3
        conn = sqlite3.connect(str(user_db.db_path))
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET email = ?, updated_at = CURRENT_TIMESTAMP WHERE user_id = ?",
                       (request.email, user_id))
        conn.commit()
        conn.close()
        log_user_action(logger, user_id, "admin_update_user", field="email", new_value=request.email)

    # 更新激活状态（如果提供）
    if request.is_active is not None:
        import sqlite3
        conn = sqlite3.connect(str(user_db.db_path))
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET is_active = ?, updated_at = CURRENT_TIMESTAMP WHERE user_id = ?",
                       (1 if request.is_active else 0, user_id))
        conn.commit()
        conn.close()
        log_user_action(logger, user_id, "admin_update_user", field="is_active", new_value=request.is_active)

    # 获取更新后的用户
    updated_user = user_db.get_user_by_id(user_id)
    updated_user.pop("password_hash", None)

    logger.info(f"Admin updated user: {user_id}")

    return {
        "success": True,
        "user": updated_user,
        "message": "User updated successfully"
    }


@router.delete("/users/{user_id}", response_model=dict)
async def delete_user(
    user_id: str,
    x_admin_token: str = Header(None, alias="X-Admin-Token")
):
    """
    删除用户（管理员专用）

    Args:
        user_id: 用户ID
        x_admin_token: 管理员令牌

    Returns:
        删除结果
    """
    verify_admin_token(x_admin_token)

    # 不允许删除默认开发用户
    if user_id == "dev_user":
        raise HTTPException(status_code=403, detail="Cannot delete dev user")

    user_db = get_user_db()
    user = user_db.get_user_by_id(user_id)

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # 删除用户
    user_db.delete_user(user_id)
    log_user_action(logger, user_id, "admin_delete_user", email=user["email"])
    logger.info(f"Admin deleted user: {user_id} ({user['email']})")

    return {
        "success": True,
        "message": f"User {user['email']} deleted successfully"
    }


@router.post("/users/{user_id}/password", response_model=dict)
async def reset_user_password(
    user_id: str,
    request: ResetPasswordRequest,
    x_admin_token: str = Header(None, alias="X-Admin-Token")
):
    """
    重置用户密码（管理员专用）

    Args:
        user_id: 用户ID
        request: 重置请求（可选 new_password）
        x_admin_token: 管理员令牌

    Returns:
        新密码（如果自动生成）
    """
    verify_admin_token(x_admin_token)

    user_db = get_user_db()
    user = user_db.get_user_by_id(user_id)

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # 生成新密码（如果未提供）
    if request.new_password:
        new_password = request.new_password
    else:
        import random
        import string
        new_password = ''.join(random.choices(string.ascii_letters + string.digits, k=12))

    # 哈希并更新密码
    password_hash = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    user_db.update_password(user_id, password_hash)

    log_user_action(logger, user_id, "admin_reset_password")
    logger.info(f"Admin reset password for user: {user_id}")

    return {
        "success": True,
        "message": "Password reset successfully",
        "new_password": new_password
    }
