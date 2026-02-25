#!/usr/bin/env python3
"""
测试脚本，尝试导入并创建应用实例。
"""

import sys
import traceback

print("Testing application import and initialization...")
print("Python version:", sys.version)
print("Current directory:", sys.path[0])
print("=" * 60)

# 测试1: 导入app模块
try:
    from app import __version__
    print("✓ app module imported successfully")
except Exception as e:
    print(f"✗ Failed to import app module: {e}")
    traceback.print_exc()

# 测试2: 导入main模块
try:
    from app.main import create_app
    print("✓ create_app imported successfully")
except Exception as e:
    print(f"✗ Failed to import create_app: {e}")
    traceback.print_exc()

# 测试3: 尝试创建应用实例
try:
    from app.main import create_app
    app = create_app()
    print("✓ Application instance created successfully")
    print(f"  App title: {app.title}")
    print(f"  App version: {app.version}")
    print(f"  Docs URL: {app.docs_url}")
    print(f"  Redoc URL: {app.redoc_url}")
except Exception as e:
    print(f"✗ Failed to create application instance: {e}")
    traceback.print_exc()

print("\nTest completed!")