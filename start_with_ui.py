"""Start script for intent service with web UI."""

import os
import sys
import uvicorn
import time
import logging

# Set environment variable to use main_ui
os.environ["PYTHONPATH"] = "."

# Import settings to get configuration
sys.path.insert(0, ".")
from app.core.config import get_settings

# Configure logging with timestamp
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] [%(module)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Add a simple progress indicator for long-running tasks
def log_progress(phase, current, total, message=""):
    """Log progress for long-running tasks."""
    if total > 0:
        percentage = (current / total) * 100
        logger.info(f"[{phase}] Progress: {current}/{total} ({percentage:.1f}%) - {message}")
    else:
        logger.info(f"[{phase}] Progress: {current} - {message}")

settings = get_settings()

logger.info("=" * 80)
logger.info(f"Starting {settings.app_name} with Web UI")
logger.info("=" * 80)
logger.info(f"Host: {settings.api_host}:{settings.api_port}")
logger.info(f"Debug: {settings.debug}")
logger.info(f"Model: {settings.model_type}")
logger.info(f"Semantic: {settings.enable_semantic_matching}")
logger.info(f"LLM Fallback: {settings.enable_llm_fallback}")
logger.info(f"Cache: {settings.enable_cache}")
logger.info("=" * 80)
logger.info(f"Web UI: http://localhost:{settings.api_port}/")
logger.info(f"API Docs: http://localhost:{settings.api_port}/docs" if settings.debug else "")
logger.info(f"Config: http://localhost:{settings.api_port}/api/ui/config")
logger.info("=" * 80)

if __name__ == "__main__":
    total_start_time = time.time()
    
    # 直接在启动时加载模型，验证模型加载过程
    logger.info("=== [START] Direct model loading test ===")
    model_start_time = time.time()
    
    try:
        logger.info("Importing embedding model...")
        from app.ml.embedding import get_embedding_model
        embedding_model = get_embedding_model()
        logger.info("Loading embedding model...")
        
        # 同步加载模型（为了测试）
        import asyncio
        asyncio.run(embedding_model.load())
        
        model_load_time = (time.time() - model_start_time) * 1000
        logger.info(f"Model loaded successfully in {model_load_time:.2f}ms")
        logger.info(f"Model dimension: {embedding_model.dimension}")
    except Exception as e:
        logger.error(f"Failed to load model: {e}")
        import traceback
        traceback.print_exc()
    
    model_end_time = time.time()
    model_total_time = (model_end_time - model_start_time) * 1000
    logger.info(f"=== [END] Direct model loading test (Total: {model_total_time:.2f}ms) ===")
    
    # 创建应用
    logger.info("=== [START] Creating app ===")
    app_start_time = time.time()
    
    try:
        from app.main_ui import create_app
        logger.info("Initializing FastAPI application...")
        app = create_app()
        app_create_time = (time.time() - app_start_time) * 1000
        logger.info(f"Application created successfully in {app_create_time:.2f}ms")
    except Exception as e:
        logger.error(f"Failed to create app: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    app_end_time = time.time()
    app_total_time = (app_end_time - app_start_time) * 1000
    logger.info(f"=== [END] Creating app (Total: {app_total_time:.2f}ms) ===")
    
    # 启动服务器
    logger.info("=== [START] Starting uvicorn server ===")
    server_start_time = time.time()
    
    logger.info(f"Starting uvicorn on {settings.api_host}:{settings.api_port}...")
    logger.info("Server startup may take several minutes. Please wait...")
    logger.info("Monitoring startup status...")
    
    try:
        uvicorn.run(
            app,
            host=settings.api_host,
            port=settings.api_port,
            reload=settings.debug,
            log_level="info",
        )
    except Exception as e:
        logger.error(f"Failed to start server: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    server_end_time = time.time()
    server_total_time = (server_end_time - server_start_time) * 1000
    logger.info(f"=== [END] Starting uvicorn server (Total: {server_total_time:.2f}ms) ===")
    
    total_end_time = time.time()
    total_total_time = (total_end_time - total_start_time) * 1000
    logger.info(f"=== [END] Complete startup process (Total: {total_total_time:.2f}ms) ===")
