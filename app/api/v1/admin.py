"""Admin API endpoints for intent configuration management."""

import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import clear_recognizer_cache
from app.core.security import verify_admin_api_key
from app.core.config import get_settings
from app.db import async_session_maker
from fastapi import Header
from app.models.database import IntentCategory, IntentRecognitionLog
from app.models.schema import (
    AppIntentCreate,
    AppIntentResponse,
    AppIntentUpdate,
    IntentCategoryCreate,
    IntentCategoryResponse,
    IntentCategoryUpdate,
    IntentRuleCreate,
    IntentRuleResponse,
    IntentRuleUpdate,
)
from sqlalchemy import and_
from app.services.config_service import ConfigService

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/admin",
    tags=["admin"],
)


# ============================================================================
# Dependencies
# ============================================================================

settings = get_settings()


async def optional_admin_auth(x_api_key: str = Header(None)) -> None:
    """Optional admin authentication - allows UI access without API key."""
    if x_api_key and x_api_key != settings.admin_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid admin API key"
        )
    return None


async def get_config_service(
    db: AsyncSession = Depends(lambda: None),
) -> ConfigService:
    """Get config service instance."""

    async with async_session_maker() as session:
        yield ConfigService(session)


# ============================================================================
# Intent Category Endpoints
# ============================================================================

@router.post("/intents", response_model=IntentCategoryResponse, status_code=status.HTTP_201_CREATED)
async def create_intent_category(
    data: IntentCategoryCreate,
    config_service: ConfigService = Depends(get_config_service),
) -> IntentCategoryResponse:
    """Create a new intent category."""

    async with async_session_maker() as session:
        svc = ConfigService(session)
        category = await svc.create_category(
            code=data.code,
            name=data.name,
            description=data.description,
            priority=data.priority,
        )

        await session.commit()
        await session.refresh(category)

    logger.info(f"Created intent category: {category.code}")
    return IntentCategoryResponse.model_validate(category)


@router.get("/intents", response_model=List[IntentCategoryResponse])
async def list_intent_categories(
    is_active: bool = Query(None, description="Filter by active status"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    config_service: ConfigService = Depends(get_config_service),
) -> List[IntentCategoryResponse]:
    """List all intent categories."""

    async with async_session_maker() as session:
        svc = ConfigService(session)
        categories = await svc.list_categories(
            is_active=is_active,
            limit=limit,
            offset=offset,
        )

    return [IntentCategoryResponse.model_validate(c) for c in categories]


@router.get("/intents/{category_id}", response_model=IntentCategoryResponse)
async def get_intent_category(
    category_id: int,
    config_service: ConfigService = Depends(get_config_service),
) -> IntentCategoryResponse:
    """Get a specific intent category."""
    from sqlalchemy import select

    async with async_session_maker() as session:
        result = await session.execute(
            select(IntentCategory).where(IntentCategory.id == category_id)
        )
        category = result.scalar_one_or_none()

    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Intent category not found: {category_id}",
        )

    return IntentCategoryResponse.model_validate(category)


@router.put("/intents/{category_id}", response_model=IntentCategoryResponse)
async def update_intent_category(
    category_id: int,
    data: IntentCategoryUpdate,
    config_service: ConfigService = Depends(get_config_service),
) -> IntentCategoryResponse:
    """Update an intent category."""

    async with async_session_maker() as session:
        svc = ConfigService(session)
        category = await svc.update_category(
            category_id,
            **data.model_dump(exclude_unset=True),
        )

        if not category:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Intent category not found: {category_id}",
            )

        await session.commit()
        await session.refresh(category)

    logger.info(f"Updated intent category: {category_id}")
    return IntentCategoryResponse.model_validate(category)


@router.delete("/intents/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_intent_category(
    category_id: int,
    config_service: ConfigService = Depends(get_config_service),
) -> None:
    """Delete an intent category."""

    async with async_session_maker() as session:
        svc = ConfigService(session)
        success = await svc.delete_category(category_id)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Intent category not found: {category_id}",
            )

        await session.commit()

    logger.info(f"Deleted intent category: {category_id}")


# ============================================================================
# Intent Rule Endpoints
# ============================================================================

