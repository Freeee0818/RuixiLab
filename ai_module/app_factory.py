"""Application factory for the AI backend."""

from fastapi import FastAPI

from config import settings
from service_common import create_service_app


def create_ai_app() -> FastAPI:
    settings.ensure_ai_directories()

    app = create_service_app(
        service_name="ai",
        title=f"{settings.APP_NAME} AI Assistant API",
        description="AI question answering, RAG retrieval, and Agent Skill/Tool runtime",
    )

    from .routes.assistant import router

    app.include_router(router)
    return app
