"""Standalone AI assistant service entrypoint."""

import argparse

import uvicorn

from config import settings
from .app_factory import create_ai_app


app = create_ai_app()


def main() -> None:
    parser = argparse.ArgumentParser(description="GuideLab AI Assistant Service")
    parser.add_argument("--host", default=settings.AI_SERVICE_HOST)
    parser.add_argument("--port", type=int, default=settings.AI_SERVICE_PORT)
    args = parser.parse_args()

    print(f"\n启动 {settings.APP_NAME} AI 服务（问答 + RAG + Agent）")
    print(f"地址: http://{args.host}:{args.port}")
    print(f"文档: http://{args.host}:{args.port}/docs\n")
    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