@router.post("/rules", response_model=IntentRuleResponse, status_code=status.HTTP_201_CREATED)
async def create_intent_rule(
    data: IntentRuleCreate,
    config_service: ConfigService = Depends(get_config_service),
) -> IntentRuleResponse:
    """Create a new intent rule."""

    async with async_session_maker() as session:
        svc = ConfigService(session)
        rule = await svc.create_rule(
            category_id=data.category_id,
            rule_type=data.rule_type,
            content=data.content,
            weight=data.weight,
        )

        await session.commit()
        await session.refresh(rule)

    logger.info(f"Created intent rule: {rule.id}")
    return IntentRuleResponse.model_validate(rule)


@router.get("/rules", response_model=List[IntentRuleResponse])
async def list_intent_rules(
    category_id: int = Query(None, description="Filter by category ID"),
    rule_type: str = Query(None, description="Filter by rule type"),
    is_active: bool = Query(None, description="Filter by active status"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    config_service: ConfigService = Depends(get_config_service),
) -> List[IntentRuleResponse]:
    """List all intent rules."""

    async with async_session_maker() as session:
        svc = ConfigService(session)
        rules = await svc.list_rules(
            category_id=category_id,
            rule_type=rule_type,
            is_active=is_active,
            limit=limit,
            offset=offset,
        )

    return [IntentRuleResponse.model_validate(r) for r in rules]


@router.put("/rules/{rule_id}", response_model=IntentRuleResponse)
async def update_intent_rule(
    rule_id: int,
    data: IntentRuleUpdate,
    config_service: ConfigService = Depends(get_config_service),
) -> IntentRuleResponse:
    """Update an intent rule."""

    async with async_session_maker() as session:
        svc = ConfigService(session)
        rule = await svc.update_rule(
            rule_id,
            **data.model_dump(exclude_unset=True),
        )

        if not rule:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Intent rule not found: {rule_id}",
            )

        await session.commit()
        await session.refresh(rule)

    logger.info(f"Updated intent rule: {rule_id}")
    return IntentRuleResponse.model_validate(rule)


@router.delete("/rules/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_intent_rule(
    rule_id: int,
    config_service: ConfigService = Depends(get_config_service),
) -> None:
    """Delete an intent rule."""

    async with async_session_maker() as session:
        svc = ConfigService(session)
        success = await svc.delete_rule(rule_id)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Intent rule not found: {rule_id}",
            )

        await session.commit()

    logger.info(f"Deleted intent rule: {rule_id}")


# ============================================================================
# App Configuration Endpoints
# ============================================================================

@router.post("/apps/{app_key}/intents", response_model=AppIntentResponse, status_code=status.HTTP_201_CREATED)
async def create_app_config(
    app_key: str,
    data: AppIntentCreate,
    config_service: ConfigService = Depends(get_config_service),
) -> AppIntentResponse:
    """Create app intent configuration."""

    async with async_session_maker() as session:
        svc = ConfigService(session)
        app_config = await svc.create_app_config(
            app_key=app_key,
            intent_ids=data.intent_ids,
            confidence_threshold=data.confidence_threshold,
            fallback_intent_code=data.fallback_intent_code,
            enable_cache=data.enable_cache,
            enable_keyword_matching=data.enable_keyword_matching,
            enable_regex_matching=data.enable_regex_matching,
            enable_semantic_matching=data.enable_semantic_matching,
            enable_llm_fallback=data.enable_llm_fallback,
        )

        await session.commit()
        await session.refresh(app_config)

    logger.info(f"Created app config: {app_key}")
    return AppIntentResponse.model_validate(app_config)


@router.get("/apps/{app_key}/intents", response_model=AppIntentResponse)
async def get_app_config(
    app_key: str,
    config_service: ConfigService = Depends(get_config_service),
) -> AppIntentResponse:
    """Get app intent configuration."""

    async with async_session_maker() as session:
        svc = ConfigService(session)
        app_config = await svc.get_app_config(app_key)

    if not app_config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"App configuration not found: {app_key}",
        )

    return AppIntentResponse.model_validate(app_config)


