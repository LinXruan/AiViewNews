"""Login, logout, current user and the one-time first-admin channel."""
from __future__ import annotations

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

from ..errors import ApiError
from ..services import auth

router = APIRouter(prefix="/api", tags=["auth"])

_LOOPBACK_HOSTS = {"127.0.0.1", "::1", "localhost"}


class LoginPayload(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=256)


class FirstAdminPayload(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=256)
    password_confirm: str = Field(min_length=1, max_length=256)


def _is_loopback(request: Request) -> bool:
    return bool(request.client and request.client.host in _LOOPBACK_HOSTS)


@router.post("/login")
def login(payload: LoginPayload, request: Request) -> dict:
    user = auth.authenticate(payload.username, payload.password)
    if user is None:
        raise ApiError(401, "invalid_credentials", "用户名或密码错误")
    request.session.clear()
    request.session["uid"] = user["id"]
    return user


@router.post("/guest")
def guest_login(request: Request) -> dict:
    user = auth.guest_user()
    request.session.clear()
    request.session["uid"] = user["id"]
    return user


@router.post("/register")
def register(payload: LoginPayload, request: Request) -> dict:
    user = auth.create_user(payload.username, payload.password, role="user")
    request.session.clear()
    request.session["uid"] = user["id"]
    return user


@router.post("/logout")
def logout(request: Request) -> dict:
    request.session.clear()
    return {"ok": True}


@router.get("/me")
def me(request: Request) -> dict:
    return auth.current_user(request)


@router.get("/setup/admin")
def first_admin_status(request: Request) -> dict:
    return {"available": auth.admin_count() == 0 and _is_loopback(request)}


@router.post("/setup/admin")
def create_first_admin(payload: FirstAdminPayload, request: Request) -> dict:
    if auth.admin_count() > 0:
        raise ApiError(403, "setup_closed", "管理员已创建，请直接登录")
    if not _is_loopback(request):
        raise ApiError(403, "setup_forbidden", "首次初始化仅允许在本机进行")
    if payload.password != payload.password_confirm:
        raise ApiError(400, "password_mismatch", "两次输入的密码不一致")
    user = auth.create_first_admin(payload.username, payload.password)
    request.session.clear()
    request.session["uid"] = user["id"]
    return user
