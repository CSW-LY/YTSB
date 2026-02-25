#!/usr/bin/env python3
"""
启动脚本，用于在端口8080上启动服务器。
"""

import uvicorn
from app.main import app

if __name__ == "__main__":
    print("Starting server on port 8080...")
    print("Server will be available at http://localhost:8080")
    print("Press Ctrl+C to stop the server")
    print("=" * 60)
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8080,
        log_level="info"
    )