@router.put("/apps/{app_key}/intents", response_model=AppIntentResponse)
async def update_app_config(
    app_key: str,
    data: AppIntentUpdate,
    config_service: ConfigService = Depends(get_config_service),
) -> AppIntentResponse:
    """Update app intent configuration."""

    async with async_session_maker() as session:
        svc = ConfigService(session)
        app_config = await svc.update_app_config(
            app_key,
            **data.model_dump(exclude_unset=True),
        )

        if not app_config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"App configuration not found: {app_key}",
            )

        await session.commit()
        await session.refresh(app_config)

        logger.info(f"Updated app config: {app_key}")
        await clear_recognizer_cache(app_key)
        return AppIntentResponse.model_validate(app_config)


@router.delete("/apps/{app_key}/intents", status_code=status.HTTP_204_NO_CONTENT)
async def delete_app_config(
    app_key: str,
    config_service: ConfigService = Depends(get_config_service),
) -> None:
    """Delete app intent configuration."""

    async with async_session_maker() as session:
        svc = ConfigService(session)
        success = await svc.delete_app_config(app_key)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"App configuration not found: {app_key}",
            )

        await session.commit()
        await clear_recognizer_cache(app_key)

    logger.info(f"Deleted app config: {app_key}")


# ============================================================================
# API Key Management Endpoints
# ============================================================================

from app.models.schema import ApiKeyCreate, ApiKeyUpdate, ApiKeyResponse, ApiKeyCreateResponse, ApiKeyListResponse
from app.models.database import ApiKey
import secrets
import bcrypt
import json
from datetime import datetime
from sqlalchemy import select, func


@router.post("/api-keys", response_model=ApiKeyCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_api_key(
    data: ApiKeyCreate,
    config_service: ConfigService = Depends(get_config_service),
    _auth: None = Depends(optional_admin_auth),
) -> ApiKeyCreateResponse:
    """Create a new API key."""

    # Generate API key
    key_prefix = f"sk_{secrets.token_urlsafe(8)}"
    key_suffix = secrets.token_urlsafe(32)
    api_key = f"{key_prefix}_{key_suffix}"
    
    # Hash the API key
    key_hash = bcrypt.hashpw(api_key.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    # Prepare permissions JSON
    permissions_json = json.dumps(data.permissions)

    async with async_session_maker() as session:
        # Create API key record
        new_api_key = ApiKey(
            key_hash=key_hash,
            key_prefix=key_prefix,
            full_key=api_key,
            description=data.description,
            permissions=permissions_json,
            rate_limit=data.rate_limit,
            app_keys=data.app_keys,
            expires_at=data.expires_at,
            is_active=True
        )
        session.add(new_api_key)
        await session.commit()
        await session.refresh(new_api_key)

    logger.info(f"Created API key: {key_prefix}")

    # Parse permissions JSON, handle empty strings and empty lists
    try:
        parsed_permissions = json.loads(new_api_key.permissions) if new_api_key.permissions else {}
        # If permissions is a list, convert to empty dict
        if isinstance(parsed_permissions, list):
            parsed_permissions = {}
    except (json.JSONDecodeError, TypeError):
        parsed_permissions = {}

    # Return response with the actual API key (only returned once)
    return ApiKeyCreateResponse(
        id=new_api_key.id,
        key_prefix=new_api_key.key_prefix,
        full_key=new_api_key.full_key,
        description=new_api_key.description,
        rate_limit=new_api_key.rate_limit,
        app_keys=new_api_key.app_keys,
        expires_at=new_api_key.expires_at,
        permissions=parsed_permissions,
        is_active=new_api_key.is_active,
        created_at=new_api_key.created_at,
        last_used_at=new_api_key.last_used_at,
        api_key=api_key
    )


@router.get("/api-keys", response_model=ApiKeyListResponse)
async def list_api_keys(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=100, description="Items per page"),
    config_service: ConfigService = Depends(get_config_service),
    _auth: None = Depends(optional_admin_auth),
) -> ApiKeyListResponse:
    """List all API keys with pagination."""

    async with async_session_maker() as session:
        # Count total API keys
        count_query = select(func.count(ApiKey.id))
        count_result = await session.execute(count_query)
        total_items = count_result.scalar() or 0
        
        # Calculate total pages
        total_pages = (total_items + page_size - 1) // page_size
        
        # Apply pagination
        offset = (page - 1) * page_size
        query = select(ApiKey).offset(offset).limit(page_size).order_by(ApiKey.created_at.desc())
        result = await session.execute(query)
        api_keys = result.scalars().all()
        
        # Format response
        items = []
        for key in api_keys:
            # Parse permissions JSON, handle empty strings and empty lists
            try:
                parsed_permissions = json.loads(key.permissions) if key.permissions else {}
                # If permissions is a list, convert to empty dict
                if isinstance(parsed_permissions, list):
                    parsed_permissions = {}
            except (json.JSONDecodeError, TypeError):
                parsed_permissions = {}

            items.append(ApiKeyResponse(
                id=key.id,
                key_prefix=key.key_prefix,
                full_key=key.full_key if key.full_key else None,
                description=key.description,
                rate_limit=key.rate_limit,
                app_keys=key.app_keys,
                expires_at=key.expires_at,
                permissions=parsed_permissions,
                is_active=key.is_active,
                created_at=key.created_at,
                last_used_at=key.last_used_at
            ))

    return ApiKeyListResponse(
        items=items,
        total_items=total_items,
        total_pages=total_pages,
        current_page=page,
        page_size=page_size
    )


@router.get("/api-keys/{key_id}", response_model=ApiKeyResponse)
async def get_api_key(
    key_id: int,
    config_service: ConfigService = Depends(get_config_service),
    _auth: None = Depends(optional_admin_auth),
) -> ApiKeyResponse:
    """Get a specific API key by ID."""

    async with async_session_maker() as session:
        result = await session.execute(select(ApiKey).where(ApiKey.id == key_id))
        api_key = result.scalar_one_or_none()
        
        if not api_key:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"API key not found: {key_id}",
            )

    # Parse permissions JSON, handle empty strings and empty lists
    try:
        parsed_permissions = json.loads(api_key.permissions) if api_key.permissions else {}
        # If permissions is a list, convert to empty dict
        if isinstance(parsed_permissions, list):
            parsed_permissions = {}
    except (json.JSONDecodeError, TypeError):
        parsed_permissions = {}

    return ApiKeyResponse(
        id=api_key.id,
        key_prefix=api_key.key_prefix,
        full_key=api_key.full_key if api_key.full_key else None,
        description=api_key.description,
        rate_limit=api_key.rate_limit,
        app_keys=api_key.app_keys,
        expires_at=api_key.expires_at,
        permissions=parsed_permissions,
        is_active=api_key.is_active,
        created_at=api_key.created_at,
        last_used_at=api_key.last_used_at
    )


