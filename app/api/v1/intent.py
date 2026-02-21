"""Intent recognition API endpoints."""

import json
import logging
import time
from typing import List, Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import get_async_log_service, get_recognizer_chain, get_recognizer_chain_for_app
from app.core.cache import CacheManager, generate_cache_key, get_cache
from app.core.config import get_settings
from app.core.security import verify_api_key
from app.db import async_session_maker
from app.models.database import Application, IntentCategory, IntentRecognitionLog
from app.models.schema import (
    BatchRecognizeRequest,
    BatchRecognizeResponse,
    MatchedRule,
    RecognitionFailureResponse,
    RecognizeRequest,
    RecognizeResponse,
)
from app.services.config_service import ConfigService
from app.services.recognizer import (
    IntentResult,
    LLMRecognizer,
    RecognizerChain,
)

logger = logging.getLogger(__name__)

settings = get_settings()

router = APIRouter(
    prefix="/intent",
    tags=["intent"],
)


async def save_log_async(log_data: dict) -> None:
    """Save log entry asynchronously."""
    async_log_service = get_async_log_service()
    log_entry = IntentRecognitionLog(**log_data)
    await async_log_service.enqueue_log(log_entry)


def build_success_response(
    result: IntentResult,
    processing_time_ms: float,
    fallback_used: bool = False,
    fallback_reason: Optional[str] = None,
) -> RecognizeResponse:
    """构建成功响应"""
    # Set success to False if LLM returned "LLM无法匹配"
    success = result.intent != "LLM无法匹配"
    
    return RecognizeResponse(
        intent=result.intent,
        confidence=result.confidence,
        entities=result.entities,
        matched_rules=[
            MatchedRule(
                id=rule.id,
                rule_type=rule.rule_type,
                content=rule.content,
                weight=rule.weight,
            )
            for rule in result.matched_rules
        ],
        cached=False,
        processing_time_ms=processing_time_ms,
        recognition_chain=getattr(result, 'recognition_chain', []),
        success=success,
        fallback_used=fallback_used,
        fallback_reason=fallback_reason,
        final_recognizer=result.recognizer_type,
        failure_reason="LLM无法匹配" if not success else None,
        failure_type="no_match" if not success else None,
    )


def build_failure_response(
    failure_type: str,
    failure_reason: str,
    recognition_chain: List,
    processing_time_ms: float,
    confidence: Optional[float] = None,
    intent: Optional[str] = None,
    matched_rules: List = None,
    threshold: Optional[float] = None,
) -> RecognizeResponse:
    """构建失败响应"""
    # 检查是否有LLM错误
    llm_error = None
    llm_error_reason = None
    for step in recognition_chain:
        if step.get("recognizer") == "llm_fallback" and step.get("status") == "error":
            llm_error = step.get("error")
            llm_error_reason = step.get("reason")
            break
    
    # 构建详细的失败原因
    detailed_reason = failure_reason
    if llm_error:
        detailed_reason += f" (LLM错误: {llm_error})"
    
    # 构建建议
    suggestion = get_failure_suggestion(failure_type, failure_reason)
    if llm_error:
        llm_suggestions = {
            "missing_api_key_or_url": "请检查LLM API密钥和基础URL配置",
            "api_connection_error": "请检查LLM API连接和网络状态",
            "unknown_error": "请检查LLM配置和日志",
        }
        llm_suggestion = llm_suggestions.get(llm_error_reason, "请检查LLM配置")
        if suggestion:
            suggestion += f"\nLLM建议: {llm_suggestion}"
        else:
            suggestion = f"LLM建议: {llm_suggestion}"
    
    return RecognizeResponse(
        success=False,
        intent=intent,
        confidence=confidence,
        failure_reason=detailed_reason,
        failure_type=failure_type,
        recognition_chain=recognition_chain,
        matched_rules=matched_rules or [],
        processing_time_ms=processing_time_ms,
        threshold=threshold,
        suggestion=suggestion,
        llm_error=llm_error,
        llm_error_reason=llm_error_reason,
        fallback_used=False,
        final_recognizer=None,
        entities={},
        cached=False
    )


