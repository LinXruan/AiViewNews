"""Current-user account: password change and full account deletion."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field

from ..db import get_conn
from ..errors import ApiError
from ..services import auth, histories
from ..services.auth import hash_password, require_user, verify_password

router = APIRouter(prefix="/api/me", tags=["account"])


class PasswordPayload(BaseModel):
    old_password: str = Field(min_length=1, max_length=256)
    new_password: str = Field(min_length=6, max_length=256)


@router.patch("/password")
def change_password(
    payload: PasswordPayload, user: dict = Depends(require_user)
) -> dict:
    if user["username"] == auth.GUEST_USERNAME:
        raise ApiError(400, "guest_password", "不登陆模式不能修改密码")
    row = auth.get_user_by_username(user["username"])
    if row is None or not verify_password(payload.old_password, row["password_hash"]):
        raise ApiError(400, "wrong_password", "旧密码不正确")
    conn = get_conn()
    with conn:
        conn.execute(
            "UPDATE users SET password_hash = ? WHERE id = ?",
            (hash_password(payload.new_password), user["id"]),
        )
    return {"ok": True}


@router.delete("")
def delete_account(request: Request, user: dict = Depends(require_user)) -> dict:
    if user["username"] == auth.GUEST_USERNAME:
        raise ApiError(400, "guest_delete", "不登陆模式没有可注销的账号")
    if user["role"] == "admin" and auth.admin_count() <= 1:
        raise ApiError(400, "last_admin", "不能注销最后一个管理员")
    histories.delete_all_for_user(user["id"])
    conn = get_conn()
    with conn:
        conn.execute("DELETE FROM users WHERE id = ?", (user["id"],))
    request.session.clear()
    return {"ok": True}
