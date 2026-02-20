"""FastAPI app with web UI."""

import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional, List
from datetime import datetime, timedelta

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from app.api.v1 import admin_router, intent_router
from app.core import get_settings, cache_manager, get_async_log_service, get_recognizer_chain
from app.core.log_service import set_session_maker
from app.models import HealthResponse, ReadyResponse
from app.models.database import Application, IntentCategory, IntentRule, AppIntent, IntentRecognitionLog
from app.services.config_service import ConfigService
from app.services.recognizer import RecognizerChain
from app.db import async_session_maker, dispose_engine
from sqlalchemy import select, func

logger = logging.getLogger(__name__)

settings = get_settings()

set_session_maker(async_session_maker)

async def save_log_async(log_data: dict) -> None:
    """Save log entry asynchronously."""
    log_entry = IntentRecognitionLog(**log_data)
    async_log_service = get_async_log_service()
    await async_log_service.enqueue_log(log_entry)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")
    async_log_service = get_async_log_service()
    await async_log_service.start()
    await cache_manager.connect()
    logger.info(f"Cache manager connected")
    
    # Preload models for better performance
    try:
        logger.info("=== Preloading models... ===")
        recognizer = await get_recognizer_chain()
        
        # Pre-build intent embeddings for semantic matching
        from app.models.database import IntentCategory, IntentRule
        from sqlalchemy import select
        async with async_session_maker() as session:
            # Get all active categories and rules
            result = await session.execute(
                select(IntentCategory).where(IntentCategory.is_active == True)
            )
            categories = result.scalars().all()
            logger.info(f"Loaded {len(categories)} active categories")
            
            result = await session.execute(
                select(IntentRule).where(IntentRule.is_active == True)
            )
            rules = result.scalars().all()
            logger.info(f"Loaded {len(rules)} active rules")
            
            # Build embeddings for semantic recognizer
            for r in recognizer.recognizers:
                logger.info(f"Checking recognizer: {r.recognizer_type}")
                if r.recognizer_type == "semantic":
                    logger.info(f"Building embeddings for semantic recognizer...")
                    await r._build_intent_embeddings(categories, rules)
                    logger.info(f"Built embeddings for {len(r._intent_embeddings)} intents")
                    break
        
        # Check LLM connection status
        if settings.enable_llm_fallback:
            logger.info("=== Checking LLM connection... ===")
            from app.services.recognizer import LLMRecognizer
            llm_recognizer = LLMRecognizer()
            await llm_recognizer.initialize()
            
            if llm_recognizer.enabled:
                logger.info("LLM recognizer enabled, testing connection...")
                # 尝试简单的连接测试
                if llm_recognizer._http_client:
                    try:
                        # 构建一个简单的测试提示
                        test_prompt = "Test connection"
                        # 尝试调用 LLM API
                        response = await llm_recognizer._call_llm(test_prompt)
                        if response:
                            logger.info("LLM connection test successful")
                        else:
                            logger.warning("LLM connection test returned no response")
                    except Exception as e:
                        logger.warning(f"LLM connection test failed: {e}")
                else:
                    logger.warning("LLM HTTP client not initialized")
            else:
                logger.info("LLM recognizer disabled or not configured")
        
        logger.info("=== Models preloaded successfully ===")
    except Exception as e:
        logger.warning(f"Failed to preload models: {e}")
        import traceback
        traceback.print_exc()
        logger.info("Models will load on first request")
    
    logger.info("Service started")
    yield
    logger.info("Shutting down...")
    async_log_service = get_async_log_service()
    await async_log_service.stop()
    await cache_manager.disconnect()
    await dispose_engine()
    logger.info("Service stopped")

