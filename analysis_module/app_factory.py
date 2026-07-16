"""Application factory for the compute backend."""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from config import settings
from service_common import create_service_app


def create_compute_app() -> FastAPI:
    settings.ensure_compute_directories()

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        try:
            yield
        finally:
            from pysr_module.pysr_service import service

            service.shutdown()

    app = create_service_app(
        service_name="compute",
        title=f"{settings.APP_NAME} Compute API",
        description="Data plotting, statistics, and PySR symbolic-regression tasks",
        lifespan=lifespan,
    )

    from .routes import router as analysis_router
    from pysr_module.routes.pysr_tasks import router as pysr_router

    app.include_router(analysis_router)
    app.include_router(pysr_router)
    return app