def get_failure_suggestion(failure_type: str, failure_reason: str) -> Optional[str]:
    """根据失败类型提供建议"""
    suggestions = {
        "no_match": "建议：1) 添加更多规则 2) 启用LLM兜底 3) 配置fallback意图",
        "low_confidence": "建议：1) 降低置信度阈值 2) 优化规则权重 3) 启用LLM兜底",
        "system_error": "建议：检查系统日志，联系管理员",
        "config_missing": "建议：确保应用配置已正确设置",
    }
    return suggestions.get(failure_type)


async def try_llm_fallback(
    text: str,
    categories: List[IntentCategory],
    application: Application,
    previous_chain: List,
) -> Optional[IntentResult]:
    """
    尝试LLM兜底识别。

    Args:
        text: 输入文本
        categories: 意图分类列表
        application: 应用配置
        previous_chain: 之前的识别链路

    Returns:
        IntentResult 如果LLM识别成功，否则 None
    """
    start_time = time.time()
    
    try:
        llm_recognizer = LLMRecognizer()
        await llm_recognizer.initialize()

        if not llm_recognizer.enabled:
            logger.warning("LLM recognizer not enabled")
            previous_chain.append({
                "recognizer": "llm_fallback",
                "status": "skipped",
                "reason": "disabled",
                "time_ms": 0.0
            })
            return None

        # 检查LLM配置完整性
        if not all([llm_recognizer._api_key, llm_recognizer._base_url, llm_recognizer._model]):
            logger.warning("LLM recognizer incomplete configuration")
            previous_chain.append({
                "recognizer": "llm_fallback",
                "status": "error",
                "error": "LLM configuration incomplete",
                "reason": "missing_api_key_or_url",
                "time_ms": (time.time() - start_time) * 1000
            })
            return None

        result = await llm_recognizer.recognize(text, categories, [], None)
        processing_time_ms = (time.time() - start_time) * 1000

        if result:
            # Always include LLM result in recognition chain, even if it's "LLM无法匹配"
            llm_status = "success" if result.intent != "LLM无法匹配" else "no_match"
            
            result.recognition_chain = previous_chain + [{
                "recognizer": "llm_fallback",
                "status": llm_status,
                "intent": result.intent,
                "confidence": result.confidence,
                "time_ms": processing_time_ms
            }]
            
            if result.intent != "LLM无法匹配":
                logger.info(f"LLM fallback matched intent: {result.intent} (confidence: {result.confidence})")
            else:
                logger.info("LLM fallback returned 'LLM无法匹配'")
            
            return result

        previous_chain.append({
            "recognizer": "llm_fallback",
            "status": "error",
            "reason": "llm_no_result",
            "time_ms": processing_time_ms
        })
        return None

    except httpx.HTTPError as e:
        error_msg = f"LLM API connection error: {str(e)}"
        logger.error(error_msg)
        previous_chain.append({
            "recognizer": "llm_fallback",
            "status": "error",
            "error": error_msg,
            "reason": "api_connection_error",
            "time_ms": (time.time() - start_time) * 1000
        })
        return None
    except Exception as e:
        error_msg = f"LLM fallback error: {str(e)}"
        logger.error(error_msg)
        previous_chain.append({
            "recognizer": "llm_fallback",
            "status": "error",
            "error": error_msg,
            "reason": "unknown_error",
            "time_ms": (time.time() - start_time) * 1000
        })
        return None


# ============================================================================
# Dependencies
# ============================================================================

async def get_config_service(
    db: AsyncSession = Depends(lambda: None),
) -> ConfigService:
    """Get config service instance."""

    async with async_session_maker() as session:
        yield ConfigService(session)


# ============================================================================
# API Endpoints
# ============================================================================