@router.put("/api-keys/{key_id}", response_model=ApiKeyResponse)
async def update_api_key(
    key_id: int,
    data: ApiKeyUpdate,
    _auth: None = Depends(optional_admin_auth),
    config_service: ConfigService = Depends(get_config_service),
) -> ApiKeyResponse:
    """Update an API key."""

    async with async_session_maker() as session:
        result = await session.execute(select(ApiKey).where(ApiKey.id == key_id))
        api_key = result.scalar_one_or_none()
        
        if not api_key:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"API key not found: {key_id}",
            )
        
        # Update fields
        if data.description is not None:
            api_key.description = data.description
        if data.permissions is not None:
            api_key.permissions = json.dumps(data.permissions) if data.permissions else '{}'
        if data.rate_limit is not None:
            api_key.rate_limit = data.rate_limit
        if data.app_keys is not None:
            api_key.app_keys = data.app_keys
        if data.expires_at is not None:
            api_key.expires_at = data.expires_at
        if data.is_active is not None:
            api_key.is_active = data.is_active
        
        await session.commit()
        await session.refresh(api_key)

    logger.info(f"Updated API key: {api_key.key_prefix}")

    # Parse permissions JSON, handle empty strings and empty lists
    try:
        parsed_permissions = json.loads(api_key.permissions) if api_key.permissions else {}
        # If permissions is a list, convert to empty dict
        if isinstance(parsed_permissions, list):
            parsed_permissions = {}
    except (json.JSONDecodeError, TypeError):
        parsed_permissions = {}

    return ApiKeyResponse(
        id=api_key.id,
        key_prefix=api_key.key_prefix,
        full_key=api_key.full_key,
        description=api_key.description,
        rate_limit=api_key.rate_limit,
        app_keys=api_key.app_keys,
        expires_at=api_key.expires_at,
        permissions=parsed_permissions,
        is_active=api_key.is_active,
        created_at=api_key.created_at,
        last_used_at=api_key.last_used_at
    )


