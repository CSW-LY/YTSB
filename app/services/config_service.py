"""Configuration service for intent management."""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import AppIntent, Application, IntentCategory, IntentRule

logger = logging.getLogger(__name__)


class CacheEntry:
    """Cache entry with TTL."""

    def __init__(self, value: Any, ttl_seconds: int = 300):
        self.value = value
        self.expires_at = datetime.utcnow() + timedelta(seconds=ttl_seconds)

    def is_expired(self) -> bool:
        return datetime.utcnow() > self.expires_at


class LRUCache:
    """Simple LRU cache with TTL support."""

    def __init__(self, max_size: int = 100, ttl_seconds: int = 300):
        self.cache: Dict[str, CacheEntry] = {}
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self.access_order: List[str] = []
        self.lock = asyncio.Lock()

    async def get(self, key: str) -> Optional[Any]:
        async with self.lock:
            entry = self.cache.get(key)
            if entry is None or entry.is_expired():
                return None
            # Update access order
            if key in self.access_order:
                self.access_order.remove(key)
            self.access_order.append(key)
            return entry.value

    async def set(self, key: str, value: Any) -> None:
        async with self.lock:
            self.cache[key] = CacheEntry(value, self.ttl_seconds)
            # Update access order
            if key in self.access_order:
                self.access_order.remove(key)
            self.access_order.append(key)
            # Evict oldest if over size
            while len(self.cache) > self.max_size:
                oldest_key = self.access_order.pop(0)
                if oldest_key in self.cache:
                    del self.cache[oldest_key]

    async def invalidate(self, key: str = None) -> None:
        async with self.lock:
            if key:
                if key in self.cache:
                    del self.cache[key]
                if key in self.access_order:
                    self.access_order.remove(key)
            else:
                self.cache.clear()
                self.access_order.clear()

    async def clear(self) -> None:
        async with self.lock:
            self.cache.clear()
            self.access_order.clear()