def create_app():
    """Create and configure FastAPI application."""
    app = FastAPI(title=settings.app_name, version=settings.app_version, description="Intent Recognition Service", lifespan=lifespan)
    app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins, allow_credentials=settings.cors_allow_credentials, allow_methods=["*"], allow_headers=["*"])
    app.include_router(intent_router, prefix=settings.api_prefix)
    app.include_router(admin_router, prefix=settings.api_prefix)
    static_dir = Path(__file__).parent / "static"
    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    @app.get("/", response_class=HTMLResponse)
    async def root():
        from fastapi.responses import HTMLResponse
        static_file = Path(__file__).parent / "static" / "index.html"
        if static_file.exists():
            return HTMLResponse(content=static_file.read_text(encoding="utf-8"))
        return HTMLResponse(content="<h1>Intent Recognition Service</h1><p>Web UI is running at <a href='/static/'>/static/</a></p>")

    @app.get("/health")
    async def health_check():
        return HealthResponse(status="ok")

    @app.get("/ready")
    async def ready_check():
        return ReadyResponse(status="ready")

    @app.get("/api/ui/config")
    async def get_ui_config():
        return {
            "app_name": settings.app_name,
            "app_version": settings.app_version,
            "model_type": settings.model_type,
            "enable_semantic_matching": settings.enable_semantic_matching,
            "semantic_similarity_threshold": settings.semantic_similarity_threshold,
            "enable_llm_fallback": settings.enable_llm_fallback,
            "llm_model": settings.llm_model,
            "enable_cache": settings.enable_cache,
            "cache_ttl": settings.cache_ttl,
        }

    @app.get("/api/ui/llm/status")
    async def get_llm_status():
        """Get LLM connection status."""
        try:
            from app.services.recognizer import LLMRecognizer
            llm_recognizer = LLMRecognizer()
            await llm_recognizer.initialize()
            
            status = {
                "enabled": llm_recognizer.enabled,
                "configured": all([llm_recognizer._api_key, llm_recognizer._base_url, llm_recognizer._model]),
                "api_key": bool(llm_recognizer._api_key),
                "base_url": llm_recognizer._base_url,
                "model": llm_recognizer._model,
                "status": "unknown"
            }
            
            if not llm_recognizer.enabled:
                status["status"] = "disabled"
            elif not status["configured"]:
                status["status"] = "misconfigured"
            else:
                # Try connection test
                if llm_recognizer._http_client:
                    try:
                        test_prompt = "Test connection"
                        response = await llm_recognizer._call_llm(test_prompt)
                        if response:
                            status["status"] = "connected"
                        else:
                            status["status"] = "no_response"
                    except Exception as e:
                        status["status"] = "error"
                        status["error"] = str(e)
                else:
                    status["status"] = "not_initialized"
            
            return status
        except Exception as e:
            return {
                "enabled": False,
                "configured": False,
                "status": "error",
                "error": str(e)
            }

    @app.get("/api/ui/stats")
    async def get_stats():
        from app.core.cache import get_cache

        async with async_session_maker() as session:
            total_rules = await session.execute(
                select(IntentRule).where(IntentRule.is_active == True)
            )
            total_categories = await session.execute(
                select(IntentCategory).where(IntentCategory.is_active == True)
            )
            total_apps = await session.execute(select(AppIntent))

            result = await session.execute(
                select(IntentRecognitionLog).where(IntentRecognitionLog.created_at >= datetime.now() - timedelta(days=7))
            )
            logs = result.scalars().all()

            total_count = len(logs)
            success_count = sum(1 for log in logs if log.recognized_intent)
            failure_count = total_count - success_count
            success_rate = (success_count / total_count * 100) if total_count > 0 else 0.0
            failure_rate = (failure_count / total_count * 100) if total_count > 0 else 0.0

            avg_time = sum(log.processing_time_ms or 0 for log in logs) / total_count if total_count > 0 else 0.0

            intent_counts = {}
            for log in logs:
                if log.recognized_intent:
                    intent_counts[log.recognized_intent] = intent_counts.get(log.recognized_intent, 0) + 1
            top_intents = sorted(
                [{"intent": k, "count": v} for k, v in intent_counts.items()],
                key=lambda x: x["count"],
                reverse=True
            )[:10]

            if failure_count > 0:
                top_intents.append({"intent": "Unmatched/Failed", "count": failure_count})

            cache = get_cache()
            cache_connected = cache is not None

            return {
                "categories": {
                    "total": len(total_categories.scalars().all())
                },
                "rules": {
                    "total": len(total_rules.scalars().all())
                },
                "apps": {
                    "total": len(total_apps.scalars().all())
                },
                "cache": {
                    "connected": cache_connected
                },
                "recognition": {
                    "total_count": total_count,
                    "success_count": success_count,
                    "failure_count": failure_count,
                    "success_rate": success_rate,
                    "failure_rate": failure_rate,
                    "average_processing_time_ms": avg_time,
                    "top_intents": top_intents
                }
            }

    @app.get("/api/ui/categories")
    async def get_categories(
        application_id: Optional[int] = None,
        page: int = 1,
        page_size: int = 10
    ):
        async with async_session_maker() as session:
            query = select(IntentCategory)

            if application_id is not None:
                query = query.where(IntentCategory.application_id == application_id)

            # Get total count
            count_query = select(func.count()).select_from(IntentCategory)
            if application_id is not None:
                count_query = count_query.where(IntentCategory.application_id == application_id)
            total_result = await session.execute(count_query)
            total = total_result.scalar()

            # Get paginated results
            offset = (page - 1) * page_size
            result = await session.execute(
                query.offset(offset).limit(page_size)
            )
            categories = result.scalars().all()

            total_pages = (total + page_size - 1) // page_size if total > 0 else 0

            return {
                "items": categories,
                "total": total,
                "page": page,
                "page_size": page_size,
                "total_pages": total_pages
            }

    @app.get("/api/ui/categories/{category_id}")
    async def get_category(category_id: int):
        """Get a single category by ID."""
        from fastapi import HTTPException, status
        async with async_session_maker() as session:
            result = await session.execute(
                select(IntentCategory).where(IntentCategory.id == category_id)
            )
            category = result.scalar_one_or_none()
            if not category:
                raise HTTPException(status_code=404, detail="Category not found")
            return category

    @app.get("/api/ui/apps")
    async def get_apps():
        async with async_session_maker() as session:
            result = await session.execute(select(AppIntent))
            apps = result.scalars().all()
            return {
                "items": apps,
                "total": len(apps)
            }

    @app.get("/api/ui/logs")
    async def get_logs(page: int = 1, page_size: int = 20):
        async with async_session_maker() as session:
            offset = (page - 1) * page_size

            total_result = await session.execute(
                select(func.count()).select_from(IntentRecognitionLog)
            )
            total = total_result.scalar()

            result = await session.execute(
                select(IntentRecognitionLog).order_by(IntentRecognitionLog.created_at.desc()).offset(offset).limit(page_size)
            )
            logs = result.scalars().all()

            total_pages = (total + page_size - 1) // page_size if total > 0 else 0

            return {
                "data": logs,
                "total": total,
                "page": page,
                "page_size": page_size,
                "total_pages": total_pages
            }

    @app.post("/api/ui/categories")
    async def create_category(data: dict):
        from fastapi import HTTPException, status
        async with async_session_maker() as session:
            try:
                svc = ConfigService(session)
                category = await svc.create_category(
                    application_id=data["application_id"],
                    code=data["code"],
                    name=data["name"],
                    description=data.get("description"),
                    priority=data.get("priority", 0)
                )
                await session.commit()
                await session.refresh(category)
                return category
            except Exception as e:
                raise HTTPException(status_code=400, detail=str(e))

    @app.put("/api/ui/categories/{category_id}")
    async def update_category(category_id: int, data: dict):
        async with async_session_maker() as session:
            result = await session.execute(
                select(IntentCategory).where(IntentCategory.id == category_id)
            )
            category = result.scalar_one_or_none()
            if not category:
                from fastapi import HTTPException, status
                raise HTTPException(status_code=404, detail="Category not found")
            for key, value in data.items():
                if hasattr(category, key):
                    setattr(category, key, value)
            await session.commit()
            return category

    @app.delete("/api/ui/categories/{category_id}")
    async def delete_category(category_id: int):
        async with async_session_maker() as session:
            result = await session.execute(
                select(IntentCategory).where(IntentCategory.id == category_id)
            )
            category = result.scalar_one_or_none()
            if not category:
                from fastapi import HTTPException, status
                raise HTTPException(status_code=404, detail="Category not found")
            await session.delete(category)
            await session.commit()

    @app.get("/api/ui/rules")
    async def get_rules(
        category_id: Optional[int] = None,
        rule_type: Optional[str] = None,
        is_active: Optional[bool] = None,
        page: int = 1,
        page_size: int = 10
    ):
        async with async_session_maker() as session:
            query = select(IntentRule)
            
            if category_id is not None:
                query = query.where(IntentRule.category_id == category_id)
            if rule_type is not None:
                query = query.where(IntentRule.rule_type == rule_type)
            if is_active is not None:
                query = query.where(IntentRule.is_active == is_active)
            
            total_query = select(func.count(IntentRule.id))
            if category_id is not None:
                total_query = total_query.where(IntentRule.category_id == category_id)
            if rule_type is not None:
                total_query = total_query.where(IntentRule.rule_type == rule_type)
            if is_active is not None:
                total_query = total_query.where(IntentRule.is_active == is_active)
            
            total_result = await session.execute(total_query)
            total = total_result.scalar() or 0
            
            offset = (page - 1) * page_size
            query = query.offset(offset).limit(page_size)
            
            result = await session.execute(query)
            rules = result.scalars().all()
            
            return {
                "items": rules,
                "total": total,
                "page": page,
                "page_size": page_size,
                "total_pages": (total + page_size - 1) // page_size
            }

    @app.post("/api/ui/rules")
    async def create_rule(data: dict):
        async with async_session_maker() as session:
            rule = IntentRule(**data)
            session.add(rule)
            await session.commit()
            await session.refresh(rule)
            return rule

    @app.get("/api/ui/rules/{rule_id}")
    async def get_rule(rule_id: int):
        """Get a single rule by ID."""
        from fastapi import HTTPException, status
        async with async_session_maker() as session:
            result = await session.execute(
                select(IntentRule).where(IntentRule.id == rule_id)
            )
            rule = result.scalar_one_or_none()
            if not rule:
                raise HTTPException(status_code=404, detail="Rule not found")
            # Return a dict instead of the model object to avoid serialization issues
            return {
                "id": rule.id,
                "category_id": rule.category_id,
                "rule_type": rule.rule_type,
                "content": rule.content,
                "weight": rule.weight,
                "rule_metadata": rule.rule_metadata,
                "is_active": rule.is_active,
                "created_at": rule.created_at,
                "updated_at": rule.updated_at
            }

    @app.put("/api/ui/rules/{rule_id}")
    async def update_rule(rule_id: int, data: dict):
        async with async_session_maker() as session:
            result = await session.execute(
                select(IntentRule).where(IntentRule.id == rule_id)
            )
            rule = result.scalar_one_or_none()
            if not rule:
                from fastapi import HTTPException, status
                raise HTTPException(status_code=404, detail="Rule not found")
            for key, value in data.items():
                if hasattr(rule, key):
                    setattr(rule, key, value)
            await session.commit()
            # Return a dict instead of the model object to avoid serialization issues
            return {
                "id": rule.id,
                "category_id": rule.category_id,
                "rule_type": rule.rule_type,
                "content": rule.content,
                "weight": rule.weight,
                "rule_metadata": rule.rule_metadata,
                "is_active": rule.is_active,
                "created_at": rule.created_at,
                "updated_at": rule.updated_at
            }

    @app.delete("/api/ui/rules/{rule_id}")
    async def delete_rule(rule_id: int):
        async with async_session_maker() as session:
            result = await session.execute(
                select(IntentRule).where(IntentRule.id == rule_id)
            )
            rule = result.scalar_one_or_none()
            if not rule:
                from fastapi import HTTPException, status
                raise HTTPException(status_code=404, detail="Rule not found")
            await session.delete(rule)
            await session.commit()

    @app.post("/api/ui/apps")
    async def create_app(data: dict):
        async with async_session_maker() as session:
            app = AppIntent(**data)
            session.add(app)
            await session.commit()
            await session.refresh(app)
            return app

    @app.get("/api/ui/apps/{app_id}")
    async def get_app(app_id: int):
        async with async_session_maker() as session:
            result = await session.execute(
                select(AppIntent).where(AppIntent.id == app_id)
            )
            app = result.scalar_one_or_none()
            if not app:
                from fastapi import HTTPException, status
                raise HTTPException(status_code=404, detail="App not found")
            return app

    @app.put("/api/ui/apps/{app_id}")
    async def update_app(app_id: int, data: dict):
        async with async_session_maker() as session:
            result = await session.execute(
                select(AppIntent).where(AppIntent.id == app_id)
            )
            app = result.scalar_one_or_none()
            if not app:
                from fastapi import HTTPException, status
                raise HTTPException(status_code=404, detail="App not found")
            for key, value in data.items():
                if hasattr(app, key):
                    setattr(app, key, value)
            await session.commit()
            return app

    @app.delete("/api/ui/apps/{app_id}")
    async def delete_app(app_id: int):
        async with async_session_maker() as session:
            result = await session.execute(
                select(AppIntent).where(AppIntent.id == app_id)
            )
            app = result.scalar_one_or_none()
            if not app:
                from fastapi import HTTPException, status
                raise HTTPException(status_code=404, detail="App not found")
            await session.delete(app)
            await session.commit()

    # Application management APIs
    @app.post("/api/ui/applications")
    async def create_application(data: dict):
        from fastapi import HTTPException
        async with async_session_maker() as session:
            try:
                svc = ConfigService(session)
                app = await svc.create_application(
                    app_key=data["app_key"],
                    name=data["name"],
                    description=data.get("description")
                )
                await session.commit()
                await session.refresh(app)
                return {
                    "id": app.id,
                    "app_key": app.app_key,
                    "name": app.name,
                    "description": app.description,
                    "is_active": app.is_active,
                    "created_at": app.created_at,
                    "updated_at": app.updated_at
                }
            except Exception as e:
                from fastapi import status
                raise HTTPException(status_code=400, detail=str(e))

    @app.get("/api/ui/applications")
    async def list_applications(
        is_active: Optional[bool] = None,
        page: int = 1,
        page_size: int = 10
    ):
        async with async_session_maker() as session:
            svc = ConfigService(session)
            applications = await svc.list_applications(
                is_active=is_active,
                limit=page_size,
                offset=(page - 1) * page_size,
            )

            total_query = select(func.count(Application.id))
            if is_active is not None:
                total_query = total_query.where(Application.is_active == is_active)
            total_result = await session.execute(total_query)
            total = total_result.scalar()

            return {
                "items": [
                    {
                        "id": app.id,
                        "app_key": app.app_key,
                        "name": app.name,
                        "description": app.description,
                        "is_active": app.is_active,
                        "created_at": app.created_at,
                        "updated_at": app.updated_at
                    }
                    for app in applications
                ],
                "total": total,
                "page": page,
                "page_size": page_size
            }

    @app.delete("/api/ui/applications/{application_id}")
    async def delete_application(application_id: int):
        from fastapi import HTTPException
        async with async_session_maker() as session:
            svc = ConfigService(session)
            success = await svc.delete_application(application_id)
            if not success:
                raise HTTPException(status_code=404, detail="Application not found")
            await session.commit()
            return {"success": True}

    @app.put("/api/ui/applications/{application_id}")
    async def update_application(application_id: int, data: dict):
        from fastapi import HTTPException
        async with async_session_maker() as session:
            result = await session.execute(
                select(Application).where(Application.id == application_id)
            )
            app = result.scalar_one_or_none()
            if not app:
                raise HTTPException(status_code=404, detail="Application not found")
            
            if "name" in data:
                app.name = data["name"]
            if "description" in data:
                app.description = data["description"]
            if "is_active" in data:
                app.is_active = data["is_active"]
            
            await session.commit()
            await session.refresh(app)
            
            return {
                "id": app.id,
                "app_key": app.app_key,
                "name": app.name,
                "description": app.description,
                "is_active": app.is_active,
                "created_at": app.created_at,
                "updated_at": app.updated_at
            }

    @app.post("/api/ui/applications/{application_id}/categories")
    async def create_application_category(application_id: int, data: dict):
        from fastapi import HTTPException
        async with async_session_maker() as session:
            try:
                svc = ConfigService(session)
                category = await svc.create_category(
                    application_id=application_id,
                    code=data["code"],
                    name=data["name"],
                    description=data.get("description"),
                    priority=data.get("priority", 0)
                )
                await session.commit()
                await session.refresh(category)
                return {
                    "id": category.id,
                    "application_id": category.application_id,
                    "code": category.code,
                    "name": category.name,
                    "description": category.description,
                    "priority": category.priority,
                    "is_active": category.is_active,
                    "created_at": category.created_at,
                    "updated_at": category.updated_at
                }
            except Exception as e:
                from fastapi import status
                raise HTTPException(status_code=400, detail=str(e))

    @app.get("/api/ui/applications/{application_id}/categories")
    async def list_application_categories(
        application_id: int,
        is_active: Optional[bool] = None
    ):
        async with async_session_maker() as session:
            svc = ConfigService(session)
            categories = await svc.get_categories_by_application(
                application_id,
                is_active=is_active
            )
            return [
                {
                    "id": cat.id,
                    "application_id": cat.application_id,
                    "code": cat.code,
                    "name": cat.name,
                    "description": cat.description,
                    "priority": cat.priority,
                    "is_active": cat.is_active,
                    "created_at": cat.created_at,
                    "updated_at": cat.updated_at
                }
                for cat in categories
            ]

    class UITestRequest(BaseModel):
        text: str
        app_key: Optional[str] = None

    class RecognitionStep(BaseModel):
        recognizer: str
        status: str
        time_ms: float = 0.0
        confidence: float = 0.0
        intent: Optional[str] = None
        error: Optional[str] = None
        reason: Optional[str] = None

    class UITestResponse(BaseModel):
        intent: Optional[str] = None
        confidence: float = 0.0
        matchedRules: list = []
        recognizer_type: Optional[str] = None
        processingTimeMs: float = 0.0
        message: str = ""
        recognitionChain: List[RecognitionStep] = []

    @app.post("/api/ui/test", response_model=UITestResponse)
    async def test_ui(request: UITestRequest, recognizer: RecognizerChain = Depends(get_recognizer_chain)):
        """Test intent recognition via UI."""
        from fastapi.responses import JSONResponse
        from time import perf_counter
        from app.models.schema import MatchedRule
        from app.api.v1.intent import try_llm_fallback

        start_time = perf_counter()
        log_data = None

        try:
            if not request.app_key or not request.app_key.strip():
                return UITestResponse(
                    intent=None,
                    confidence=0.0,
                    matchedRules=[],
                    recognizer_type=None,
                    processingTimeMs=0.0,
                    message="Please select an App Key"
                )

            if request.app_key:
                config_service = ConfigService(async_session_maker)
                context = await config_service.get_app_intent_context(request.app_key)

                if not context:
                    return UITestResponse(
                        intent=None,
                        confidence=0.0,
                        matchedRules=[],
                        recognizer_type=None,
                        processingTimeMs=0.0,
                        message=f"No configuration found for app: {request.app_key}"
                    )

                result = await recognizer.recognize(
                    request.text,
                    context["categories"],
                    context["rules"]
                )

                # Try LLM fallback if no match found
                if result is None:
                    logger.info("No match found in UI test, attempting LLM fallback")
                    from app.core.config import get_settings
                    settings = get_settings()
                    
                    if settings.enable_llm_fallback:
                        # Get app config
                        app_config = context.get("app_config")
                        categories = context.get("categories", [])
                        
                        # Try LLM fallback
                        llm_result = await try_llm_fallback(
                            text=request.text,
                            categories=categories,
                            app_config=app_config,
                            previous_chain=getattr(recognizer, 'last_chain', [])
                        )
                        
                        if llm_result:
                            result = llm_result
                            logger.info(f"LLM fallback used in UI test: {result.intent}")

                if result is None:
                    return UITestResponse(
                        intent=None,
                        confidence=0.0,
                        matchedRules=[],
                        recognizer_type=None,
                        processingTimeMs=0.0,
                        message="No intent matched. Please check your rules and categories configuration."
                    )

                log_data = {
                    "app_key": request.app_key,
                    "input_text": request.text,
                    "recognized_intent": result.intent,
                    "confidence": result.confidence,
                    "matched_rules": [
                        MatchedRule(
                            id=r.id,
                            rule_type=r.rule_type,
                            content=r.content,
                            weight=r.weight
                        )
                        for r in result.matched_rules
                    ],
                    "execution_time_ms": (perf_counter() - start_time) * 1000,
                    "recognizer_type": result.recognizer_type,
                }
            else:
                async with async_session_maker() as session:
                    all_categories_result = await session.execute(
                        select(IntentCategory).where(IntentCategory.is_active == True)
                    )
                    all_rules_result = await session.execute(
                        select(IntentRule).where(IntentRule.is_active == True)
                    )
                    all_categories = all_categories_result.scalars().all()
                    all_rules = all_rules_result.scalars().all()

                result = await recognizer.recognize(request.text, all_categories, all_rules)

                # Try LLM fallback if no match found
                if result is None:
                    logger.info("No match found in UI test, attempting LLM fallback")
                    from app.core.config import get_settings
                    settings = get_settings()
                    
                    if settings.enable_llm_fallback:
                        # Try LLM fallback
                        llm_result = await try_llm_fallback(
                            text=request.text,
                            categories=all_categories,
                            app_config=None,
                            previous_chain=getattr(recognizer, 'last_chain', [])
                        )
                        
                        if llm_result:
                            result = llm_result
                            logger.info(f"LLM fallback used in UI test: {result.intent}")

                if result is None:
                    return UITestResponse(
                        intent=None,
                        confidence=0.0,
                        matchedRules=[],
                        recognizer_type=None,
                        processingTimeMs=0.0,
                        message="No intent matched. Please check your rules and categories configuration."
                    )

                log_data = {
                    "app_key": "ui_test",
                    "input_text": request.text,
                    "recognized_intent": result.intent,
                    "confidence": result.confidence,
                    "matched_rules": [
                        MatchedRule(
                            id=r.id,
                            rule_type=r.rule_type,
                            content=r.content,
                            weight=r.weight
                        )
                        for r in result.matched_rules
                    ],
                    "execution_time_ms": (perf_counter() - start_time) * 1000,
                    "recognizer_type": result.recognizer_type,
                }

            if log_data:
                await save_log_async(log_data)

            execution_time = perf_counter() - start_time

            recognition_chain_steps = []
            for step in getattr(result, 'recognition_chain', []):
                recognition_chain_steps.append(RecognitionStep(
                    recognizer=step.get("recognizer", ""),
                    status=step.get("status", "unknown"),
                    time_ms=step.get("time_ms", 0.0),
                    confidence=step.get("confidence", 0.0),
                    intent=step.get("intent"),
                    error=step.get("error"),
                    reason=step.get("reason")
                ))

            message = "Intent recognized successfully"
            if result.intent == "LLM无法匹配":
                message = "No intent matched, LLM fallback returned 'LLM无法匹配'"

            return UITestResponse(
                intent=result.intent,
                confidence=result.confidence,
                matchedRules=[
                    MatchedRule(
                        id=r.id,
                        rule_type=r.rule_type,
                        content=r.content,
                        weight=r.weight
                    )
                    for r in result.matched_rules
                ],
                recognizer_type=result.recognizer_type,
                processingTimeMs=execution_time * 1000,
                message=message,
                recognitionChain=recognition_chain_steps
            )
        except Exception as e:
            logger.error(f"Error in test endpoint: {e}")
            import traceback
            traceback.print_exc()
            return UITestResponse(
                intent=None,
                confidence=0.0,
                matchedRules=[],
                processingTimeMs=0.0,
                message=f"Error: {str(e)}"
            )

    return app

app = create_app()
