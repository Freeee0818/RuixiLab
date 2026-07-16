"""Common HTTP concerns shared by independently deployed services."""

from __future__ import annotations

from typing import Any, Callable, Optional

from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from .session import ClassroomSessionMiddleware, classroom_security_warning


def create_service_app(
    *,
    service_name: str,
    title: str,
    description: str,
    lifespan: Optional[Callable[..., Any]] = None,
) -> FastAPI:
    app = FastAPI(
        title=title,
        description=description,
        version=settings.APP_VERSION,
        lifespan=lifespan,
    )

    warning = classroom_security_warning()
    if warning:
        import logging

        logging.getLogger(__name__).warning(warning)

    app.add_middleware(ClassroomSessionMiddleware)

    cors_origins = settings.CORS_ORIGINS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if "*" in cors_origins else cors_origins,
        allow_credentials=settings.CORS_ALLOW_CREDENTIALS and "*" not in cors_origins,
        allow_methods=settings.CORS_ALLOW_METHODS,
        allow_headers=settings.CORS_ALLOW_HEADERS,
        expose_headers=["*"],
        max_age=3600,
    )

    @app.get("/", tags=["system"])
    async def root():
        return {"service": service_name, "status": "running"}

    @app.get("/health", tags=["system"])
    async def health():
        return {"service": service_name, "status": "ok"}

    @app.get("/favicon.ico", include_in_schema=False)
    async def favicon():
        return Response(status_code=204)

    @app.get("/robots.txt", include_in_schema=False)
    async def robots_txt():
        return Response("User-agent: *\nDisallow: /\n", media_type="text/plain")

    return app
