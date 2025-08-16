"""
API routes module.

This module imports and exposes the routers for different API endpoints.
"""

from fastapi import APIRouter

from .routes.messages import router as messages_router
from .routes.state import router as state_router
from .routes.threads import router as threads_router

# Create auth router (placeholder for now)
auth_router = APIRouter()


@auth_router.get("/auth/status")
async def auth_status():
    """Get authentication status."""
    from .auth import get_auth_config

    auth_config = get_auth_config()
    return {"auth_enabled": auth_config.require_auth()}


__all__ = ["auth_router", "threads_router", "messages_router", "state_router"]
