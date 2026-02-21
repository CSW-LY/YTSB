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
from app.models.database import Application, IntentCategory, IntentRule, IntentRecognitionLog
from app.services.config_service import ConfigService
from app.services.recognizer import RecognizerChain
from app.db import async_session_maker, dispose_engine
from sqlalchemy import select, func

# Ensure consistent logging format
if not logging.getLogger().handlers:
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] [%(module)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
logger = logging.getLogger(__name__)

settings = get_settings()

set_session_maker(async_session_maker)

# Startup status tracking
startup_status = {
    "status": "initializing",
    "phase": "starting",
    "start_time": None,
    "current_phase": "initializing",
    "phases": [],
    "is_complete": False
}

async def save_log_async(log_data: dict) -> None:
    """Save log entry asynchronously."""
    log_entry = IntentRecognitionLog(**log_data)
    async_log_service = get_async_log_service()
    await async_log_service.enqueue_log(log_entry)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    import time
    total_start_time = time.time()
    
    # 初始化启动状态
    global startup_status
    startup_status = {
        "status": "initializing",
        "phase": "starting",
        "start_time": total_start_time,
        "current_phase": "initializing",
        "phases": [],
        "is_complete": False
    }
    
    logger.info(f"=== [START] Starting {settings.app_name} v{settings.app_version} ===")
    
    # 启动异步日志服务
    startup_status["current_phase"] = "initializing_log_service"
    startup_status["phases"].append({"phase": "initializing_log_service", "status": "starting", "timestamp": time.time()})
    logger.info("=== [START] Initializing async log service ===")
    log_start_time = time.time()
    async_log_service = get_async_log_service()
    await async_log_service.start()
    log_end_time = time.time()
    log_duration = (log_end_time - log_start_time) * 1000
    startup_status["phases"].append({"phase": "initializing_log_service", "status": "completed", "timestamp": log_end_time, "duration": log_duration})
    logger.info(f"=== [END] Async log service initialized (Duration: {log_duration:.2f}ms) ===")
    
    # 连接缓存管理器
    startup_status["current_phase"] = "connecting_cache"
    startup_status["phases"].append({"phase": "connecting_cache", "status": "starting", "timestamp": time.time()})
    logger.info("=== [START] Connecting cache manager ===")
    cache_start_time = time.time()
    await cache_manager.connect()
    cache_end_time = time.time()
    cache_duration = (cache_end_time - cache_start_time) * 1000
    startup_status["phases"].append({"phase": "connecting_cache", "status": "completed", "timestamp": cache_end_time, "duration": cache_duration})
    logger.info(f"=== [END] Cache manager connected (Duration: {cache_duration:.2f}ms) ===")
    
    # Preload models for better performance
    try:
        startup_status["current_phase"] = "preloading_models"
        startup_status["phases"].append({"phase": "preloading_models", "status": "starting", "timestamp": time.time()})
        logger.info("=== [START] Preloading models ===")
        model_start_time = time.time()
        
        logger.info("Initializing recognizer chain...")
        startup_status["current_phase"] = "initializing_recognizer"
        recognizer = await get_recognizer_chain()
        
        # Pre-build intent embeddings for semantic matching
        from app.models.database import IntentCategory, IntentRule
        from sqlalchemy import select
        async with async_session_maker() as session:
            # Get all active categories and rules
            startup_status["current_phase"] = "loading_categories"
            logger.info("Loading active categories...")
            categories_start_time = time.time()
            result = await session.execute(
                select(IntentCategory).where(IntentCategory.is_active == True)
            )
            categories = result.scalars().all()
            categories_end_time = time.time()
            categories_duration = (categories_end_time - categories_start_time) * 1000
            logger.info(f"Loaded {len(categories)} active categories (Duration: {categories_duration:.2f}ms)")
            
            startup_status["current_phase"] = "loading_rules"
            logger.info("Loading active rules...")
            rules_start_time = time.time()
            result = await session.execute(
                select(IntentRule).where(IntentRule.is_active == True)
            )
            rules = result.scalars().all()
            rules_end_time = time.time()
            rules_duration = (rules_end_time - rules_start_time) * 1000
            logger.info(f"Loaded {len(rules)} active rules (Duration: {rules_duration:.2f}ms)")
            
            # Build embeddings for semantic recognizer
            startup_status["current_phase"] = "building_embeddings"
            logger.info("Checking recognizers...")
            for r in recognizer.recognizers:
                logger.info(f"Found recognizer: {r.recognizer_type}")
                if r.recognizer_type == "semantic":
                    logger.info("Building embeddings for semantic recognizer...")
                    embedding_start_time = time.time()
                    await r._build_intent_embeddings(categories, rules)
                    embedding_end_time = time.time()
                    embedding_duration = (embedding_end_time - embedding_start_time) * 1000
                    logger.info(f"Built embeddings for {len(r._intent_embeddings)} intents (Duration: {embedding_duration:.2f}ms)")
                    break
        
        # Check LLM connection status
        if settings.enable_llm_fallback:
            startup_status["current_phase"] = "checking_llm"
            startup_status["phases"].append({"phase": "checking_llm", "status": "starting", "timestamp": time.time()})
            logger.info("=== [START] Checking LLM connection ===")
            llm_start_time = time.time()
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
                        test_start_time = time.time()
                        response = await llm_recognizer._call_llm(test_prompt)
                        test_end_time = time.time()
                        test_duration = (test_end_time - test_start_time) * 1000
                        if response:
                            logger.info(f"LLM connection test successful (Duration: {test_duration:.2f}ms)")
                        else:
                            logger.warning(f"LLM connection test returned no response (Duration: {test_duration:.2f}ms)")
                    except Exception as e:
                        logger.warning(f"LLM connection test failed: {e}")
                else:
                    logger.warning("LLM HTTP client not initialized")
            else:
                logger.info("LLM recognizer disabled or not configured")
            
            llm_end_time = time.time()
            llm_duration = (llm_end_time - llm_start_time) * 1000
            startup_status["phases"].append({"phase": "checking_llm", "status": "completed", "timestamp": llm_end_time, "duration": llm_duration})
            logger.info(f"=== [END] LLM connection check (Duration: {llm_duration:.2f}ms) ===")
        
        model_end_time = time.time()
        model_duration = (model_end_time - model_start_time) * 1000
        startup_status["phases"].append({"phase": "preloading_models", "status": "completed", "timestamp": model_end_time, "duration": model_duration})
        logger.info(f"=== [END] Models preloaded successfully (Total Duration: {model_duration:.2f}ms) ===")
    except Exception as e:
        logger.error(f"Failed to preload models: {e}")
        import traceback
        traceback.print_exc()
        logger.info("Models will load on first request")
        startup_status["phases"].append({"phase": "preloading_models", "status": "failed", "timestamp": time.time(), "error": str(e)})
    
    total_end_time = time.time()
    total_duration = (total_end_time - total_start_time) * 1000
    
    # 更新启动状态为完成
    startup_status["status"] = "completed"
    startup_status["phase"] = "started"
    startup_status["current_phase"] = "completed"
    startup_status["is_complete"] = True
    startup_status["total_duration"] = total_duration
    startup_status["end_time"] = total_end_time
    
    logger.info(f"=== [END] Service started successfully (Total Startup Time: {total_duration:.2f}ms) ===")
    
    yield
    
    # Shutdown
    logger.info("=== [START] Shutting down service ===")
    shutdown_start_time = time.time()
    
    async_log_service = get_async_log_service()
    await async_log_service.stop()
    await cache_manager.disconnect()
    await dispose_engine()
    
    shutdown_end_time = time.time()
    shutdown_duration = (shutdown_end_time - shutdown_start_time) * 1000
    logger.info(f"=== [END] Service stopped (Shutdown Time: {shutdown_duration:.2f}ms) ===")

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

    @app.get("/ready", response_model=ReadyResponse)
    async def ready_check():
        """Readiness check endpoint."""
        # Check database
        from sqlalchemy import text
        database_connected = False
        try:
            async with async_session_maker() as session:
                await session.execute(text("SELECT 1"))
                database_connected = True
        except Exception:
            pass

        # Check cache
        cache_connected = cache_manager._pool is not None

        # Check if model is loaded
        model_loaded = False
        try:
            from app.ml.embedding import get_embedding_model
            embedding_model = get_embedding_model()
            model_loaded = embedding_model.is_loaded
        except Exception:
            pass

        ready = database_connected

        return ReadyResponse(
            ready=ready,
            is_model_loaded=model_loaded,
            database_connected=database_connected,
            cache_connected=cache_connected,
        )

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

    @app.get("/api/ui/startup/status")
    async def get_startup_status():
        """Get startup status information."""
        import time
        current_time = time.time()
        
        # Calculate elapsed time if startup is in progress
        if not startup_status.get("is_complete") and startup_status.get("start_time"):
            elapsed_time = (current_time - startup_status["start_time"]) * 1000
            startup_status["elapsed_time"] = elapsed_time
        
        # Add current timestamp for reference
        response = startup_status.copy()
        response["timestamp"] = current_time
        
        return response

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
            total_apps = await session.execute(select(Application))

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
            # Refresh the rule to get the updated timestamp from database trigger
            await session.refresh(rule)
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
                    description=data.get("description"),
                    enable_keyword=data.get("enable_keyword", True),
                    enable_regex=data.get("enable_regex", True),
                    enable_semantic=data.get("enable_semantic", True),
                    enable_llm_fallback=data.get("enable_llm_fallback", False),
                    enable_cache=data.get("enable_cache", True),
                    fallback_intent_code=data.get("fallback_intent_code"),
                    confidence_threshold=data.get("confidence_threshold", 0.7)
                )
                await session.commit()
                await session.refresh(app)
                return {
                    "id": app.id,
                    "app_key": app.app_key,
                    "name": app.name,
                    "description": app.description,
                    "is_active": app.is_active,
                    "enable_keyword": app.enable_keyword,
                    "enable_regex": app.enable_regex,
                    "enable_semantic": app.enable_semantic,
                    "enable_llm_fallback": app.enable_llm_fallback,
                    "enable_cache": app.enable_cache,
                    "fallback_intent_code": app.fallback_intent_code,
                    "confidence_threshold": app.confidence_threshold,
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
                        "enable_keyword": app.enable_keyword,
                        "enable_regex": app.enable_regex,
                        "enable_semantic": app.enable_semantic,
                        "enable_llm_fallback": app.enable_llm_fallback,
                        "enable_cache": app.enable_cache,
                        "fallback_intent_code": app.fallback_intent_code,
                        "confidence_threshold": app.confidence_threshold,
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

    @app.get("/api/ui/applications/{application_id}")
    async def get_application(application_id: int):
        from fastapi import HTTPException
        async with async_session_maker() as session:
            result = await session.execute(
                select(Application).where(Application.id == application_id)
            )
            app = result.scalar_one_or_none()
            if not app:
                raise HTTPException(status_code=404, detail="Application not found")

            return {
                "id": app.id,
                "app_key": app.app_key,
                "name": app.name,
                "description": app.description,
                "is_active": app.is_active,
                "enable_keyword": app.enable_keyword,
                "enable_regex": app.enable_regex,
                "enable_semantic": app.enable_semantic,
                "enable_llm_fallback": app.enable_llm_fallback,
                "enable_cache": app.enable_cache,
                "fallback_intent_code": app.fallback_intent_code,
                "confidence_threshold": app.confidence_threshold,
                "created_at": app.created_at,
                "updated_at": app.updated_at
            }

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
            if "enable_keyword" in data:
                app.enable_keyword = data["enable_keyword"]
            if "enable_regex" in data:
                app.enable_regex = data["enable_regex"]
            if "enable_semantic" in data:
                app.enable_semantic = data["enable_semantic"]
            if "enable_llm_fallback" in data:
                app.enable_llm_fallback = data["enable_llm_fallback"]
            if "enable_cache" in data:
                app.enable_cache = data["enable_cache"]
            if "fallback_intent_code" in data:
                app.fallback_intent_code = data["fallback_intent_code"]
            if "confidence_threshold" in data:
                app.confidence_threshold = data["confidence_threshold"]

            await session.commit()
            await session.refresh(app)

            return {
                "id": app.id,
                "app_key": app.app_key,
                "name": app.name,
                "description": app.description,
                "is_active": app.is_active,
                "enable_keyword": app.enable_keyword,
                "enable_regex": app.enable_regex,
                "enable_semantic": app.enable_semantic,
                "enable_llm_fallback": app.enable_llm_fallback,
                "enable_cache": app.enable_cache,
                "fallback_intent_code": app.fallback_intent_code,
                "confidence_threshold": app.confidence_threshold,
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
                async with async_session_maker() as session:
                    config_service = ConfigService(session)
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
                        "processing_time_ms": (perf_counter() - start_time) * 1000,
                        "is_success": True,
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
                    "processing_time_ms": (perf_counter() - start_time) * 1000,
                    "is_success": True,
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
