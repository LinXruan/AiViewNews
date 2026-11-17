"""Big histories (PDF sets) and their publication lifecycle."""
from __future__ import annotations

import re
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .. import paths
from ..db import get_conn
from . import documents

GUEST_RETENTION_HOURS = 24
DRAFT_RETENTION_HOURS = 24
TITLE_MAX = 60


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _iso(value: datetime) -> str:
    return value.isoformat(timespec="seconds")


def create_draft(user_id: int, is_guest: bool) -> int:
    now = datetime.now(timezone.utc)
    expires = _iso(now + timedelta(hours=GUEST_RETENTION_HOURS)) if is_guest else None
    conn = get_conn()
    cursor = conn.execute(
        "INSERT INTO histories (user_id, title, status, created_at, updated_at, expires_at) "
        "VALUES (?, '', 'draft', ?, ?, ?)",
        (user_id, _iso(now), _iso(now), expires),
    )
    conn.commit()
    return cursor.lastrowid


def get_raw(history_id: int, user_id: int | None = None) -> dict | None:
    sql = "SELECT * FROM histories WHERE id = ?"
    params: tuple = (history_id,)
    if user_id is not None:
        sql += " AND user_id = ?"
        params = (history_id, user_id)
    row = get_conn().execute(sql, params).fetchone()
    return dict(row) if row else None


def _clean_title(text: str) -> str:
    value = re.sub(r"[*_`]+", "", text)
    value = re.sub(r"\s+", " ", value).strip(" #-")
    return value[:TITLE_MAX]


def _title_for_history(history_id: int) -> str:
    rows = get_conn().execute(
        "SELECT * FROM documents WHERE history_id = ? ORDER BY id", (history_id,)
    ).fetchall()
    for row in rows:
        doc = dict(row)
        if doc["parse_status"] != "parsed":
            continue
        try:
            text = documents.read_markdown(doc)
        except OSError:
            continue
        for line in text.splitlines():
            title = _clean_title(line)
            if title and not title.isdigit():
                return title
    if rows:
        return Path(rows[0]["filename"]).stem[:TITLE_MAX]
    return "未命名记录"


def publish_if_ready(history_id: int) -> None:
    conn = get_conn()
    history = get_raw(history_id)
    if history is None or history["status"] != "draft":
        return
    rows = conn.execute(
        "SELECT id, parse_status FROM documents WHERE history_id = ?", (history_id,)
    ).fetchall()
    if not rows:
        delete_history_internal(history_id)
        return
    if any(row["parse_status"] in ("pending", "parsing") for row in rows):
        return
    title = _title_for_history(history_id)
    status = "ready" if any(row["parse_status"] == "parsed" for row in rows) else "failed"
    now = _now()
    with conn:
        conn.execute(
            "UPDATE histories SET title = ?, status = ?, published_at = ?, updated_at = ? "
            "WHERE id = ?",
            (title, status, now, now, history_id),
        )


def publish_pending() -> None:
    rows = get_conn().execute(
        "SELECT id FROM histories WHERE status = 'draft'"
    ).fetchall()
    for row in rows:
        publish_if_ready(row["id"])


def touch(history_id: int) -> None:
    conn = get_conn()
    with conn:
        conn.execute(
            "UPDATE histories SET updated_at = ? WHERE id = ?", (_now(), history_id)
        )


def _public_history(row: dict) -> dict:
    return {
        "id": row["id"],
        "title": row["title"],
        "status": row["status"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        "published_at": row["published_at"],
        "expires_at": row["expires_at"],
    }


def _escape_like(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def list_histories(user_id: int, query: str = "") -> list[dict]:
    conn = get_conn()
    sql = (
        "SELECT h.*, "
        "(SELECT COUNT(*) FROM documents d WHERE d.history_id = h.id) AS doc_count, "
        "(SELECT COUNT(*) FROM tasks t WHERE t.history_id = h.id) AS record_count, "
        "(SELECT t.query FROM tasks t WHERE t.history_id = h.id ORDER BY t.id DESC LIMIT 1) AS last_query "
        "FROM histories h WHERE h.user_id = ? AND h.status IN ('ready', 'failed')"
    )
    params: list = [user_id]
    value = query.strip()
    if value:
        pattern = "%" + _escape_like(value) + "%"
        sql += (
            " AND (h.title LIKE ? ESCAPE '\\' OR EXISTS ("
            "SELECT 1 FROM tasks t WHERE t.history_id = h.id AND t.query LIKE ? ESCAPE '\\'))"
        )
        params.extend([pattern, pattern])
    sql += " ORDER BY h.updated_at DESC, h.id DESC LIMIT 100"
    rows = conn.execute(sql, params).fetchall()
    return [dict(row) for row in rows]


def get_detail(history_id: int, user_id: int) -> dict | None:
    history = get_raw(history_id, user_id)
    if history is None:
        return None
    conn = get_conn()
    docs = conn.execute(
        "SELECT * FROM documents WHERE history_id = ? ORDER BY id", (history_id,)
    ).fetchall()
    records = conn.execute(
        "SELECT t.*, (SELECT COUNT(*) FROM events e WHERE e.task_id = t.id) AS event_count "
        "FROM tasks t WHERE t.history_id = ? ORDER BY t.id DESC",
        (history_id,),
    ).fetchall()
    payload = _public_history(history)
    payload["documents"] = [documents.public_document(dict(row)) for row in docs]
    payload["records"] = [dict(row) for row in records]
    return payload


def delete_history_internal(history_id: int) -> None:
    conn = get_conn()
    docs = conn.execute(
        "SELECT id, stored_path FROM documents WHERE history_id = ?", (history_id,)
    ).fetchall()
    for doc in docs:
        if doc["stored_path"]:
            Path(doc["stored_path"]).unlink(missing_ok=True)
        shutil.rmtree(paths.PARSED_DIR / str(doc["id"]), ignore_errors=True)
    with conn:
        conn.execute("DELETE FROM histories WHERE id = ?", (history_id,))


def delete_history(history_id: int, user_id: int) -> None:
    if get_raw(history_id, user_id) is None:
        return
    delete_history_internal(history_id)


def delete_all_for_user(user_id: int) -> None:
    rows = get_conn().execute(
        "SELECT id FROM histories WHERE user_id = ?", (user_id,)
    ).fetchall()
    for row in rows:
        delete_history_internal(row["id"])


def expired_history_ids() -> list[int]:
    rows = get_conn().execute(
        "SELECT id FROM histories WHERE expires_at IS NOT NULL AND expires_at < ?",
        (_now(),),
    ).fetchall()
    return [row["id"] for row in rows]


def stale_draft_ids() -> list[int]:
    cutoff = _iso(datetime.now(timezone.utc) - timedelta(hours=DRAFT_RETENTION_HOURS))
    rows = get_conn().execute(
        "SELECT id FROM histories WHERE status = 'draft' AND created_at < ?",
        (cutoff,),
    ).fetchall()
    return [row["id"] for row in rows]
