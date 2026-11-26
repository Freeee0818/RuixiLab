"""Invitation login and browser-based account administration."""

from __future__ import annotations

import threading
import time
from collections import defaultdict, deque
from functools import lru_cache
from typing import Optional

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel, Field

from config import settings
from service_common.access import (
    get_access_identity,
    issue_access_token,
    request_client_ip,
    require_admin,
)
from access_service.account_store import (
    AccountConflictError,
    AccountStore,
    AccountValidationError,
)


router = APIRouter(prefix="/auth", tags=["access"])


class LoginPayload(BaseModel):
    identifier: str = Field(min_length=1, max_length=254)
    password: str = Field(min_length=1, max_length=256)


class AccountCreatePayload(BaseModel):
    username: str
    password: str
    display_name: str = ""
    email: str = ""
    is_admin: bool = False
    class_id: Optional[int] = Field(default=None, gt=0, strict=True)


class AccountUpdatePayload(BaseModel):
    display_name: Optional[str] = None
    email: Optional[str] = None
    password: Optional[str] = None
    enabled: Optional[bool] = None
    is_admin: Optional[bool] = None
    class_id: Optional[int] = Field(default=None, gt=0, strict=True)


class ClassCreatePayload(BaseModel):
    name: str = Field(min_length=1, max_length=128)


class LoginAttemptLimiter:
    def __init__(self) -> None:
        self._attempts: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def _prune(self, key: str, now: float) -> deque[float]:
        attempts = self._attempts[key]
        cutoff = now - settings.ACCESS_LOGIN_WINDOW_SECONDS
        while attempts and attempts[0] <= cutoff:
            attempts.popleft()
        return attempts

    def check(self, key: str) -> bool:
        with self._lock:
            return len(self._prune(key, time.monotonic())) < settings.ACCESS_LOGIN_MAX_ATTEMPTS

    def record_failure(self, key: str) -> None:
        with self._lock:
            self._prune(key, time.monotonic()).append(time.monotonic())

    def clear(self, key: str) -> None:
        with self._lock:
            self._attempts.pop(key, None)


LOGIN_LIMITER = LoginAttemptLimiter()


@lru_cache(maxsize=1)
def get_account_store() -> AccountStore:
    store = AccountStore(settings.ACCESS_DB_PATH)
    store.ensure_bootstrap_admin()
    return store


def _require_current_admin(request: Request):
    identity = require_admin(request)
    try:
        account = get_account_store().get(identity.username)
    except AccountValidationError as exc:
        raise HTTPException(status_code=403, detail="管理员账号无效") from exc
    if account is None or not account["enabled"] or not account["is_admin"]:
        raise HTTPException(status_code=403, detail="管理员权限已失效，请重新登录")
    return identity


def _set_access_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=settings.ACCESS_COOKIE_NAME,
        value=token,
        max_age=settings.ACCESS_TOKEN_TTL_SECONDS,
        httponly=True,
        secure=settings.CLASSROOM_SESSION_COOKIE_SECURE,
        samesite=settings.CLASSROOM_SESSION_COOKIE_SAMESITE,
        path="/",
    )


def _clear_access_cookie(response: Response) -> None:
    response.delete_cookie(
        key=settings.ACCESS_COOKIE_NAME,
        path="/",
        secure=settings.CLASSROOM_SESSION_COOKIE_SECURE,
        httponly=True,
        samesite=settings.CLASSROOM_SESSION_COOKIE_SAMESITE,
    )


def _clear_classroom_cookie(response: Response) -> None:
    # A classroom session owns PySR tasks. Clearing it on logout prevents the
    # next student on a shared browser from inheriting the previous student's
    # task history after signing in with a different invited account.
    response.delete_cookie(
        key=settings.CLASSROOM_SESSION_COOKIE_NAME,
        path="/",
        secure=settings.CLASSROOM_SESSION_COOKIE_SECURE,
        httponly=True,
        samesite=settings.CLASSROOM_SESSION_COOKIE_SAMESITE,
    )


