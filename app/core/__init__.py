"""Core module for configuration and utilities."""

from app.core.cache import (
    CacheManager,
    cache_manager,
    generate_cache_key,
    get_cache,
)
from app.core.config import Settings, get_settings
from app.core.log_service import get_async_log_service
from app.core.recognizer import (
    get_recognizer_chain,
    get_recognizer_chain_for_app,
    clear_recognizer_cache,
    get_llm_recognizer,
)
from app.core.security import (
    verify_admin_api_key,
    verify_api_key,
)

__all__ = [
    "Settings",
    "get_settings",
    "CacheManager",
    "cache_manager",
    "get_cache",
    "generate_cache_key",
    "verify_api_key",
    "verify_admin_api_key",
    "get_async_log_service",
    "get_recognizer_chain",
    "get_recognizer_chain_for_app",
    "clear_recognizer_cache",
    "get_llm_recognizer",
]
