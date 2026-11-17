"""Document records: ownership checks and parse-status transitions."""
from __future__ import annotations

import shutil
from datetime import datetime, timezone
from pathlib import Path

from .. import paths
from ..db import get_conn


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def public_document(row: dict) -> dict:
    return {
        "id": row["id"],
        "history_id": row["history_id"],
        "filename": row["filename"],
        "page_count": row["page_count"],
        "char_count": row["char_count"],
        "parse_status": row["parse_status"],
        "parse_error": row["parse_error"],
        "pdf_purged_at": row.get("pdf_purged_at"),
        "created_at": row["created_at"],
    }


def list_documents(user_id: int, history_id: int | None = None) -> list[dict]:
    sql = "SELECT * FROM documents WHERE user_id = ?"
    params: list = [user_id]
    if history_id is not None:
        sql += " AND history_id = ?"
        params.append(history_id)
    sql += " ORDER BY id DESC"
    rows = get_conn().execute(sql, params).fetchall()
    return [public_document(dict(row)) for row in rows]


def get_document(doc_id: int, user_id: int | None = None) -> dict | None:
    sql = "SELECT * FROM documents WHERE id = ?"
    params: tuple = (doc_id,)
    if user_id is not None:
        sql += " AND user_id = ?"
        params = (doc_id, user_id)
    row = get_conn().execute(sql, params).fetchone()
    return dict(row) if row else None


def create_document(
    user_id: int,
    history_id: int,
    filename: str,
    stored_path: str,
    page_count: int | None = None,
) -> dict:
    conn = get_conn()
    cursor = conn.execute(
        "INSERT INTO documents "
        "(user_id, history_id, filename, stored_path, page_count, parse_status, created_at) "
        "VALUES (?, ?, ?, ?, ?, 'pending', ?)",
        (user_id, history_id, filename, stored_path, page_count, _now()),
    )
    conn.commit()
    return get_document(cursor.lastrowid) or {}


def delete_document(doc_id: int) -> None:
    conn = get_conn()
    with conn:
        conn.execute("DELETE FROM documents WHERE id = ?", (doc_id,))


def mark_parsing(doc_id: int) -> None:
    conn = get_conn()
    with conn:
        conn.execute(
            "UPDATE documents SET parse_status = 'parsing', parse_error = NULL WHERE id = ?",
            (doc_id,),
        )


def mark_parsed(
    doc_id: int, md_path: str, page_count: int, char_count: int, page_offsets: str
) -> None:
    conn = get_conn()
    with conn:
        conn.execute(
            "UPDATE documents SET parse_status = 'parsed', parse_error = NULL, "
            "md_path = ?, page_count = ?, char_count = ?, page_offsets = ? WHERE id = ?",
            (md_path, page_count, char_count, page_offsets, doc_id),
        )


def mark_failed(doc_id: int, error: str) -> None:
    conn = get_conn()
    with conn:
        conn.execute(
            "UPDATE documents SET parse_status = 'failed', parse_error = ? WHERE id = ?",
            (error[-2000:], doc_id),
        )


def purge_pdf(doc_id: int) -> None:
    """PDFs are temporary: remove the file and forget its path in SQLite."""
    doc = get_document(doc_id)
    if doc is None:
        return
    stored = doc.get("stored_path")
    if stored:
        Path(stored).unlink(missing_ok=True)
    conn = get_conn()
    with conn:
        conn.execute(
            "UPDATE documents SET stored_path = NULL, pdf_purged_at = ? WHERE id = ?",
            (_now(), doc_id),
        )


def delete_artifacts(doc_id: int) -> None:
    shutil.rmtree(paths.PARSED_DIR / str(doc_id), ignore_errors=True)


def pending_document_ids() -> list[int]:
    rows = get_conn().execute(
        "SELECT id FROM documents WHERE parse_status = 'pending' ORDER BY id"
    ).fetchall()
    return [row["id"] for row in rows]


def read_markdown(doc: dict) -> str:
    md_path = doc.get("md_path")
    if not md_path:
        raise FileNotFoundError("document has no parsed markdown")
    return Path(md_path).read_text(encoding="utf-8")