@router.get("/session")
async def access_session(request: Request, response: Response):
    identity = get_access_identity(request)
    account = None
    if identity and identity.source == "account":
        try:
            account = get_account_store().get(identity.username)
        except AccountValidationError:
            account = None
        if account is None or not account["enabled"]:
            identity = None
            _clear_access_cookie(response)

    return {
        "access_control_enabled": settings.ACCESS_CONTROL_ENABLED,
        "authenticated": identity is not None,
        "source": identity.source if identity else "none",
        "role": identity.role if identity else "guest",
        "username": identity.username if identity and identity.source == "account" else "",
        "display_name": (account or {}).get("display_name", "") if account else "",
        "email": (account or {}).get("email", "") if account else "",
        "is_admin": bool(identity and identity.is_admin),
        "admin_email": settings.ACCESS_ADMIN_EMAIL,
        "client_ip": request_client_ip(request),
    }


@router.post("/login")
async def login(payload: LoginPayload, request: Request, response: Response):
    client_ip = request_client_ip(request) or "unknown"
    if not LOGIN_LIMITER.check(client_ip):
        raise HTTPException(status_code=429, detail="登录尝试过多，请稍后再试")

    account = get_account_store().authenticate(payload.identifier, payload.password)
    if account is None:
        LOGIN_LIMITER.record_failure(client_ip)
        raise HTTPException(status_code=401, detail="账号或密码错误，或账号已停用")

    LOGIN_LIMITER.clear(client_ip)
    token, identity = issue_access_token(
        subject=str(account["id"]),
        username=account["username"],
        role="admin" if account["is_admin"] else "student",
    )
    _set_access_cookie(response, token)
    return {
        "success": True,
        "username": identity.username,
        "display_name": account["display_name"],
        "role": identity.role,
        "is_admin": identity.is_admin,
    }


@router.post("/logout")
async def logout(response: Response):
    _clear_access_cookie(response)
    _clear_classroom_cookie(response)
    return {"success": True}


@router.get("/admin/accounts")
async def list_accounts(request: Request):
    _require_current_admin(request)
    return {"accounts": get_account_store().list_accounts()}


@router.post("/admin/accounts", status_code=201)
async def create_account(payload: AccountCreatePayload, request: Request):
    admin = _require_current_admin(request)
    try:
        account = get_account_store().create_account(
            username=payload.username,
            password=payload.password,
            display_name=payload.display_name,
            email=payload.email,
            is_admin=payload.is_admin,
            created_by=admin.username,
            class_id=payload.class_id,
        )
    except AccountConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except AccountValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"account": account}


@router.patch("/admin/accounts/{username}")
async def update_account(username: str, payload: AccountUpdatePayload, request: Request):
    admin = _require_current_admin(request)
    store = get_account_store()
    try:
        target = store.get(username)
    except AccountValidationError as exc:
        raise HTTPException(status_code=404, detail="账号不存在") from exc
    if target is None:
        raise HTTPException(status_code=404, detail="账号不存在")

    demoting = payload.is_admin is False or payload.enabled is False
    enabled_admins = [item for item in store.list_accounts() if item["is_admin"] and item["enabled"]]
    if target["is_admin"] and target["enabled"] and demoting and len(enabled_admins) <= 1:
        raise HTTPException(status_code=400, detail="不能停用或取消唯一的管理员")
    if target["username"] == admin.username and demoting:
        raise HTTPException(status_code=400, detail="不能停用或取消当前登录的管理员")

    try:
        account = store.update_account(
            username,
            display_name=payload.display_name,
            email=payload.email,
            password=payload.password,
            enabled=payload.enabled,
            is_admin=payload.is_admin,
            **({"class_id": payload.class_id} if "class_id" in payload.model_fields_set else {}),
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="账号不存在") from exc
    except AccountConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except AccountValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"account": account}


@router.get("/admin/classes")
async def list_classes(request: Request):
    _require_current_admin(request)
    return {"classes": get_account_store().list_classes()}


@router.post("/admin/classes", status_code=201)
async def create_class(payload: ClassCreatePayload, request: Request):
    admin = _require_current_admin(request)
    try:
        classroom = get_account_store().create_class(payload.name, created_by=admin.username)
    except AccountConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except AccountValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"class": classroom}


@router.get("/admin/classes/{class_id}/accounts")
async def list_class_accounts(class_id: int, request: Request):
    _require_current_admin(request)
    try:
        accounts = get_account_store().list_class_accounts(class_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="班级不存在") from exc
    return {"accounts": accounts}


__all__ = ["get_account_store", "router"]
