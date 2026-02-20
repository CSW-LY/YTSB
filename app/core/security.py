"""Security utilities for API authentication."""

import asyncio
import hashlib
import hmac
import logging
from datetime import datetime, timedelta
from typing import Optional

from fastapi import Header, HTTPException, status

from app.core.config import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()

# API Key cache (key_prefix -> cached data)
_api_key_cache: dict[str, dict] = {}
_api_key_cache_lock = asyncio.Lock()
_CACHE_TTL = timedelta(minutes=5)


def _verify_hmac_signature(api_key: str, signature: str, secret: str) -> bool:
    """Verify HMAC signature of API key."""
    expected_signature = hmac.new(
        secret.encode('utf-8'),
        api_key.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected_signature, signature)


def _split_api_key(full_key: Optional[str]) -> tuple[Optional[str], Optional[str]]:
    """Split API key into key_id and signature."""
    if not full_key:
        return None, None

    parts = full_key.split('.')
    if len(parts) != 2:
        return full_key, None
    return parts[0], parts[1]


async def _update_last_used_async(key_prefix: str) -> None:
    """Update last_used_at timestamp asynchronously."""
    try:
        from app.db import async_session_maker
        from app.models.database import ApiKey
        from sqlalchemy import select

        async with async_session_maker() as session:
            result = await session.execute(
                select(ApiKey).where(ApiKey.key_prefix == key_prefix)
            )
            api_key_record = result.scalar_one_or_none()
            if api_key_record:
                api_key_record.last_used_at = datetime.utcnow()
                await session.commit()
    except Exception as e:
        logger.error(f"Failed to update last_used_at: {e}")


async def verify_api_key(
    x_api_key: Optional[str] = Header(None, alias=settings.api_key_header),
) -> Optional[dict]:
    """Verify API key for regular endpoints - OPTIONAL for UI access."""
    if not x_api_key:
        return None

    # Check if it's admin API key (bypass database check)
    if settings.admin_api_key and x_api_key == settings.admin_api_key:
        logger.debug("Admin API key used for regular endpoint")
        return {
            'key_id': None,
            'key_prefix': 'admin',
            'permissions': {},
            'rate_limit': None,
            'app_keys': None,
        }
    
    # If x_api_key was provided but not admin key, continue with verification

    # Check if signature verification is enabled
    api_secret = getattr(settings, 'api_secret', None)
    if api_secret:
        key_id, signature = _split_api_key(x_api_key)
        if signature:
            if not _verify_hmac_signature(key_id, signature, api_secret):
                logger.warning(f"Invalid API key signature for key_id: {key_id}")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid API key signature",
                )

    # Extract key prefix
    if x_api_key.startswith('sk_'):
        # New format: sk_xxxx_yyyy
        key_parts = x_api_key.split('_')
        if len(key_parts) >= 2:
            key_prefix = f"sk_{key_parts[1]}"
        else:
            key_prefix = x_api_key[:20]
    else:
        # Legacy format
        key_prefix = x_api_key[:20]

    # Check cache first
    async with _api_key_cache_lock:
        cached = _api_key_cache.get(key_prefix)
        if cached and datetime.utcnow() < cached['expires_at']:
            # Schedule async update of last_used_at
            asyncio.create_task(_update_last_used_async(key_prefix))
            return cached['data']

    # Cache miss - verify against database
    from app.db import async_session_maker
    from app.models.database import ApiKey
    from sqlalchemy import select
    import bcrypt
    import json

    async with async_session_maker() as session:
        # Search for API key by prefix
        result = await session.execute(
            select(ApiKey).where(
                ApiKey.key_prefix == key_prefix,
                ApiKey.is_active == True
            )
        )
        api_key_record = result.scalar_one_or_none()

        if not api_key_record:
            logger.warning(f"API key not found: {key_prefix}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid API key",
            )

        # Check if key is expired
        if api_key_record.expires_at and api_key_record.expires_at < datetime.utcnow():
            logger.warning(f"API key expired: {key_prefix}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="API key expired",
            )

        # Verify the full key against hash
        if not bcrypt.checkpw(x_api_key.encode('utf-8'), api_key_record.key_hash.encode('utf-8')):
            logger.warning(f"Invalid API key hash: {key_prefix}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid API key",
            )

        # Cache the result
        cached_data = {
            'key_id': api_key_record.id,
            'key_prefix': api_key_record.key_prefix,
            'permissions': json.loads(api_key_record.permissions),
            'rate_limit': api_key_record.rate_limit,
            'app_keys': api_key_record.app_keys
        }

        async with _api_key_cache_lock:
            _api_key_cache[key_prefix] = {
                'data': cached_data,
                'expires_at': datetime.utcnow() + _CACHE_TTL
            }

        # Update last used timestamp
        api_key_record.last_used_at = datetime.utcnow()
        await session.commit()

        return cached_data

    logger.debug(f"API request with key: {x_api_key[:8]}...")


async def verify_admin_api_key(
    x_api_key: Optional[str] = Header(None, alias=settings.api_key_header),
) -> None:
    """Verify admin API key for admin endpoints."""
    if not settings.admin_api_key:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Admin API not configured",
        )

    if x_api_key != settings.admin_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid admin API key",
        )

    logger.debug("Admin API request authorized")
