#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
PySR Web服务 - 主入口
用于启动符号回归分析服务，包括API和Web界面
"""

import os
import argparse
import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

# 导入API路由
from api import app as api_app

# 创建主应用
app = FastAPI(
    title="PySR Web Service",
    description="Symbolic Regression as a Service",
    version="1.0.0"
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 将API应用挂载到根路径
app.mount("/", api_app)

# 获取静态文件目录
static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")

# 挂载静态文件服务（如果目录存在）
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="PySR Web Service")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Host to run the service on")
    parser.add_argument("--port", type=int, default=8000, help="Port to run the service on")
    args = parser.parse_args()
    
    print(f"Starting PySR Web Service on http://{args.host}:{args.port}")
    print("API endpoints available at:")
    print(f"  - http://{args.host}:{args.port}/")
    print("Press Ctrl+C to stop the server")
    
    # 启动服务
    uvicorn.run(app, host=args.host, port=args.port)

if __name__ == "__main__":
    main() 