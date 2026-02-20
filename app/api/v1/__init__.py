"""API v1 module."""

from app.api.v1.admin import router as admin_router
from app.api.v1.intent import router as intent_router

__all__ = [
    "admin_router",
    "intent_router",
]