class ConfigService:
    """Service for managing intent configuration from database."""

    def __init__(self, db_session: AsyncSession):
        """Initialize config service."""
        self.db = db_session
        self.app_cache = LRUCache(max_size=100, ttl_seconds=300)
        self.context_cache = LRUCache(max_size=100, ttl_seconds=300)

    async def get_app_config(
        self,
        app_key: str,
    ) -> Optional[AppIntent]:
        """Get app configuration by app key."""
        result = await self.db.execute(
            select(AppIntent).where(AppIntent.app_key == app_key)
        )
        return result.scalar_one_or_none()

    async def get_application_by_key(
        self,
        app_key: str,
    ) -> Optional[Application]:
        """Get application by app key."""
        result = await self.db.execute(
            select(Application).where(Application.app_key == app_key)
        )
        return result.scalar_one_or_none()

    async def get_application_by_id(
        self,
        application_id: int,
    ) -> Optional[Application]:
        """Get application by id."""
        result = await self.db.execute(
            select(Application).where(Application.id == application_id)
        )
        return result.scalar_one_or_none()

    async def get_active_categories(
        self,
        intent_ids: Optional[List[int]] = None,
    ) -> List[IntentCategory]:
        """Get active intent categories."""
        query = select(IntentCategory).where(IntentCategory.is_active == True)

        if intent_ids:
            query = query.where(IntentCategory.id.in_(intent_ids))

        result = await self.db.execute(query.order_by(IntentCategory.priority.desc()))
        return list(result.scalars().all())

    async def get_active_rules(
        self,
        category_ids: Optional[List[int]] = None,
    ) -> List[IntentRule]:
        """Get active intent rules."""
        query = select(IntentRule).where(IntentRule.is_active == True)

        if category_ids:
            query = query.where(IntentRule.category_id.in_(category_ids))

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_app_intent_context(
        self,
        app_key: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Get complete context for intent recognition with application binding.

        Returns:
            Dict with application, app config, categories, and rules
        """
        context_key = f"context:{app_key}"
        cached = await self.context_cache.get(context_key)

        if cached is None:
            application = await self.get_application_by_key(app_key)

            if not application:
                logger.warning(f"Application not found: {app_key}")
                logger.warning(f"This may cause 'app config not found' errors for requests using app_key='{app_key}'")
                return None

            app_config = await self.get_app_config(app_key)

            if not app_config:
                logger.warning(f"No configuration found for app: {app_key}")
                logger.warning(f"This may cause 'app config not found' errors for requests using app_key='{app_key}'")
                return None

            categories = await self.get_categories_by_application(
                application.id,
                is_active=True
            )
            category_ids = [c.id for c in categories]

            if not category_ids:
                logger.warning(f"No active categories found for app: {app_key}")
                logger.warning(f"This may cause 'app config not found' errors for requests using app_key='{app_key}'")
                return None

            rules = await self.get_active_rules(category_ids)

            context = {
                "application": application,
                "app_config": app_config,
                "categories": categories,
                "rules": rules,
            }

            await self.context_cache.set(context_key, context)
            return context

        return cached

    # ============================================================================
    # Admin Operations
    # ============================================================================

    async def create_category(
        self,
        application_id: int,
        code: str,
        name: str,
        description: Optional[str] = None,
        priority: int = 0,
    ) -> IntentCategory:
        """Create new intent category for specified application."""
        category = IntentCategory(
            application_id=application_id,
            code=code,
            name=name,
            description=description,
            priority=priority,
        )
        self.db.add(category)
        await self.db.flush()
        return category

    async def update_category(
        self,
        category_id: int,
        **kwargs,
    ) -> Optional[IntentCategory]:
        """Update intent category."""
        result = await self.db.execute(
            select(IntentCategory).where(IntentCategory.id == category_id)
        )
        category = result.scalar_one_or_none()

        if not category:
            return None

        for key, value in kwargs.items():
            if hasattr(category, key):
                setattr(category, key, value)

        await self.db.flush()
        await self.context_cache.invalidate()
        return category

    async def delete_category(self, category_id: int) -> bool:
        """Delete intent category."""
        result = await self.db.execute(
            select(IntentCategory).where(IntentCategory.id == category_id)
        )
        category = result.scalar_one_or_none()

        if not category:
            return False

        await self.db.delete(category)
        await self.db.flush()
        await self.context_cache.invalidate()
        return True

    async def create_rule(
        self,
        category_id: int,
        rule_type: str,
        content: str,
        weight: float = 1.0,
    ) -> IntentRule:
        """Create new intent rule."""
        rule = IntentRule(
            category_id=category_id,
            rule_type=rule_type,
            content=content,
            weight=weight,
        )
        self.db.add(rule)
        await self.db.flush()
        await self.context_cache.invalidate()
        return rule

    async def update_rule(
        self,
        rule_id: int,
        **kwargs,
    ) -> Optional[IntentRule]:
        """Update intent rule."""
        result = await self.db.execute(
            select(IntentRule).where(IntentRule.id == rule_id)
        )
        rule = result.scalar_one_or_none()

        if not rule:
            return None

        for key, value in kwargs.items():
            if hasattr(rule, key):
                setattr(rule, key, value)

        await self.db.flush()
        await self.context_cache.invalidate()
        return rule

    async def delete_rule(self, rule_id: int) -> bool:
        """Delete intent rule."""
        result = await self.db.execute(
            select(IntentRule).where(IntentRule.id == rule_id)
        )
        rule = result.scalar_one_or_none()

        if not rule:
            return False

        await self.db.delete(rule)
        await self.db.flush()
        await self.context_cache.invalidate()
        return True

    async def create_app_config(
        self,
        app_key: str,
        intent_ids: List[int],
        confidence_threshold: float = 0.7,
        **kwargs,
    ) -> AppIntent:
        """Create new app configuration."""
        app_config = AppIntent(
            app_key=app_key,
            intent_ids=intent_ids,
            confidence_threshold=confidence_threshold,
            **kwargs,
        )
        self.db.add(app_config)
        await self.db.flush()
        await self.context_cache.invalidate()
        return app_config

    async def update_app_config(
        self,
        app_key: str,
        **kwargs,
    ) -> Optional[AppIntent]:
        """Update app configuration."""
        app_config = await self.get_app_config(app_key)

        if not app_config:
            return None

        for key, value in kwargs.items():
            if hasattr(app_config, key):
                setattr(app_config, key, value)

        await self.db.flush()
        await self.context_cache.invalidate()
        return app_config

    async def delete_app_config(self, app_key: str) -> bool:
        """Delete app configuration."""
        app_config = await self.get_app_config(app_key)

        if not app_config:
            return False

        await self.db.delete(app_config)
        await self.db.flush()
        return True

    async def list_categories(
        self,
        is_active: Optional[bool] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[IntentCategory]:
        """List intent categories."""
        query = select(IntentCategory)

        if is_active is not None:
            query = query.where(IntentCategory.is_active == is_active)

        query = query.order_by(IntentCategory.priority.desc()).offset(offset).limit(limit)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def list_rules(
        self,
        category_id: Optional[int] = None,
        rule_type: Optional[str] = None,
        is_active: Optional[bool] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[IntentRule]:
        """List intent rules."""
        query = select(IntentRule)

        if category_id:
            query = query.where(IntentRule.category_id == category_id)

        if rule_type:
            query = query.where(IntentRule.rule_type == rule_type)

        if is_active is not None:
            query = query.where(IntentRule.is_active == is_active)

        query = query.offset(offset).limit(limit)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def list_app_configs(
        self,
        limit: int = 100,
        offset: int = 0,
    ) -> List[AppIntent]:
        """List app configurations."""
        query = select(AppIntent).offset(offset).limit(limit)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def create_application(
        self,
        app_key: str,
        name: str,
        description: Optional[str] = None,
    ) -> Application:
        """Create new application."""
        app = Application(
            app_key=app_key,
            name=name,
            description=description,
        )
        self.db.add(app)
        await self.db.flush()
        return app

    async def list_applications(
        self,
        is_active: Optional[bool] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Application]:
        """List all applications."""
        query = select(Application)

        if is_active is not None:
            query = query.where(Application.is_active == is_active)

        query = query.order_by(Application.created_at.desc()).offset(offset).limit(limit)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def delete_application(self, application_id: int) -> bool:
        """Delete application (cascade delete related categories and rules)."""
        result = await self.db.execute(
            select(Application).where(Application.id == application_id)
        )
        app = result.scalar_one_or_none()

        if not app:
            return False

        await self.db.delete(app)
        await self.db.flush()
        await self.context_cache.invalidate()
        return True

    async def get_categories_by_application(
        self,
        application_id: int,
        is_active: Optional[bool] = None,
    ) -> List[IntentCategory]:
        """Get categories for specified application."""
        query = select(IntentCategory).where(
            IntentCategory.application_id == application_id
        )

        if is_active is not None:
            query = query.where(IntentCategory.is_active == is_active)

        query = query.order_by(IntentCategory.priority.desc())

        result = await self.db.execute(query)
        return list(result.scalars().all())
