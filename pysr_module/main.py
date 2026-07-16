#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
PySR Web服务 - 主入口
用于启动符号回归分析服务，包括API和Web界面
支持两种模式：
- 开发模式：无 dist 时，API 挂载在 /，可选 pysr_module/static
- 打包模式：有 dist 时，API 挂载在 /api，根路径提供 Vue SPA
支持 PyInstaller 冻结运行：通过 sys._MEIPASS 定位内嵌的 dist 与 config。
"""

import os
import sys
import argparse
import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

# PyInstaller 打包后：确保项目根（解压目录）在 path 中，并作为 PROJECT_ROOT
if getattr(sys, "frozen", False):
    _MEIPASS = getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
    sys.path.insert(0, _MEIPASS)
    PROJECT_ROOT = _MEIPASS
else:
    PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from config import settings

# 导入API路由（必须在 PROJECT_ROOT 设置后，以便 config 等可被找到）
# 兼容两种运行方式：
# - 作为包模块运行：python -m pysr_module.main / scripts.start_backend 导入 pysr_module.main
# - 直接脚本运行：python pysr_module/main.py
if __package__:
    from .api import app as api_app  # type: ignore
else:
    from api import app as api_app

DIST_DIR = os.path.join(PROJECT_ROOT, "dist")
DIST_INDEX = os.path.join(DIST_DIR, "index.html")

# 只有 PyInstaller 打包后才启用一体模式，开发时始终走 dev 模式
HAS_FRONTEND_DIST = getattr(sys, "frozen", False) and os.path.exists(DIST_INDEX)

# 创建主应用
app = FastAPI(
    title="PySR Web Service",
    description="Symbolic Regression as a Service",
    version="1.0.0"
)

cors_origins = settings.CORS_ORIGINS
cors_allow_credentials = settings.CORS_ALLOW_CREDENTIALS and "*" not in cors_origins

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if "*" in cors_origins else cors_origins,
    allow_credentials=cors_allow_credentials,
    allow_methods=settings.CORS_ALLOW_METHODS,
    allow_headers=settings.CORS_ALLOW_HEADERS,
)


@app.get("/health", include_in_schema=False)
async def health():
    return {"status": "ok"}

if HAS_FRONTEND_DIST:
    # 打包模式：API 在 /api，根路径提供 Vue SPA
    app.mount("/api", api_app)
    assets_dir = os.path.join(DIST_DIR, "assets")
    if os.path.isdir(assets_dir):
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    @app.get("/")
    def serve_index():
        return FileResponse(DIST_INDEX)

    @app.get("/{full_path:path}")
    def serve_spa(full_path: str):
        # 非 API、非 assets 的路径由 SPA 接管（如 /analysis）
        return FileResponse(DIST_INDEX)
else:
    # 开发模式：API 在根路径
    app.mount("/", api_app)
    static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
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

    # 启动服务（关闭访问日志，只显示警告和错误）
    uvicorn.run(
        app,
        host=args.host,
        port=args.port,
        access_log=False,  # 关闭访问日志（GET/POST请求）
        log_level="warning"  # 只显示警告和错误
    )

if __name__ == "__main__":
    main()
