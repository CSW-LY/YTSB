#!/usr/bin/env python3
"""
测试脚本，检查关键模块的导入是否成功。
"""

import sys
import traceback

print("Python路径:")
for path in sys.path:
    print(f"  - {path}")

print("\n测试导入...")

# 测试1: 导入Application模型
try:
    from app.models.database import Application
    print("✓ Application 导入成功")
except Exception as e:
    print(f"✗ Application 导入失败: {e}")
    traceback.print_exc()

# 测试2: 导入schema模型
try:
    from app.models.schema import ApplicationResponse
    print("✓ ApplicationResponse 导入成功")
except Exception as e:
    print(f"✗ ApplicationResponse 导入失败: {e}")
    traceback.print_exc()

# 测试3: 导入admin模块
try:
    from app.api.v1.admin import list_applications
    print("✓ list_applications 导入成功")
except Exception as e:
    print(f"✗ list_applications 导入失败: {e}")
    traceback.print_exc()

# 测试4: 导入intent模块
try:
    from app.api.v1.intent import recognize
    print("✓ recognize 导入成功")
except Exception as e:
    print(f"✗ recognize 导入失败: {e}")
    traceback.print_exc()

print("\n测试完成！")