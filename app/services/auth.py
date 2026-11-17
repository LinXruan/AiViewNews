"""Password hashing, user records, seeding and request guards."""
from __future__ import annotations

import hashlib
import hmac
import secrets
import sqlite3
from datetime import datetime, timezone

from fastapi import HTTPException, Request

from .. import config
from ..db import get_conn
from ..errors import ApiError

PBKDF2_ITERATIONS = 100_000
USERNAME_MIN = 3
USERNAME_MAX = 32
PASSWORD_MIN = 6


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS
    )
    return f"{salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        salt_hex, digest_hex = stored.split("$", 1)
        salt = bytes.fromhex(salt_hex)
    except ValueError:
        return False
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS
    )
    return hmac.compare_digest(digest.hex(), digest_hex)


def _validated(username: str, password: str) -> tuple[str, str]:
    username = username.strip()
    if not USERNAME_MIN <= len(username) <= USERNAME_MAX:
        raise ApiError(
            400,
            "invalid_username",
            f"用户名长度需为 {USERNAME_MIN}-{USERNAME_MAX} 个字符",
        )
    if len(password) < PASSWORD_MIN:
        raise ApiError(400, "invalid_password", f"密码至少 {PASSWORD_MIN} 位")
    return username, password


def public_user(row: dict) -> dict:
    return {"id": row["id"], "username": row["username"], "role": row["role"]}


def get_user_by_id(user_id: int) -> dict | None:
    row = get_conn().execute(
        "SELECT id, username, role FROM users WHERE id = ?", (user_id,)
    ).fetchone()
    return dict(row) if row else None


def get_user_by_username(username: str) -> dict | None:
    row = get_conn().execute(
        "SELECT id, username, role, password_hash FROM users WHERE username = ?",
        (username,),
    ).fetchone()
    return dict(row) if row else None


def user_count() -> int:
    return get_conn().execute("SELECT COUNT(*) FROM users").fetchone()[0]


def admin_count() -> int:
    return get_conn().execute(
        "SELECT COUNT(*) FROM users WHERE role = 'admin'"
    ).fetchone()[0]


def create_user(username: str, password: str, role: str = "user") -> dict:
    username, password = _validated(username, password)
    conn = get_conn()
    try:
        cursor = conn.execute(
            "INSERT INTO users (username, password_hash, role, created_at) "
            "VALUES (?, ?, ?, ?)",
            (username, hash_password(password), role, _now()),
        )
        conn.commit()
    except sqlite3.IntegrityError as exc:
        conn.rollback()
        raise ApiError(409, "username_taken", "用户名已存在") from exc
    return {"id": cursor.lastrowid, "username": username, "role": role}


def authenticate(username: str, password: str) -> dict | None:
    row = get_user_by_username(username.strip())
    if row is None or not verify_password(password, row["password_hash"]):
        return None
    return public_user(row)


def create_first_admin(username: str, password: str) -> dict:
    """Create the only admin when the table is empty. Atomic against races."""
    username, password = _validated(username, password)
    conn = get_conn()
    conn.execute("BEGIN IMMEDIATE")
    try:
        if conn.execute("SELECT 1 FROM users WHERE role = 'admin' LIMIT 1").fetchone():
            raise ApiError(403, "setup_closed", "管理员已创建，请直接登录")
        cursor = conn.execute(
            "INSERT INTO users (username, password_hash, role, created_at) "
            "VALUES (?, ?, 'admin', ?)",
            (username, hash_password(password), _now()),
        )
        conn.commit()
    except ApiError:
        conn.rollback()
        raise
    except sqlite3.IntegrityError as exc:
        conn.rollback()
        raise ApiError(409, "username_taken", "用户名已存在") from exc
    except Exception:
        conn.rollback()
        raise
    return {"id": cursor.lastrowid, "username": username, "role": "admin"}


def seed_initial_users() -> None:
    """Seed from .env. The packaged build has no .env and uses /setup instead."""
    username = config.admin_username()
    password = config.admin_password()
    if username and password and get_user_by_username(username) is None:
        create_user(username, password, role="admin")

    demo_password = config.demo_password()
    if demo_password and get_user_by_username("demo") is None:
        create_user("demo", demo_password, role="user")


def current_user(request: Request) -> dict:
    user_id = request.session.get("uid")
    if not isinstance(user_id, int):
        raise HTTPException(status_code=401, detail="请先登录")
    row = get_user_by_id(user_id)
    if row is None:
        request.session.clear()
        raise HTTPException(status_code=401, detail="登录已失效，请重新登录")
    return public_user(row)


def require_user(request: Request) -> dict:
    return current_user(request)


def require_admin(request: Request) -> dict:
    user = current_user(request)
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="需要管理员权限")
    return user