@router.delete("/api-keys/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_api_key(
    key_id: int,
    config_service: ConfigService = Depends(get_config_service),
    _auth: None = Depends(optional_admin_auth),
) -> None:
    """Delete an API key."""

    async with async_session_maker() as session:
        result = await session.execute(select(ApiKey).where(ApiKey.id == key_id))
        api_key = result.scalar_one_or_none()
        
        if not api_key:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"API key not found: {key_id}",
            )
        
        await session.delete(api_key)
        await session.commit()

    logger.info(f"Deleted API key: {api_key.key_prefix}")


@router.get("/api-keys/{key_id}/stats")
async def get_api_key_stats(
    key_id: int,
    days: int = Query(7, ge=1, le=30, description="Number of days to analyze"),
    config_service: ConfigService = Depends(get_config_service),
) -> dict:
    """Get usage statistics for a specific API key."""
    from datetime import datetime, timedelta

    async with async_session_maker() as session:
        # Verify API key exists
        api_key_result = await session.execute(select(ApiKey).where(ApiKey.id == key_id))
        api_key = api_key_result.scalar_one_or_none()
        
        if not api_key:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"API key not found: {key_id}",
            )
        
        # Calculate date range
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        # Query usage statistics
        # Total requests
        total_requests = await session.execute(
            select(func.count(IntentRecognitionLog.id))
            .where(
                IntentRecognitionLog.api_key_id == key_id,
                IntentRecognitionLog.created_at >= start_date
            )
        )
        total_count = total_requests.scalar() or 0
        
        # Successful requests
        success_requests = await session.execute(
            select(func.count(IntentRecognitionLog.id))
            .where(
                IntentRecognitionLog.api_key_id == key_id,
                IntentRecognitionLog.is_success == True,
                IntentRecognitionLog.created_at >= start_date
            )
        )
        success_count = success_requests.scalar() or 0
        
        # Average response time
        avg_time = await session.execute(
            select(func.avg(IntentRecognitionLog.processing_time_ms))
            .where(
                IntentRecognitionLog.api_key_id == key_id,
                IntentRecognitionLog.is_success == True,
                IntentRecognitionLog.processing_time_ms.isnot(None),
                IntentRecognitionLog.created_at >= start_date
            )
        )
        avg_processing_time = avg_time.scalar() or 0
        
        # Top apps used
        top_apps = await session.execute(
            select(
                IntentRecognitionLog.app_key,
                func.count(IntentRecognitionLog.id).label('count')
            )
            .where(
                IntentRecognitionLog.api_key_id == key_id,
                IntentRecognitionLog.created_at >= start_date
            )
            .group_by(IntentRecognitionLog.app_key)
            .order_by(func.count(IntentRecognitionLog.id).desc())
            .limit(10)
        )
        top_apps_list = [
            {"app_key": row[0], "count": row[1]}
            for row in top_apps.all()
        ]
        
        # Daily usage trend
        # Note: This is a simplified version, actual implementation would use date_trunc
        daily_trend = await session.execute(
            select(
                func.date_trunc('day', IntentRecognitionLog.created_at).label('date'),
                func.count(IntentRecognitionLog.id).label('count')
            )
            .where(
                IntentRecognitionLog.api_key_id == key_id,
                IntentRecognitionLog.created_at >= start_date
            )
            .group_by(func.date_trunc('day', IntentRecognitionLog.created_at))
            .order_by(func.date_trunc('day', IntentRecognitionLog.created_at))
        )
        trend_list = [
            {"date": row[0].isoformat() if row[0] else None, "count": row[1]}
            for row in daily_trend.all()
        ]
        
        # Calculate success rate
        success_rate = (success_count / total_count * 100) if total_count > 0 else 0
        
        return {
            "api_key_id": key_id,
            "api_key_prefix": api_key.key_prefix,
            "description": api_key.description,
            "period": f"Last {days} days",
            "statistics": {
                "total_requests": total_count,
                "successful_requests": success_count,
                "failed_requests": total_count - success_count,
                "success_rate": success_rate,
                "average_processing_time_ms": avg_processing_time,
                "top_apps": top_apps_list,
                "daily_trend": trend_list
            }
        }


