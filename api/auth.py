"""Authentication API endpoints for Hermes Agent."""

import os
import bcrypt
import jwt
import logging
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from database.user_db_sqlite import get_user_db
from api._user_sync import ensure_orm_user

logger = logging.getLogger("hermes-auth")

router = APIRouter(prefix="/api/auth", tags=["Auth"])

# JWT Configuration
JWT_SECRET = os.getenv("JWT_SECRET", "your-secret-key-change-in-production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24 * 7  # 7 days

# Dev mode
DEV_MODE = os.getenv("DEV_MODE", "false").lower() in ("1", "true", "yes")
DEFAULT_USER_EMAIL = os.getenv("DEFAULT_USER_EMAIL", "user@example.com")
DEFAULT_USER_PASSWORD = os.getenv("DEFAULT_USER_PASSWORD", "password123")


class LoginRequest(BaseModel):
    """Login request model"""
    email: str
    password: str


class RegisterRequest(BaseModel):
    """Register request model"""
    email: str
    password: str
    name: str = ""


class LoginResponse(BaseModel):
    """Login response model"""
    access_token: str
    user_id: str
    email: str


class RegisterResponse(BaseModel):
    """Register response model"""
    access_token: str
    user_id: str
    email: str
    name: str = ""


def create_access_token(user_id: str, email: str) -> str:
    """Create JWT access token"""
    payload = {
        "user_id": user_id,
        "email": email,
        "exp": datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS),
        "iat": datetime.utcnow()
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def verify_token(token: str) -> dict:
    """Verify JWT token and return payload"""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


def hash_password(password: str) -> str:
    """Hash password using bcrypt"""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


def verify_password(password: str, hashed: str) -> bool:
    """Verify password against hash"""
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))


@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    """
    User login

    Args:
        request: Login request with email and password

    Returns:
        Login response with access token
    """
    user_db = get_user_db()

    # Check default user in dev mode
    if DEV_MODE and request.email == DEFAULT_USER_EMAIL and request.password == DEFAULT_USER_PASSWORD:
        # Ensure default user exists in database
        user = user_db.get_user_by_email(request.email)
        if not user:
            user_id = "dev_user"
            hashed = hash_password(DEFAULT_USER_PASSWORD)
            user_db.create_user(user_id, request.email, hashed)
            # 同步写入 ORM 数据库
            ensure_orm_user(user_id, request.email, hashed, "Dev User")
            logger.info(f"Created default dev user: {request.email}")
        else:
            user_id = user["user_id"]
            # 确保 ORM 中也有该用户
            ensure_orm_user(user_id, request.email, user.get("password_hash", ""))
    else:
        # Normal login flow
        user = user_db.get_user_by_email(request.email)
        if not user:
            raise HTTPException(status_code=401, detail="Invalid email or password")

        if not verify_password(request.password, user["password_hash"]):
            raise HTTPException(status_code=401, detail="Invalid email or password")

        user_id = user["user_id"]
        # 确保 ORM 中也有该用户
        ensure_orm_user(user_id, request.email, user.get("password_hash", ""))

    # Create access token
    access_token = create_access_token(user_id, request.email)

    logger.info(f"User logged in: {request.email}")

    return LoginResponse(
        access_token=access_token,
        user_id=user_id,
        email=request.email
    )


@router.post("/register", response_model=RegisterResponse)
async def register(request: RegisterRequest):
    """
    用户注册

    注册成功后自动登录，返回 JWT token。

    Args:
        request: 注册请求（email, password, name）

    Returns:
        RegisterResponse with access_token
    """
    import uuid

    # 验证邮箱格式
    if not request.email or "@" not in request.email:
        raise HTTPException(status_code=400, detail="请输入有效的邮箱地址")

    # 验证密码长度
    if len(request.password) < 6:
        raise HTTPException(status_code=400, detail="密码长度至少 6 位")

    user_db = get_user_db()

    # 检查邮箱是否已注册
    if user_db.get_user_by_email(request.email):
        raise HTTPException(status_code=409, detail="该邮箱已注册")

    # 生成用户 ID
    user_id = f"user_{uuid.uuid4().hex[:12]}"
    hashed_pw = hash_password(request.password)

    # 写入 auth 库 (users.db)
    user_db.create_user(user_id, request.email, hashed_pw)

    # 同步写入 ORM 库 (edulingua.db)
    ensure_orm_user(user_id, request.email, hashed_pw, request.name)

    # 生成 token
    access_token = create_access_token(user_id, request.email)

    logger.info(f"新用户注册: {request.email} -> {user_id}")

    return RegisterResponse(
        access_token=access_token,
        user_id=user_id,
        email=request.email,
        name=request.name,
    )


@router.post("/verify")
async def verify_user_token(token: str):
    """
    Verify user token

    Args:
        token: JWT access token

    Returns:
        User info if token is valid
    """
    payload = verify_token(token)
    return {
        "user_id": payload["user_id"],
        "email": payload["email"]
    }


@router.get("/dev-check")
async def dev_mode_check():
    """
    Check if dev mode is enabled and return default credentials

    Returns:
        Dev mode status and default credentials (masked)
    """
    return {
        "dev_mode": DEV_MODE,
        "default_email": DEFAULT_USER_EMAIL if DEV_MODE else None,
        "has_default_password": bool(DEFAULT_USER_PASSWORD) if DEV_MODE else False
    }
