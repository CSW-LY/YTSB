"""Test configuration loading."""

import sys
import os
print(f"Current directory: {os.getcwd()}")
print(f".env file exists: {os.path.exists('.env')}")

# Read .env file directly
if os.path.exists('.env'):
    print("=== .env file content ===")
    with open('.env', 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#'):
                print(line)
    print("========================")

sys.path.insert(0, ".")
from app.core.config import get_settings

# Clear cache
get_settings.cache_clear()

# Get settings
settings = get_settings()

print("=== Configuration Test ===")
print(f"ENABLE_LLM_FALLBACK: {settings.enable_llm_fallback}")
print(f"LLM_API_KEY: {settings.llm_api_key}")
print(f"LLM_BASE_URL: {settings.llm_base_url}")
print(f"LLM_MODEL: {settings.llm_model}")
print("========================")
