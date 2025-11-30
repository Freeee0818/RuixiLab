#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
PySR Web服务 - 主入口
用于启动符号回归分析服务，包括API和Web界面
"""

import os
import sys
import argparse
import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 加载环境变量
from dotenv import load_dotenv
from pathlib import Path
project_root = Path(__file__).parent.parent
env_path = project_root / ".env"
if env_path.exists():
    load_dotenv(env_path)

# 导入配置
from config import get_config
from config.logging_config import setup_logging

# 设置日志
logger = setup_logging()
config = get_config()

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
    allow_origins=config.CORS_ORIGINS if config.CORS_ORIGINS else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 将API应用挂载到根路径和/api路径
app.mount("/api", api_app)
app.mount("/", api_app)

# 获取静态文件目录
static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")

# 挂载静态文件服务（如果目录存在）
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="PySR Web Service")
    parser.add_argument("--host", type=str, default=config.API_HOST, help="Host to run the service on")
    parser.add_argument("--port", type=int, default=config.API_PORT, help="Port to run the service on")
    args = parser.parse_args()
    
    logger.info(f"Starting PySR Web Service on http://{args.host}:{args.port}")
    logger.info("API endpoints available at:")
    logger.info(f"  - http://{args.host}:{args.port}/api")
    logger.info(f"  - http://{args.host}:{args.port}/")
    print(f"\n{'='*60}")
    print(f"智析实验平台 - PySR服务")
    print(f"{'='*60}")
    print(f"服务地址: http://{args.host}:{args.port}")
    print(f"环境: {os.getenv('ENVIRONMENT', 'development')}")
    print(f"按 Ctrl+C 停止服务\n")
    
    # 启动服务
    uvicorn.run(app, host=args.host, port=args.port, log_config=None)

if __name__ == "__main__":
    main() 