@router.get("/api-keys/stats/summary")
async def get_api_keys_summary_stats(
    days: int = Query(7, ge=1, le=30, description="Number of days to analyze"),
    config_service: ConfigService = Depends(get_config_service),
) -> dict:
    """Get summary statistics for all API keys."""
    from datetime import datetime, timedelta

    async with async_session_maker() as session:
        # Calculate date range
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        # Total API keys
        total_api_keys = await session.execute(
            select(func.count(ApiKey.id))
            .where(ApiKey.is_active == True)
        )
        active_api_keys = total_api_keys.scalar() or 0
        
        # Total requests across all API keys
        total_requests = await session.execute(
            select(func.count(IntentRecognitionLog.id))
            .where(IntentRecognitionLog.created_at >= start_date)
        )
        total_count = total_requests.scalar() or 0
        
        # Top API keys by usage
        top_api_keys = await session.execute(
            select(
                ApiKey.id,
                ApiKey.key_prefix,
                ApiKey.description,
                func.count(IntentRecognitionLog.id).label('count')
            )
            .outerjoin(
                IntentRecognitionLog,
                and_(
                    IntentRecognitionLog.api_key_id == ApiKey.id,
                    IntentRecognitionLog.created_at >= start_date
                )
            )
            .group_by(ApiKey.id, ApiKey.key_prefix, ApiKey.description)
            .order_by(func.count(IntentRecognitionLog.id).desc())
            .limit(10)
        )
        top_api_keys_list = [
            {
                "id": row[0],
                "key_prefix": row[1],
                "description": row[2],
                "request_count": row[3] or 0
            }
            for row in top_api_keys.all()
        ]
        
        return {
            "period": f"Last {days} days",
            "summary": {
                "active_api_keys": active_api_keys,
                "total_requests": total_count,
                "top_api_keys_by_usage": top_api_keys_list
            }
        }


@router.get("/apps", response_model=List[AppIntentResponse])
async def list_app_configs(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    config_service: ConfigService = Depends(get_config_service),
) -> List[AppIntentResponse]:
    """List all app configurations."""

    async with async_session_maker() as session:
        svc = ConfigService(session)
        app_configs = await svc.list_app_configs(
            limit=limit,
            offset=offset,
        )

    return [AppIntentResponse.model_validate(c) for c in app_configs]


# ============================================================================
# Intent Recognition Log Endpoints
# ============================================================================

from app.models.database import IntentRecognitionLog
from datetime import datetime

@router.get("/logs/recognition", response_model=List[dict])
async def list_recognition_logs(
    app_key: str = Query(None, description="Filter by app key"),
    intent: str = Query(None, description="Filter by recognized intent"),
    is_success: bool = Query(None, description="Filter by success status"),
    start_time: datetime = Query(None, description="Filter by start time"),
    end_time: datetime = Query(None, description="Filter by end time"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    config_service: ConfigService = Depends(get_config_service),
) -> List[dict]:
    """List intent recognition logs with filtering and pagination."""
    from sqlalchemy import select

    async with async_session_maker() as session:
        query = select(IntentRecognitionLog)
        
        # Apply filters
        if app_key:
            query = query.where(IntentRecognitionLog.app_key == app_key)
        if intent:
            query = query.where(IntentRecognitionLog.recognized_intent == intent)
        if is_success is not None:
            query = query.where(IntentRecognitionLog.is_success == is_success)
        if start_time:
            query = query.where(IntentRecognitionLog.created_at >= start_time)
        if end_time:
            query = query.where(IntentRecognitionLog.created_at <= end_time)
        
        # Apply pagination and order by creation time (newest first)
        query = query.order_by(IntentRecognitionLog.created_at.desc())
        query = query.limit(limit).offset(offset)
        
        result = await session.execute(query)
        logs = result.scalars().all()
    
    # Convert to dict format
    return [{
        "id": log.id,
        "app_key": log.app_key,
        "input_text": log.input_text,
        "recognized_intent": log.recognized_intent,
        "confidence": log.confidence,
        "processing_time_ms": log.processing_time_ms,
        "is_success": log.is_success,
        "error_message": log.error_message,
        "recognition_chain": log.recognition_chain,
        "matched_rules": log.matched_rules,
        "created_at": log.created_at.isoformat() if log.created_at else None
    } for log in logs]


@router.get("/logs/recognition/{log_id}", response_model=dict)
async def get_recognition_log(
    log_id: int,
    config_service: ConfigService = Depends(get_config_service),
) -> dict:
    """Get a specific recognition log by ID."""
    from sqlalchemy import select

    async with async_session_maker() as session:
        result = await session.execute(
            select(IntentRecognitionLog).where(IntentRecognitionLog.id == log_id)
        )
        log = result.scalar_one_or_none()

    if not log:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Recognition log not found: {log_id}",
        )
    
    # Return detailed log information
    return {
        "id": log.id,
        "app_key": log.app_key,
        "input_text": log.input_text,
        "recognized_intent": log.recognized_intent,
        "confidence": log.confidence,
        "processing_time_ms": log.processing_time_ms,
        "is_success": log.is_success,
        "error_message": log.error_message,
        "recognition_chain": log.recognition_chain,
        "matched_rules": log.matched_rules,
        "created_at": log.created_at.isoformat() if log.created_at else None
    }


