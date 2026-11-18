"""Administrator user/task views plus runtime settings."""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from ..db import get_conn
from ..errors import ApiError
from ..services import llm, parser, settings
from ..services.auth import create_user, require_admin

router = APIRouter(prefix="/api/admin", tags=["admin"])

VALID_TIERS = {"flash", "basic", "standard", "advanced"}


class RolePayload(BaseModel):
    role: str = Field(pattern="^(user|admin)$")


class NewUserPayload(BaseModel):
    username: str = Field(min_length=3, max_length=32)
    password: str = Field(min_length=6, max_length=256)
    role: str = Field(default="user", pattern="^(user|admin)$")


class LlmPayload(BaseModel):
    base_url: str = Field(min_length=1, max_length=300)
    model: str = Field(min_length=1, max_length=100)
    api_key: str | None = ""
    temperature: float = Field(ge=0, le=2)
    timeout: float = Field(ge=5, le=600)


class ParsePayload(BaseModel):
    mineru_cmd: str = Field(default="", max_length=500)
    tier: str = Field(default="flash")


class ExportPayload(BaseModel):
    pandoc: str = Field(default="", max_length=500)


class SettingsPayload(BaseModel):
    llm: LlmPayload
    parse: ParsePayload
    export: ExportPayload = Field(default_factory=ExportPayload)


def _admin_count() -> int:
    return get_conn().execute(
        "SELECT COUNT(*) FROM users WHERE role = 'admin'"
    ).fetchone()[0]


@router.get("/users")
def list_users(_: dict = Depends(require_admin)) -> dict:
    rows = get_conn().execute(
        "SELECT u.id, u.username, u.role, u.avatar_color, u.created_at, "
        "(SELECT COUNT(*) FROM documents d WHERE d.user_id = u.id) AS doc_count, "
        "(SELECT COUNT(*) FROM tasks t WHERE t.user_id = u.id) AS task_count, "
        "(SELECT MAX(t.created_at) FROM tasks t WHERE t.user_id = u.id) AS last_active "
        "FROM users u ORDER BY u.id"
    ).fetchall()
    return {"users": [dict(row) for row in rows]}


@router.post("/users")
def add_user(payload: NewUserPayload, _: dict = Depends(require_admin)) -> dict:
    return create_user(payload.username, payload.password, role=payload.role)


@router.patch("/users/{user_id}")
def change_role(
    user_id: int, payload: RolePayload, _: dict = Depends(require_admin)
) -> dict:
    conn = get_conn()
    row = conn.execute("SELECT id, role FROM users WHERE id = ?", (user_id,)).fetchone()
    if row is None:
        raise ApiError(404, "user_not_found", "用户不存在")
    if row["role"] == "admin" and payload.role != "admin" and _admin_count() <= 1:
        raise ApiError(400, "last_admin", "不能降级最后一个管理员")
    with conn:
        conn.execute("UPDATE users SET role = ? WHERE id = ?", (payload.role, user_id))
    return {"id": user_id, "role": payload.role}


@router.get("/tasks")
def list_all_tasks(
    user_id: int | None = None, _: dict = Depends(require_admin)
) -> dict:
    sql = (
        "SELECT t.*, u.username, "
        "(SELECT COUNT(*) FROM events e WHERE e.task_id = t.id) AS event_count "
        "FROM tasks t JOIN users u ON u.id = t.user_id"
    )
    params: tuple = ()
    if user_id is not None:
        sql += " WHERE t.user_id = ?"
        params = (user_id,)
    sql += " ORDER BY t.id DESC LIMIT 100"
    rows = get_conn().execute(sql, params).fetchall()
    return {"tasks": [dict(row) for row in rows]}


