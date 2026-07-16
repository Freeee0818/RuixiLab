"""Signed anonymous classroom sessions shared by the AI and compute services.

The browser only receives the token as an HttpOnly cookie.  The AI service can
forward the same signed token to the compute service through an internal
header, so a task keeps the same owner across the service boundary without a
shared database.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import logging
import secrets
import time
from dataclasses import dataclass
from http.cookies import SimpleCookie
from typing import Any, Optional

from fastapi import HTTPException, Request

from config import settings

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ClassroomSession:
    session_id: str
    token: str
    expires_at: int
    is_new: bool = False


def _secret() -> bytes:
    value = settings.CLASSROOM_SESSION_SECRET.strip()
    if not value:
        raise RuntimeError("CLASSROOM_SESSION_SECRET 未配置")
    return value.encode("utf-8")


def _signature(payload: str) -> str:
    digest = hmac.new(_secret(), payload.encode("ascii"), hashlib.sha256).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


def issue_classroom_session(now: Optional[int] = None) -> ClassroomSession:
    current = int(time.time() if now is None else now)
    expires_at = current + settings.CLASSROOM_SESSION_TTL_SECONDS
    session_id = secrets.token_hex(24)
    payload = f"{session_id}.{expires_at}"
    return ClassroomSession(
        session_id=session_id,
        token=f"{payload}.{_signature(payload)}",
        expires_at=expires_at,
        is_new=True,
    )


def verify_classroom_session(token: str, now: Optional[int] = None) -> Optional[ClassroomSession]:
    try:
        session_id, expires_text, supplied_signature = token.split(".", 2)
        if len(session_id) != 48 or any(ch not in "0123456789abcdef" for ch in session_id):
            return None
        expires_at = int(expires_text)
        current = int(time.time() if now is None else now)
        if expires_at <= current:
            return None
        payload = f"{session_id}.{expires_at}"
        if not hmac.compare_digest(supplied_signature, _signature(payload)):
            return None
        return ClassroomSession(session_id, token, expires_at, is_new=False)
    except (AttributeError, TypeError, ValueError):
        return None


def _cookie_header(session: ClassroomSession) -> bytes:
    cookie = SimpleCookie()
    cookie[settings.CLASSROOM_SESSION_COOKIE_NAME] = session.token
    morsel = cookie[settings.CLASSROOM_SESSION_COOKIE_NAME]
    morsel["path"] = "/"
    morsel["max-age"] = str(settings.CLASSROOM_SESSION_TTL_SECONDS)
    morsel["httponly"] = True
    morsel["samesite"] = settings.CLASSROOM_SESSION_COOKIE_SAMESITE
    if settings.CLASSROOM_SESSION_COOKIE_SECURE:
        morsel["secure"] = True
    return morsel.OutputString().encode("latin-1")


class ClassroomSessionMiddleware:
    """Pure ASGI middleware that does not buffer streaming/SSE responses."""

    def __init__(self, app: Any):
        self.app = app

    async def __call__(self, scope: dict, receive: Any, send: Any) -> None:
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope)
        header_token = request.headers.get(settings.CLASSROOM_SESSION_HEADER)
        cookie_token = request.cookies.get(settings.CLASSROOM_SESSION_COOKIE_NAME)
        supplied_token = header_token or cookie_token
        session = verify_classroom_session(supplied_token) if supplied_token else None

        # An invalid internal bearer token must not silently create a different
        # owner, otherwise an Agent task could become unreachable immediately.
        if header_token and session is None:
            response = HTTPException(status_code=401, detail="无效或已过期的课堂会话")
            from starlette.responses import JSONResponse

            await JSONResponse(
                status_code=response.status_code,
                content={"detail": response.detail},
            )(scope, receive, send)
            return

        if session is None:
            session = issue_classroom_session()

        scope.setdefault("state", {})["classroom_session"] = session

        async def send_with_session(message: dict) -> None:
            if message.get("type") == "http.response.start" and session.is_new and not header_token:
                headers = list(message.get("headers") or [])
                headers.append((b"set-cookie", _cookie_header(session)))
                message["headers"] = headers
            await send(message)

        await self.app(scope, receive, send_with_session)


def get_classroom_session(request: Request) -> ClassroomSession:
    session = getattr(request.state, "classroom_session", None)
    if not isinstance(session, ClassroomSession):
        raise HTTPException(status_code=500, detail="课堂会话中间件未初始化")
    return session


def session_forward_headers(session: ClassroomSession) -> dict[str, str]:
    return {settings.CLASSROOM_SESSION_HEADER: session.token}


def classroom_security_warning() -> Optional[str]:
    secret = settings.CLASSROOM_SESSION_SECRET.strip()
    if (
        "change-me" in secret.lower()
        or "development" in secret.lower()
        or len(secret) < 32
    ):
        return "CLASSROOM_SESSION_SECRET 仍是开发值或长度不足 32；部署前必须更换"
    return None


__all__ = [
    "ClassroomSession",
    "ClassroomSessionMiddleware",
    "classroom_security_warning",
    "get_classroom_session",
    "issue_classroom_session",
    "session_forward_headers",
    "verify_classroom_session",
]
