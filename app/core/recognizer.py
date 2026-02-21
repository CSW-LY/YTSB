"""Shared recognizer chain module."""

import hashlib
import json
import logging
from typing import Dict, Optional

from app.core.config import get_settings
from app.models.database import Application
from app.services.recognizer import (
    KeywordRecognizer,
    RegexRecognizer,
    SemanticRecognizer,
    LLMRecognizer,
    RecognizerChain,
)

logger = logging.getLogger(__name__)
settings = get_settings()

# ============================================================================
# Recognizer Chain Cache
# ============================================================================

_recognizer_chain_cache: Dict[str, RecognizerChain] = {}
_config_version_cache: Dict[str, str] = {}


def _get_app_config_key(application: Application) -> str:
    """生成应用配置的唯一键。"""
    config_data = {
        "app_key": application.app_key,
        "enable_keyword": application.enable_keyword,
        "enable_regex": application.enable_regex,
        "enable_semantic": application.enable_semantic,
        "enable_llm": application.enable_llm_fallback,
        "semantic_threshold": settings.semantic_similarity_threshold,
    }
    config_str = json.dumps(config_data, sort_keys=True)
    config_hash = hashlib.md5(config_str.encode()).hexdigest()
    return f"{application.app_key}:{config_hash}"


async def get_recognizer_chain() -> RecognizerChain:
    """Get or create recognizer chain singleton."""
    if _recognizer_chain_cache:
        return list(_recognizer_chain_cache.values())[0]

    recognizers = [
        KeywordRecognizer(),
        RegexRecognizer(),
    ]
    # Only add semantic/LLM recognizers if explicitly enabled
    try:
        if settings.enable_semantic_matching:
            recognizers.append(SemanticRecognizer({
                "threshold": settings.semantic_similarity_threshold,
            }))
        if settings.enable_llm_fallback:
            recognizers.append(LLMRecognizer())
    except Exception as e:
        logger.warning(f"Failed to initialize optional recognizers: {e}")

    chain = RecognizerChain(recognizers)
    await chain.initialize_all()
    logger.info("Recognizer chain initialized")
    
    config_key = "global:default"
    _recognizer_chain_cache[config_key] = chain
    return chain


async def get_recognizer_chain_for_app(application: Application) -> RecognizerChain:
    """
    根据应用配置创建或获取缓存的识别器链。

    使用缓存避免每次请求都重新初始化模型，特别是语义模型。
    """
    config_key = _get_app_config_key(application)

    if config_key in _recognizer_chain_cache:
        logger.debug(f"Using cached recognizer chain for {application.app_key} (cache key: {config_key})")
        return _recognizer_chain_cache[config_key]

    logger.warning(f"Creating new recognizer chain for {application.app_key} (cache key: {config_key})")
    logger.warning(f"Application config - enable_keyword: {application.enable_keyword}, enable_regex: {application.enable_regex}, enable_semantic: {application.enable_semantic}, enable_llm_fallback: {application.enable_llm_fallback}")
    recognizers = []

    if application.enable_keyword:
        recognizers.append(KeywordRecognizer())

    if application.enable_regex:
        recognizers.append(RegexRecognizer())

    if application.enable_semantic and settings.enable_semantic_matching:
        recognizers.append(SemanticRecognizer({
            "threshold": settings.semantic_similarity_threshold,
        }))

    if application.enable_llm_fallback and settings.enable_llm_fallback:
        recognizers.append(LLMRecognizer())

    chain = RecognizerChain(recognizers)
    await chain.initialize_all()

    _recognizer_chain_cache[config_key] = chain
    _config_version_cache[config_key] = config_key

    logger.info(
        f"Cached recognizer chain for app {application.app_key} with {len(recognizers)} recognizers"
    )
    return chain


async def clear_recognizer_cache(app_key: Optional[str] = None) -> None:
    """
    清除识别器缓存。

    Args:
        app_key: 如果提供，只清除指定应用的缓存；否则清除所有缓存
    """
    if app_key:
        keys_to_remove = [k for k in _recognizer_chain_cache.keys() if k.startswith(f"{app_key}:")]
        for key in keys_to_remove:
            _recognizer_chain_cache.pop(key, None)
            _config_version_cache.pop(key, None)
        logger.info(f"Cleared recognizer cache for app: {app_key}")
    else:
        _recognizer_chain_cache.clear()
        _config_version_cache.clear()
        logger.info("Cleared all recognizer cache")


def get_llm_recognizer() -> Optional[LLMRecognizer]:
    """
    Get LLM recognizer instance from cached chains.

    Returns:
        LLMRecognizer instance if found, None otherwise
    """
    for chain in _recognizer_chain_cache.values():
        for recognizer in chain.recognizers:
            if isinstance(recognizer, LLMRecognizer):
                logger.debug(f"Found LLM recognizer in cached chain")
                return recognizer
    logger.warning("No LLM recognizer found in cached chains")
    return None