@router.get("/tasks/{task_id}")
def task_detail(task_id: int, _: dict = Depends(require_admin)) -> dict:
    conn = get_conn()
    row = conn.execute(
        "SELECT t.*, u.username FROM tasks t JOIN users u ON u.id = t.user_id "
        "WHERE t.id = ?",
        (task_id,),
    ).fetchone()
    if row is None:
        raise ApiError(404, "task_not_found", "任务不存在")
    task = dict(row)
    events = [
        dict(item)
        for item in conn.execute(
            "SELECT e.*, d.filename FROM events e JOIN documents d ON d.id = e.doc_id "
            "WHERE e.task_id = ? ORDER BY e.order_index",
            (task_id,),
        ).fetchall()
    ]
    for event in events:
        event["source_offset"] = (
            json.loads(event["source_offset"]) if event["source_offset"] else None
        )
    report = conn.execute(
        "SELECT title, content_md, edited_at FROM reports WHERE task_id = ?", (task_id,)
    ).fetchone()
    return {
        "task": task,
        "events": events,
        "report": dict(report) if report else None,
    }


@router.get("/settings")
def get_settings(_: dict = Depends(require_admin)) -> dict:
    return settings.public()


@router.put("/settings")
def put_settings(payload: SettingsPayload, admin: dict = Depends(require_admin)) -> dict:
    if payload.parse.tier not in VALID_TIERS:
        raise ApiError(400, "invalid_tier", "不支持的解析档位")
    updates: dict[str, str | None] = {
        "llm.base_url": payload.llm.base_url.strip(),
        "llm.model": payload.llm.model.strip(),
        "llm.temperature": str(payload.llm.temperature),
        "llm.timeout": str(payload.llm.timeout),
        "parse.mineru_cmd": payload.parse.mineru_cmd.strip(),
        "parse.tier": payload.parse.tier,
        "export.pandoc": payload.export.pandoc.strip(),
    }
    if payload.llm.api_key is not None and payload.llm.api_key.strip():
        updates["llm.api_key"] = payload.llm.api_key.strip()
    elif payload.llm.api_key is None:
        updates["llm.api_key"] = ""
    settings.save(updates, admin["id"])
    return settings.public()


def _mineru_candidates() -> list[str]:
    found: list[str] = []
    which = shutil.which("mineru")
    if which:
        found.append(which)
    env_roots = [
        Path(sys.prefix).resolve().parent,
        Path(sys.prefix).resolve().parent.parent / "envs",
        Path.home() / "anaconda3" / "envs",
        Path.home() / "miniconda3" / "envs",
    ]
    for base in env_roots:
        if not base.is_dir():
            continue
        for env_dir in base.iterdir():
            for candidate in (env_dir / "Scripts" / "mineru.exe", env_dir / "bin" / "mineru"):
                if candidate.is_file() and str(candidate) not in found:
                    found.append(str(candidate))
    return found


@router.get("/settings/detect-mineru")
def detect_mineru(_: dict = Depends(require_admin)) -> dict:
    return {"candidates": _mineru_candidates()}


def _pandoc_candidates() -> list[str]:
    found: list[str] = []
    configured = settings.value("export.pandoc").strip()
    if configured:
        found.append(configured)
    which = shutil.which("pandoc")
    if which:
        found.append(which)
    for candidate in (
        Path("C:/Program Files/Pandoc/pandoc.exe"),
        Path(sys.prefix).resolve().parent / "Library" / "bin" / "pandoc.exe",
        Path.home() / "AppData" / "Local" / "Pandoc" / "pandoc.exe",
    ):
        if candidate.is_file() and str(candidate) not in found:
            found.append(str(candidate))
    return found


@router.get("/settings/detect-pandoc")
def detect_pandoc(_: dict = Depends(require_admin)) -> dict:
    return {"candidates": _pandoc_candidates()}


@router.post("/settings/test-llm")
def test_llm(_: dict = Depends(require_admin)) -> dict:
    return llm.ping()


@router.post("/settings/test-parse")
def test_parse(_: dict = Depends(require_admin)) -> dict:
    return parser.probe()
