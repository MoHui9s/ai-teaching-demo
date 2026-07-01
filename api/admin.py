"""Admin endpoints for Hermes Agent API."""

import os
from fastapi import APIRouter, Header, HTTPException

router = APIRouter(prefix="/api/admin", tags=["Admin"])

ADMIN_TOKEN = os.getenv("ADMIN_TOKEN")


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
    if not ADMIN_TOKEN:
        raise HTTPException(status_code=401, detail="Admin interface not enabled")

    if x_admin_token != ADMIN_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid admin token")

    return {"success": True, "message": "Admin token verified"}

