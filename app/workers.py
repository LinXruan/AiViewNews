"""Single-thread parse queue and analysis queue. SQLite access is thread-local."""
from __future__ import annotations

import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

from .db import get_conn
from .services import documents, parser

_parse_pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix="parse")
_analysis_pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix="analyze")
_lock = threading.Lock()
_parse_inflight: set[int] = set()
_analysis_inflight: set[int] = set()


def _run_parse(doc_id: int) -> None:
    try:
        parser.parse_document(doc_id)
    finally:
        with _lock:
            _parse_inflight.discard(doc_id)


def enqueue_parse(doc_id: int) -> None:
    with _lock:
        if doc_id in _parse_inflight:
            return
        _parse_inflight.add(doc_id)
    documents.mark_parsing(doc_id)
    _parse_pool.submit(_run_parse, doc_id)


def _run_analysis(task_id: int) -> None:
    from .services import analyzer

    try:
        analyzer.analyze_task(task_id)
    except Exception as exc:
        conn = get_conn()
        with conn:
            conn.execute(
                "UPDATE tasks SET status = 'failed', error = ?, finished_at = ? "
                "WHERE id = ?",
                (str(exc)[-2000:], datetime.now(timezone.utc).isoformat(timespec="seconds"), task_id),
            )
    finally:
        with _lock:
            _analysis_inflight.discard(task_id)


def enqueue_analysis(task_id: int) -> None:
    from .services import analyzer

    with _lock:
        if task_id in _analysis_inflight:
            return
        _analysis_inflight.add(task_id)
    analyzer.mark_analyzing(task_id)
    _analysis_pool.submit(_run_analysis, task_id)


def requeue_interrupted() -> None:
    """Called once at startup: documents and tasks were reset to pending."""
    for doc_id in documents.pending_document_ids():
        enqueue_parse(doc_id)
    rows = get_conn().execute(
        "SELECT id FROM tasks WHERE status = 'pending' ORDER BY id"
    ).fetchall()
    for row in rows:
        enqueue_analysis(row["id"])


def shutdown() -> None:
    _parse_pool.shutdown(wait=False, cancel_futures=True)
    _analysis_pool.shutdown(wait=False, cancel_futures=True)
