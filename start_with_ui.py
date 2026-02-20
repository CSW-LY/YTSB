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
    from app.main_ui import create_app
    app = create_app()
    uvicorn.run(
        app,
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug,
        log_level="info",
    )
