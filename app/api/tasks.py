"""Create analysis tasks, list them and expose events."""
from __future__ import annotations

import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from .. import workers
from ..db import get_conn
from ..errors import ApiError
from ..services import documents
from ..services.auth import require_user

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class CreateTaskPayload(BaseModel):
    doc_ids: list[int] = Field(min_length=1, max_length=10)
    query: str = Field(min_length=1, max_length=500)


def _public_task(row: dict) -> dict:
    return {
        "id": row["id"],
        "query": row["query"],
        "status": row["status"],
        "timeline_summary": row["timeline_summary"],
        "error": row["error"],
        "created_at": row["created_at"],
        "finished_at": row["finished_at"],
        "event_count": row.get("event_count", 0),
    }


def _owned_task(task_id: int, user_id: int) -> dict:
    row = get_conn().execute(
        "SELECT * FROM tasks WHERE id = ? AND user_id = ?", (task_id, user_id)
    ).fetchone()
    if row is None:
        raise ApiError(404, "task_not_found", "任务不存在")
    return dict(row)


def _task_detail(task: dict) -> dict:
    conn = get_conn()
    count = conn.execute(
        "SELECT COUNT(*) FROM events WHERE task_id = ?", (task["id"],)
    ).fetchone()[0]
    report = conn.execute(
        "SELECT id FROM reports WHERE task_id = ?", (task["id"],)
    ).fetchone()
    docs = conn.execute(
        "SELECT d.id, d.filename FROM documents d JOIN task_documents td ON td.doc_id = d.id "
        "WHERE td.task_id = ? ORDER BY d.id",
        (task["id"],),
    ).fetchall()
    payload = _public_task(dict(task))
    payload["event_count"] = count
    payload["has_report"] = report is not None
    payload["documents"] = [dict(row) for row in docs]
    return payload


@router.post("")
def create_task(payload: CreateTaskPayload, user: dict = Depends(require_user)) -> dict:
    query = payload.query.strip()
    if not query:
        raise ApiError(400, "empty_query", "查询内容不能为空")
    doc_ids = list(dict.fromkeys(payload.doc_ids))
    docs = []
    for doc_id in doc_ids:
        doc = documents.get_document(doc_id, user["id"])
        if doc is None:
            raise ApiError(404, "document_not_found", "文档不存在或无权访问")
        if doc["parse_status"] != "parsed":
            raise ApiError(409, "document_not_ready", "文档尚未解析完成：" + doc["filename"])
        docs.append(doc)

    conn = get_conn()
    try:
        cursor = conn.execute(
            "INSERT INTO tasks (user_id, query, status, created_at) VALUES (?, ?, 'pending', ?)",
            (user["id"], query, _now()),
        )
        task_id = cursor.lastrowid
        conn.executemany(
            "INSERT INTO task_documents (task_id, doc_id) VALUES (?, ?)",
            [(task_id, doc["id"]) for doc in docs],
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    workers.enqueue_analysis(task_id)
    return _task_detail(_owned_task(task_id, user["id"]))


@router.get("")
def list_tasks(user: dict = Depends(require_user)) -> dict:
    conn = get_conn()
    rows = conn.execute(
        "SELECT t.*, (SELECT COUNT(*) FROM events e WHERE e.task_id = t.id) AS event_count "
        "FROM tasks t WHERE t.user_id = ? ORDER BY t.id DESC LIMIT 50",
        (user["id"],),
    ).fetchall()
    tasks = []
    for row in rows:
        task = _public_task(dict(row))
        titles = conn.execute(
            "SELECT event_text FROM events WHERE task_id = ? ORDER BY order_index LIMIT 3",
            (task["id"],),
        ).fetchall()
        task["event_titles"] = [item["event_text"][:30] for item in titles]
        tasks.append(task)
    return {"tasks": tasks}


@router.get("/{task_id}")
def get_task(task_id: int, user: dict = Depends(require_user)) -> dict:
    return _task_detail(_owned_task(task_id, user["id"]))


@router.get("/{task_id}/events")
def get_events(task_id: int, user: dict = Depends(require_user)) -> dict:
    task = _owned_task(task_id, user["id"])
    rows = get_conn().execute(
        "SELECT e.*, d.filename FROM events e JOIN documents d ON d.id = e.doc_id "
        "WHERE e.task_id = ? ORDER BY e.order_index",
        (task["id"],),
    ).fetchall()
    events = []
    for row in rows:
        item = dict(row)
        item["source_offset"] = json.loads(item["source_offset"]) if item["source_offset"] else None
        events.append(item)
    return {"events": events}
