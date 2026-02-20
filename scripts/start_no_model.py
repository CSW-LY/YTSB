"""Fast start script without loading embedding model."""

import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, ".")

import uvicorn

# Set environment variable to disable semantic matching
os.environ["ENABLE_SEMANTIC_MATCHING"] = "false"

from app.core.config import get_settings

settings = get_settings()

print("=" * 50)
print(f"Starting {settings.app_name} without semantic matching")
print("=" * 50)
print(f"Host: {settings.api_host}:{settings.api_port}")
print("Semantic matching: DISABLED")
print("=" * 50)

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True,
        workers=1,
    )
