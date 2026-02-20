"""Shared recognizer chain module."""

import hashlib
import json
import logging
from typing import Dict, Optional

from app.core.config import get_settings
from app.models.database import AppIntent
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


def _get_app_config_key(app_config: AppIntent) -> str:
    """生成应用配置的唯一键。"""
    config_data = {
        "app_key": app_config.app_key,
        "enable_keyword": app_config.enable_keyword_matching,
        "enable_regex": app_config.enable_regex_matching,
        "enable_semantic": app_config.enable_semantic_matching,
        "enable_llm": app_config.enable_llm_fallback,
        "semantic_threshold": settings.semantic_similarity_threshold,
    }
    config_str = json.dumps(config_data, sort_keys=True)
    config_hash = hashlib.md5(config_str.encode()).hexdigest()
    return f"{app_config.app_key}:{config_hash}"


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


async def get_recognizer_chain_for_app(app_config: AppIntent) -> RecognizerChain:
    """
    根据应用配置创建或获取缓存的识别器链。

    使用缓存避免每次请求都重新初始化模型，特别是语义模型。
    """
    config_key = _get_app_config_key(app_config)

    if config_key in _recognizer_chain_cache:
        logger.debug(f"Using cached recognizer chain for {app_config.app_key}")
        return _recognizer_chain_cache[config_key]

    logger.info(f"Creating new recognizer chain for {app_config.app_key}")
    recognizers = []

    if app_config.enable_keyword_matching:
        recognizers.append(KeywordRecognizer())

    if app_config.enable_regex_matching:
        recognizers.append(RegexRecognizer())

    if app_config.enable_semantic_matching and settings.enable_semantic_matching:
        recognizers.append(SemanticRecognizer({
            "threshold": settings.semantic_similarity_threshold,
        }))

    if app_config.enable_llm_fallback and settings.enable_llm_fallback:
        recognizers.append(LLMRecognizer())

    chain = RecognizerChain(recognizers)
    await chain.initialize_all()

    _recognizer_chain_cache[config_key] = chain
    _config_version_cache[config_key] = config_key

    logger.info(
        f"Cached recognizer chain for app {app_config.app_key} with {len(recognizers)} recognizers"
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
