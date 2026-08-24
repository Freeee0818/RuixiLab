"""Shared invitation and trusted-network access control.

The access service owns the account database, while AI and compute services
verify the same signed access cookie.  Nginx must keep ports 8000/8001/8002 private
and strip the internal classroom-session header from public requests.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import ipaddress
import json
import time
from dataclasses import dataclass
from typing import Any, Optional

from fastapi import HTTPException, Request
from starlette.responses import JSONResponse

from config import settings
from .session import verify_classroom_session


PUBLIC_PATHS = {
    "/",
    "/health",
    "/favicon.ico",
    "/robots.txt",
    "/auth/session",
    "/auth/login",
    "/auth/logout",
}


@dataclass(frozen=True)
class AccessIdentity:
    subject: str
    username: str
    role: str
    source: str
    expires_at: int = 0
    client_ip: str = ""

    @property
    def is_admin(self) -> bool:
        return self.role == "admin"


def _secret() -> bytes:
    value = settings.CLASSROOM_SESSION_SECRET.strip()
    if not value:
        raise RuntimeError("CLASSROOM_SESSION_SECRET 未配置")
    return value.encode("utf-8")


def _b64encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _b64decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode((value + padding).encode("ascii"))


def _signature(payload: str) -> str:
    digest = hmac.new(_secret(), f"guidelab-access.{payload}".encode("ascii"), hashlib.sha256).digest()
    return _b64encode(digest)


def issue_access_token(
    *,
    subject: str,
    username: str,
    role: str,
    now: Optional[int] = None,
) -> tuple[str, AccessIdentity]:
    current = int(time.time() if now is None else now)
    expires_at = current + settings.ACCESS_TOKEN_TTL_SECONDS
    claims = {
        "v": 1,
        "sub": str(subject),
        "username": str(username),
        "role": "admin" if role == "admin" else "student",
        "exp": expires_at,
    }
    payload = _b64encode(json.dumps(claims, separators=(",", ":"), sort_keys=True).encode("utf-8"))
    token = f"{payload}.{_signature(payload)}"
    identity = AccessIdentity(
        subject=claims["sub"],
        username=claims["username"],
        role=claims["role"],
        source="account",
        expires_at=expires_at,
    )
    return token, identity


def verify_access_token(token: str, now: Optional[int] = None) -> Optional[AccessIdentity]:
    try:
        payload, supplied_signature = token.split(".", 1)
        if not hmac.compare_digest(supplied_signature, _signature(payload)):
            return None
        claims = json.loads(_b64decode(payload).decode("utf-8"))
        if claims.get("v") != 1:
            return None
        expires_at = int(claims["exp"])
        current = int(time.time() if now is None else now)
        if expires_at <= current:
            return None
        role = str(claims.get("role") or "")
        if role not in {"student", "admin"}:
            return None
        subject = str(claims.get("sub") or "").strip()
        username = str(claims.get("username") or "").strip()
        if not subject or not username:
            return None
        return AccessIdentity(subject, username, role, "account", expires_at)
    except (AttributeError, KeyError, TypeError, ValueError, json.JSONDecodeError):
        return None


def request_client_ip(request: Request) -> str:
    host = request.client.host if request.client else ""
    if host.startswith("::ffff:"):
        host = host[7:]
    return host


def is_trusted_network(client_ip: str) -> bool:
    if not client_ip:
        return False
    try:
        address = ipaddress.ip_address(client_ip)
    except ValueError:
        return False
    for raw_network in settings.ACCESS_TRUSTED_NETWORKS:
        try:
            if address in ipaddress.ip_network(str(raw_network).strip(), strict=False):
                return True
        except ValueError:
            continue
    return False


def get_access_identity(request: Request) -> Optional[AccessIdentity]:
    identity = getattr(request.state, "access_identity", None)
    return identity if isinstance(identity, AccessIdentity) else None


def require_access_identity(request: Request) -> AccessIdentity:
    identity = get_access_identity(request)
    if identity is None:
        raise HTTPException(status_code=401, detail="需要邀请账号或校园网访问")
    return identity


def require_admin(request: Request) -> AccessIdentity:
    identity = require_access_identity(request)
    if not identity.is_admin:
        raise HTTPException(status_code=403, detail="需要管理员权限")
    return identity


class AccessControlMiddleware:
    """Require an invited account, campus IP, or trusted internal session."""

    def __init__(self, app: Any):
        self.app = app

    async def __call__(self, scope: dict, receive: Any, send: Any) -> None:
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope)
        client_ip = request_client_ip(request)
        identity: Optional[AccessIdentity] = None

        if not settings.ACCESS_CONTROL_ENABLED:
            identity = AccessIdentity("access-disabled", "local", "admin", "disabled", client_ip=client_ip)
        else:
            internal_session = request.headers.get(settings.CLASSROOM_SESSION_HEADER)
            if internal_session and verify_classroom_session(internal_session):
                identity = AccessIdentity("internal-agent", "agent", "student", "internal", client_ip=client_ip)
            else:
                access_token = request.cookies.get(settings.ACCESS_COOKIE_NAME)
                identity = verify_access_token(access_token) if access_token else None
                if identity is not None:
                    identity = AccessIdentity(
                        identity.subject,
                        identity.username,
                        identity.role,
                        identity.source,
                        identity.expires_at,
                        client_ip,
                    )
                elif is_trusted_network(client_ip):
                    identity = AccessIdentity(
                        f"network:{client_ip}",
                        "campus-user",
                        "student",
                        "campus",
                        client_ip=client_ip,
                    )

        scope.setdefault("state", {})["access_identity"] = identity
        scope["state"]["access_client_ip"] = client_ip

        path = str(scope.get("path") or "")
        method = str(scope.get("method") or "GET").upper()
        is_public = method == "OPTIONS" or path in PUBLIC_PATHS
        if settings.ACCESS_CONTROL_ENABLED and identity is None and not is_public:
            await JSONResponse(
                status_code=401,
                content={
                    "detail": "需要邀请账号或校园网访问",
                    "code": "access_required",
                    "admin_email": settings.ACCESS_ADMIN_EMAIL,
                },
            )(scope, receive, send)
            return

        await self.app(scope, receive, send)


__all__ = [
    "AccessControlMiddleware",
    "AccessIdentity",
    "get_access_identity",
    "is_trusted_network",
    "issue_access_token",
    "request_client_ip",
    "require_access_identity",
    "require_admin",
    "verify_access_token",
]
