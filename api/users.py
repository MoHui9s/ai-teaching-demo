"""User management API endpoints for Hermes Agent (Admin only)."""

import logging
import os
from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel
from typing import Optional

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from database.user_db import get_user_db
from api.auth import hash_password

logger = logging.getLogger("hermes-users")

router = APIRouter(prefix="/api/admin/users", tags=["Admin"])

# Get admin token from environment
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", None)


def _verify_admin(admin_token: Optional[str]) -> None:
    """Verify admin token or raise exception."""
    if not ADMIN_TOKEN:
        raise HTTPException(status_code=404, detail="Admin interface not enabled")
    if not admin_token:
        raise HTTPException(status_code=401, detail="Admin token required")
    if admin_token != ADMIN_TOKEN:
        raise HTTPException(status_code=403, detail="Invalid admin token")


class CreateUserRequest(BaseModel):
    """Create user request model"""
    user_id: str
    email: str
    password: str


class UpdatePasswordRequest(BaseModel):
    """Update password request model"""
    new_password: str


@router.get("/list")
async def list_users(admin_token: Optional[str] = Header(None, alias="X-Admin-Token")):
    """List all users (Admin only)"""
    _verify_admin(admin_token)

    user_db = get_user_db()
    users = user_db.list_users()

    logger.info(f"Listed {len(users)} users")

    return {
        "users": users,
        "total": len(users)
    }


@router.post("/create")
async def create_user(request: CreateUserRequest, admin_token: Optional[str] = Header(None, alias="X-Admin-Token")):
    """Create a new user (Admin only)"""
    _verify_admin(admin_token)

    user_db = get_user_db()

    try:
        password_hash = hash_password(request.password)
        user_db.create_user(request.user_id, request.email, password_hash)

        logger.info(f"User created: {request.email} ({request.user_id})")

        return {
            "success": True,
            "message": "User created successfully",
            "user_id": request.user_id
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to create user: {e}")
        raise HTTPException(status_code=500, detail="Failed to create user")


@router.delete("/{user_id}")
async def delete_user(user_id: str, admin_token: Optional[str] = Header(None, alias="X-Admin-Token")):
    """Delete a user (Admin only)"""
    _verify_admin(admin_token)

    user_db = get_user_db()

    if user_db.delete_user(user_id):
        logger.info(f"User deleted: {user_id}")
        return {
            "success": True,
            "message": f"User {user_id} deleted successfully"
        }
    else:
        raise HTTPException(status_code=404, detail=f"User not found: {user_id}")


@router.put("/{user_id}/password")
async def update_user_password(user_id: str, request: UpdatePasswordRequest, admin_token: Optional[str] = Header(None, alias="X-Admin-Token")):
    """Update user password (Admin only)"""
    _verify_admin(admin_token)

    user_db = get_user_db()

    password_hash = hash_password(request.new_password)

    if user_db.update_password(user_id, password_hash):
        logger.info(f"Password updated for user: {user_id}")
        return {
            "success": True,
            "message": f"Password updated for user {user_id}"
        }
    else:
        raise HTTPException(status_code=404, detail=f"User not found: {user_id}")


@router.get("/stats")
async def get_user_stats(admin_token: Optional[str] = Header(None, alias="X-Admin-Token")):
    """Get user statistics (Admin only)"""
    _verify_admin(admin_token)

    user_db = get_user_db()
    users = user_db.list_users()

    return {
        "total_users": len(users),
        "users": users
    }
