"""Application factory for the standalone access service."""

import logging

from fastapi import FastAPI

from config import settings
from service_common import create_service_app


logger = logging.getLogger(__name__)


def create_access_app() -> FastAPI:
    settings.ensure_access_directories()

    from .routes import get_account_store, router

    accounts = get_account_store().list_accounts()
    if settings.ACCESS_CONTROL_ENABLED and not any(
        account["enabled"] and account["is_admin"] for account in accounts
    ):
        logger.warning(
            "访问门禁已启用，但当前没有可用管理员；"
            "请临时配置 ACCESS_BOOTSTRAP_ADMIN_USERNAME/PASSWORD 并重启 access 服务"
        )

    app = create_service_app(
        service_name="access",
        title=f"{settings.APP_NAME} Access API",
        description="Invitation accounts, login sessions, campus-network access, and browser administration",
    )
    app.include_router(router)
    return app


__all__ = ["create_access_app"]
