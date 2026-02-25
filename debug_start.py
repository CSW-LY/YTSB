#!/usr/bin/env python3
"""
调试脚本，用于启动服务器并显示详细的错误信息。
"""

import uvicorn
from app.main import app

if __name__ == "__main__":
    print("Starting server in debug mode...")
    print("Server will be available at http://localhost:8000")
    print("Press Ctrl+C to stop the server")
    print("=" * 60)
    
    # 启动服务器，使用详细的日志级别
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="debug",
        reload_dirs=["app"]
    )