@router.post("/recognize", response_model=RecognizeResponse)
async def recognize_intent(
    request: RecognizeRequest,
    config_service: ConfigService = Depends(get_config_service),
    cache: CacheManager = Depends(get_cache),
    api_key_info: Optional[dict] = Depends(verify_api_key),
):
    """
    识别用户输入的意图。

    使用多种策略按顺序识别：
    1. 关键词匹配（最快）
    2. 正则匹配
    3. 语义相似度
    4. LLM分类（兜底）

    即使识别失败，也会返回完整的识别链路和失败原因。
    """
    import time
    start_time = time.time()
    log_data = {
        "app_key": request.app_key,
        "api_key_id": api_key_info.get('key_id') if api_key_info else None,
        "input_text": request.text,
        "is_success": True,
        "error_message": None,
    }

    # Check cache first
    if settings.enable_cache:
        cache_key = generate_cache_key(request.app_key, request.text, request.context)
        cached_result = await cache.get(cache_key)

        if cached_result:
            logger.debug(f"Cache hit for app: {request.app_key}")
            # Log cache hit
            log_data["recognized_intent"] = cached_result["intent"]
            log_data["confidence"] = cached_result["confidence"]
            log_data["processing_time_ms"] = (time.time() - start_time) * 1000
            log_data["recognition_chain"] = json.dumps([{"recognizer": "cache", "status": "success", "time_ms": log_data["processing_time_ms"]}])
            await save_log_async(log_data)
            cached_response = RecognizeResponse(**cached_result)
            cached_response.success = True
            return cached_response

    # Get app configuration
    context_data = await config_service.get_app_intent_context(request.app_key)

    if not context_data:
        log_data["is_success"] = False
        log_data["error_message"] = f"App configuration not found: {request.app_key}"
        log_data["processing_time_ms"] = (time.time() - start_time) * 1000

        # Try LLM fallback even if app config not found
        if settings.enable_llm_fallback:
            logger.info("App config not found, attempting LLM fallback with default categories")

            # Get all active categories as fallback
            from app.models.database import IntentCategory
            from sqlalchemy import select
            async with async_session_maker() as session:
                result = await session.execute(
                    select(IntentCategory).where(IntentCategory.is_active == True)
                )
                categories = result.scalars().all()

            # Try LLM fallback
            if categories:
                from app.services.recognizer import LLMRecognizer
                llm_recognizer = LLMRecognizer()
                await llm_recognizer.initialize()

                if llm_recognizer.enabled:
                    try:
                        result = await try_llm_fallback(
                            llm_recognizer,
                            request.text,
                            categories,
                            [],
                            [],
                            start_time,
                            log_data.get("recognition_chain", [])
                        )

                        if result:
                            await save_log_async(log_data)
                            return response
                    except Exception as e:
                        logger.error(f"LLM fallback error: {e}")

        # If LLM fallback fails or not enabled, return failure
        await save_log_async(log_data)
        return build_failure_response(
            failure_type="config_missing",
            failure_reason=f"App configuration not found: {request.app_key}",
            recognition_chain=[],
            processing_time_ms=(time.time() - start_time) * 1000
        )

    application = context_data["application"]
    categories = context_data["categories"]
    rules = context_data["rules"]

    if not categories:
        log_data["is_success"] = False
        log_data["error_message"] = f"No active intents configured for app: {request.app_key}"
        log_data["processing_time_ms"] = (time.time() - start_time) * 1000
        await save_log_async(log_data)
        return build_failure_response(
            failure_type="config_missing",
            failure_reason=f"No active intents configured for app: {request.app_key}",
            recognition_chain=[],
            processing_time_ms=(time.time() - start_time) * 1000
        )

    # Create recognizer chain based on application config
    recognizer = await get_recognizer_chain_for_app(application)

    # Run recognition
    result = None
    try:
        result = await recognizer.recognize(
            request.text,
            categories,
            rules,
            request.context,
        )
    except Exception as e:
        logger.error(f"Recognition error: {e}")
        log_data["is_success"] = False
        log_data["error_message"] = str(e)
        log_data["processing_time_ms"] = (time.time() - start_time) * 1000
        await save_log_async(log_data)
        return build_failure_response(
            failure_type="system_error",
            failure_reason=str(e),
            recognition_chain=[],
            processing_time_ms=(time.time() - start_time) * 1000
        )

    # Handle no match
    if not result:
        recognition_chain = getattr(recognizer, 'last_chain', [])

        # 尝试LLM兜底
        if application.enable_llm_fallback or settings.enable_llm_fallback:
            logger.info("No match found, attempting LLM fallback")
            llm_result = await try_llm_fallback(
                text=request.text,
                categories=categories,
                application=application,
                previous_chain=recognition_chain.copy()
            )

            if llm_result:
                # LLM兜底成功
                processing_time = (time.time() - start_time) * 1000
                response = build_success_response(
                    llm_result,
                    processing_time,
                    True,
                    "LLM fallback (no match from rule-based recognizers)"
                )
                
                log_data["recognized_intent"] = llm_result.intent
                log_data["confidence"] = llm_result.confidence
                log_data["processing_time_ms"] = processing_time
                log_data["recognition_chain"] = json.dumps(llm_result.recognition_chain)
                await save_log_async(log_data)
                
                # Cache result
                if settings.enable_cache and application.enable_cache:
                    cache_key = generate_cache_key(request.app_key, request.text, request.context)
                    await cache.set(cache_key, response.model_dump())

                return response

        # LLM兜底失败或未启用，尝试fallback_intent
        if application.fallback_intent_code:
            fallback_category = next(
                (c for c in categories if c.code == application.fallback_intent_code),
                None,
            )

            if fallback_category:
                processing_time = (time.time() - start_time) * 1000
                recognition_chain.append({
                    "recognizer": "fallback",
                    "status": "success",
                    "intent": fallback_category.code,
                    "confidence": 0.0,
                    "time_ms": 0.0
                })
                
                response = RecognizeResponse(
                    intent=fallback_category.code,
                    confidence=0.0,
                    matched_rules=[],
                    recognition_chain=recognition_chain,
                    processing_time_ms=processing_time,
                    success=True,
                    fallback_used=True,
                    fallback_reason="Fallback intent (no match from recognizers)",
                    final_recognizer="fallback"
                )
                
                log_data["recognized_intent"] = fallback_category.code
                log_data["confidence"] = 0.0
                log_data["processing_time_ms"] = processing_time
                log_data["recognition_chain"] = json.dumps(recognition_chain)
                await save_log_async(log_data)
                
                return response

        # 所有兜底都失败，返回失败响应
        log_data["is_success"] = False
        log_data["error_message"] = "No matching intent found and no fallback configured"
        log_data["processing_time_ms"] = (time.time() - start_time) * 1000
        await save_log_async(log_data)
        return build_failure_response(
            failure_type="no_match",
            failure_reason="No matching intent found and no fallback configured",
            recognition_chain=recognition_chain,
            processing_time_ms=(time.time() - start_time) * 1000
        )

    # Check confidence threshold
    threshold = application.confidence_threshold or settings.default_confidence_threshold
    if result.confidence < threshold:
        # 尝试LLM兜底
        if application.enable_llm_fallback:
            logger.info(
                f"Confidence {result.confidence:.2f} below threshold {threshold}, "
                f"attempting LLM fallback"
            )
            llm_result = await try_llm_fallback(
                text=request.text,
                categories=categories,
                application=application,
                previous_chain=result.recognition_chain.copy()
            )

            if llm_result:
                # LLM兜底成功
                processing_time = (time.time() - start_time) * 1000
                response = build_success_response(
                    llm_result,
                    processing_time,
                    True,
                    f"LLM fallback (original confidence {result.confidence:.2f} < {threshold})"
                )

                log_data["recognized_intent"] = llm_result.intent
                log_data["confidence"] = llm_result.confidence
                log_data["processing_time_ms"] = processing_time
                log_data["recognition_chain"] = json.dumps(llm_result.recognition_chain)
                await save_log_async(log_data)

                # Cache result
                if settings.enable_cache and application.enable_cache:
                    cache_key = generate_cache_key(request.app_key, request.text, request.context)
                    await cache.set(cache_key, response.model_dump())

                return response

        # LLM兜底失败或未启用，返回带链路的失败响应
        log_data["is_success"] = False
        log_data["error_message"] = f"Intent confidence {result.confidence:.2f} below threshold {threshold}"
        log_data["recognized_intent"] = result.intent
        log_data["confidence"] = result.confidence
        log_data["processing_time_ms"] = (time.time() - start_time) * 1000
        if hasattr(result, 'recognition_chain'):
            log_data["recognition_chain"] = json.dumps(result.recognition_chain)
        if hasattr(result, 'matched_rules'):
            log_data["matched_rules"] = json.dumps([{"id": r.id, "type": r.rule_type, "content": r.content, "weight": r.weight} for r in result.matched_rules])
        await save_log_async(log_data)
        
        return build_failure_response(
            failure_type="low_confidence",
            failure_reason=f"Intent confidence {result.confidence:.2f} below threshold {threshold}",
            recognition_chain=result.recognition_chain,
            confidence=result.confidence,
            intent=result.intent,
            matched_rules=[
                MatchedRule(
                    id=rule.id,
                    rule_type=rule.rule_type,
                    content=rule.content,
                    weight=rule.weight,
                )
                for rule in result.matched_rules
            ],
            threshold=threshold,
            processing_time_ms=(time.time() - start_time) * 1000
        )

    # Success - build response
    processing_time = (time.time() - start_time) * 1000
    response = build_success_response(result, processing_time)

    # Update log data
    log_data["recognized_intent"] = result.intent
    log_data["confidence"] = result.confidence
    log_data["processing_time_ms"] = processing_time
    if hasattr(result, 'recognition_chain'):
        log_data["recognition_chain"] = json.dumps(result.recognition_chain)
    if hasattr(result, 'matched_rules'):
        log_data["matched_rules"] = json.dumps([{"id": r.id, "type": r.rule_type, "content": r.content, "weight": r.weight} for r in result.matched_rules])

    await save_log_async(log_data)

    # Cache result
    if settings.enable_cache and application.enable_cache:
        cache_key = generate_cache_key(request.app_key, request.text, request.context)
        await cache.set(cache_key, response.model_dump())

    return response