@router.get("/logs/recognition/stats", response_model=dict)
async def get_recognition_stats(
    app_key: str = Query(None, description="Filter by app key"),
    start_time: datetime = Query(None, description="Filter by start time"),
    end_time: datetime = Query(None, description="Filter by end time"),
    config_service: ConfigService = Depends(get_config_service),
) -> dict:
    """Get recognition statistics."""
    from sqlalchemy import select, func, and_

    async with async_session_maker() as session:
        # Base query for filtering
        base_filters = []
        if app_key:
            base_filters.append(IntentRecognitionLog.app_key == app_key)
        if start_time:
            base_filters.append(IntentRecognitionLog.created_at >= start_time)
        if end_time:
            base_filters.append(IntentRecognitionLog.created_at <= end_time)
        
        # Total count
        total_query = select(func.count(IntentRecognitionLog.id))
        if base_filters:
            total_query = total_query.where(and_(*base_filters))
        total_result = await session.execute(total_query)
        total_count = total_result.scalar() or 0
        
        # Success count
        success_query = select(func.count(IntentRecognitionLog.id))
        success_filters = base_filters + [IntentRecognitionLog.is_success == True]
        success_query = success_query.where(and_(*success_filters))
        success_result = await session.execute(success_query)
        success_count = success_result.scalar() or 0
        
        # Failure count
        failure_count = total_count - success_count
        
        # Average processing time (for successful requests)
        time_query = select(func.avg(IntentRecognitionLog.processing_time_ms))
        time_filters = base_filters + [IntentRecognitionLog.is_success == True, IntentRecognitionLog.processing_time_ms.isnot(None)]
        time_query = time_query.where(and_(*time_filters))
        time_result = await session.execute(time_query)
        avg_time = time_result.scalar() or 0
        
        # Top intents
        intent_query = select(
            IntentRecognitionLog.recognized_intent,
            func.count(IntentRecognitionLog.id).label('count')
        )
        intent_filters = base_filters + [IntentRecognitionLog.is_success == True, IntentRecognitionLog.recognized_intent.isnot(None)]
        intent_query = intent_query.where(and_(*intent_filters))
        intent_query = intent_query.group_by(IntentRecognitionLog.recognized_intent)
        intent_query = intent_query.order_by(func.count(IntentRecognitionLog.id).desc())
        intent_query = intent_query.limit(10)
        intent_result = await session.execute(intent_query)
        top_intents = [{
            "intent": row[0],
            "count": row[1]
        } for row in intent_result.all()]
    
    return {
        "total_count": total_count,
        "success_count": success_count,
        "failure_count": failure_count,
        "success_rate": (success_count / total_count * 100) if total_count > 0 else 0,
        "failure_rate": (failure_count / total_count * 100) if total_count > 0 else 0,
        "average_processing_time_ms": avg_time,
        "top_intents": top_intents
    }
