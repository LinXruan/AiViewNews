"""Report read/save, markdown preview and DOCX export."""
from __future__ import annotations

from datetime import datetime, timezone
from urllib.parse import quote

from fastapi import APIRouter, Depends
from fastapi.responses import Response
from pydantic import BaseModel, Field

from ..db import get_conn
from ..errors import ApiError
from ..services import exporter, markdown_renderer
from ..services.auth import require_user

router = APIRouter(prefix="/api", tags=["reports"])


class ReportPayload(BaseModel):
    content_md: str = Field(default="", max_length=200_000)


class RenderPayload(BaseModel):
    markdown: str = Field(default="", max_length=200_000)


def _owned_task(task_id: int, user_id: int) -> dict:
    row = get_conn().execute(
        "SELECT * FROM tasks WHERE id = ? AND user_id = ?", (task_id, user_id)
    ).fetchone()
    if row is None:
        raise ApiError(404, "task_not_found", "任务不存在")
    return dict(row)


@router.get("/tasks/{task_id}/report")
def get_report(task_id: int, user: dict = Depends(require_user)) -> dict:
    task = _owned_task(task_id, user["id"])
    row = get_conn().execute(
        "SELECT * FROM reports WHERE task_id = ?", (task["id"],)
    ).fetchone()
    if row is None:
        return {
            "task_id": task["id"],
            "title": "",
            "content_md": "",
            "edited_at": None,
            "exists": False,
        }
    report = dict(row)
    return {
        "task_id": task["id"],
        "title": report["title"],
        "content_md": report["content_md"],
        "edited_at": report["edited_at"],
        "exists": True,
    }


@router.put("/tasks/{task_id}/report")
def save_report(
    task_id: int, payload: ReportPayload, user: dict = Depends(require_user)
) -> dict:
    task = _owned_task(task_id, user["id"])
    conn = get_conn()
    edited_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    title = "分析报告"
    for line in payload.content_md.splitlines():
        if line.startswith("# "):
            title = line[2:].strip() or title
            break
    with conn:
        updated = conn.execute(
            "UPDATE reports SET title = ?, content_md = ?, edited_at = ? WHERE task_id = ?",
            (title, payload.content_md, edited_at, task["id"]),
        ).rowcount
        if not updated:
            conn.execute(
                "INSERT INTO reports (task_id, title, content_md, created_at, edited_at) "
                "VALUES (?, ?, ?, ?, ?)",
                (task["id"], title, payload.content_md, edited_at, edited_at),
            )
    return {"task_id": task["id"], "edited_at": edited_at}


@router.post("/render")
def render_markdown(payload: RenderPayload, user: dict = Depends(require_user)) -> dict:
    return {"html": markdown_renderer.render(payload.markdown)}


@router.get("/tasks/{task_id}/report.docx")
def download_report(task_id: int, user: dict = Depends(require_user)) -> Response:
    task = _owned_task(task_id, user["id"])
    row = get_conn().execute(
        "SELECT title, content_md FROM reports WHERE task_id = ?", (task["id"],)
    ).fetchone()
    title = row["title"] if row else "分析报告"
    content = row["content_md"] if row else ""
    data = exporter.export_docx(title, content)
    filename = exporter.safe_filename(task["query"])
    headers = {
        "Content-Disposition": "attachment; filename*=UTF-8''" + quote(filename)
    }
    return Response(
        content=data,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers=headers,
    )