@router.post("/recognize/batch", response_model=BatchRecognizeResponse)
async def recognize_intent_batch(
    request: BatchRecognizeRequest,
    recognizer: RecognizerChain = Depends(get_recognizer_chain),
    config_service: ConfigService = Depends(get_config_service),
    cache: CacheManager = Depends(get_cache),
    api_key_info: dict = Depends(verify_api_key),
) -> BatchRecognizeResponse:
    """
    Recognize intent for multiple texts.

    Processes texts in parallel for better performance.
    """
    import asyncio

    if len(request.texts) > settings.max_batch_size:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Batch size exceeds maximum: {settings.max_batch_size}",
        )

    # Process in parallel
    tasks = [
        recognize_intent(
            RecognizeRequest(
                app_key=request.app_key,
                text=text,
            ),
            recognizer,
            config_service,
            cache,
            api_key_info,
        )
        for text in request.texts
    ]

    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Handle exceptions
    processed_results = []
    cached_count = 0

    for i, result in enumerate(results):
        if isinstance(result, HTTPException):
            # Create error response
            processed_results.append(
                RecognizeResponse(
                    intent="error",
                    confidence=0.0,
                    matched_rules=[],
                )
            )
        elif isinstance(result, Exception):
            logger.error(f"Error processing text {i}: {result}")
            processed_results.append(
                RecognizeResponse(
                    intent="error",
                    confidence=0.0,
                    matched_rules=[],
                )
            )
        else:
            processed_results.append(result)
            if result.cached:
                cached_count += 1

    return BatchRecognizeResponse(
        results=processed_results,
        total_count=len(request.texts),
        cached_count=cached_count,
    )
