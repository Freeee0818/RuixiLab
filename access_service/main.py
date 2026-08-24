"""Standalone account and access-control service entrypoint."""

import argparse

import uvicorn

from config import settings
from .app_factory import create_access_app


app = create_access_app()


def main() -> None:
    parser = argparse.ArgumentParser(description="Ruixi Lab Access Service")
    parser.add_argument("--host", default=settings.ACCESS_SERVICE_HOST)
    parser.add_argument("--port", type=int, default=settings.ACCESS_SERVICE_PORT)
    args = parser.parse_args()

    print(f"\n启动 {settings.APP_NAME} 账号与访问控制服务")
    print(f"地址: http://{args.host}:{args.port}")
    print(f"文档: http://{args.host}:{args.port}/docs\n")
    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
