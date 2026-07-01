"""Authentication middleware for Hermes Agent."""

import os
from typing import Optional
from fastapi import HTTPException, Header

# Admin configuration
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", None)


def verify_admin_token(admin_token: Optional[str]) -> None:
    """Verify admin token for admin-only endpoints."""
    if not ADMIN_TOKEN:
        raise HTTPException(status_code=404, detail="Admin interface not enabled")
    if not admin_token:
        raise HTTPException(status_code=401, detail="Admin token required")
    if admin_token != ADMIN_TOKEN:
        raise HTTPException(status_code=403, detail="Invalid admin token")


def get_admin_token_from_header(admin_token: str = Header(None, alias="X-Admin-Token")) -> str:
    """Get and verify admin token from header."""
    if not admin_token:
        raise HTTPException(status_code=401, detail="Admin token required")
    if admin_token != ADMIN_TOKEN:
        raise HTTPException(status_code=403, detail="Invalid admin token")
    return admin_token
