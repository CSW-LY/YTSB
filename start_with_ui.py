"""Start script for intent service with web UI."""

import os
import sys
import uvicorn

# Set environment variable to use main_ui
os.environ["PYTHONPATH"] = "."

# Import settings to get configuration
sys.path.insert(0, ".")
from app.core.config import get_settings

settings = get_settings()

print("=" * 60)
print(f"Starting {settings.app_name} with Web UI")
print("=" * 60)
print(f"Host: {settings.api_host}:{settings.api_port}")
print(f"Debug: {settings.debug}")
print(f"Model: {settings.model_type}")
print(f"Semantic: {settings.enable_semantic_matching}")
print(f"LLM Fallback: {settings.enable_llm_fallback}")
print(f"Cache: {settings.enable_cache}")
print("=" * 60)
print(f"Web UI: http://localhost:{settings.api_port}/")
print(f"API Docs: http://localhost:{settings.api_port}/docs" if settings.debug else "")
print(f"Config: http://localhost:{settings.api_port}/api/ui/config")
print("=" * 60)

if __name__ == "__main__":
    import time
    import logging
    
    # 设置根日志级别为DEBUG
    logging.basicConfig(level=logging.DEBUG)
    logger = logging.getLogger(__name__)
    
    # 直接在启动时加载模型，验证模型加载过程
    logger.info("=== Direct model loading test ===")
    start_time = time.time()
    
    try:
        from app.ml.embedding import get_embedding_model
        embedding_model = get_embedding_model()
        logger.info("Loading embedding model...")
        
        # 同步加载模型（为了测试）
        import asyncio
        asyncio.run(embedding_model.load())
        
        load_time = (time.time() - start_time) * 1000
        logger.info(f"Model loaded successfully in {load_time:.2f}ms")
        logger.info(f"Model dimension: {embedding_model.dimension}")
    except Exception as e:
        logger.error(f"Failed to load model: {e}")
        import traceback
        traceback.print_exc()
    
    logger.info("=== Creating app ===")
    from app.main_ui import create_app
    app = create_app()
    
    logger.info("=== Starting uvicorn ===")
    uvicorn.run(
        app,
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug,
        log_level="debug",
    )
