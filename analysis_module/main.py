"""Standalone compute service entrypoint."""

import argparse

import uvicorn

from config import settings
from .app_factory import create_compute_app


app = create_compute_app()


def main() -> None:
    parser = argparse.ArgumentParser(description="GuideLab Compute Service")
    parser.add_argument("--host", default=settings.COMPUTE_SERVICE_HOST)
    parser.add_argument("--port", type=int, default=settings.COMPUTE_SERVICE_PORT)
    args = parser.parse_args()

    print(f"\n启动 {settings.APP_NAME} 计算服务（绘图 + PySR）")
    print(f"地址: http://{args.host}:{args.port}")
    print(f"文档: http://{args.host}:{args.port}/docs\n")
    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
