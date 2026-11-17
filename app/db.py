"""SQLite access: one connection per thread, WAL, foreign keys on."""
from __future__ import annotations

import shutil
import sqlite3
import threading

from . import paths

_local = threading.local()

SCHEMA_VERSION = 1
_LEGACY_TABLES = (
    "events",
    "reports",
    "task_documents",
    "tasks",
    "documents",
    "histories",
)


def get_conn() -> sqlite3.Connection:
    conn: sqlite3.Connection | None = getattr(_local, "conn", None)
    if conn is None:
        paths.ensure_dirs()
        conn = sqlite3.connect(paths.DB_PATH, timeout=5.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA busy_timeout = 5000")
        _local.conn = conn
    return conn


def close_conn() -> None:
    conn: sqlite3.Connection | None = getattr(_local, "conn", None)
    if conn is not None:
        conn.close()
        _local.conn = None


def _clear_legacy_data(conn: sqlite3.Connection) -> None:
    """PLAN 14 starts a new model; old documents/tasks are intentionally deleted."""
    for table in _LEGACY_TABLES:
        conn.execute("DROP TABLE IF EXISTS " + table)
    for path in paths.UPLOAD_DIR.glob("*"):
        if path.is_file():
            path.unlink(missing_ok=True)
    for path in paths.PARSED_DIR.glob("*"):
        if path.is_dir():
            shutil.rmtree(path, ignore_errors=True)
        elif path.is_file():
            path.unlink(missing_ok=True)
    (paths.LOG_DIR / "llm.jsonl").unlink(missing_ok=True)


def init_db() -> None:
    """Apply the schema, resetting legacy data once when the model changes."""
    paths.ensure_dirs()
    conn = get_conn()
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA synchronous = NORMAL")
    version = conn.execute("PRAGMA user_version").fetchone()[0]
    if version < SCHEMA_VERSION:
        _clear_legacy_data(conn)
        conn.executescript(paths.SCHEMA_PATH.read_text(encoding="utf-8"))
        conn.execute("PRAGMA user_version = " + str(SCHEMA_VERSION))
    else:
        conn.executescript(paths.SCHEMA_PATH.read_text(encoding="utf-8"))
    conn.commit()


def reset_interrupted_statuses() -> None:
    """A previous process died while parsing/analyzing; put work back in queue."""
    conn = get_conn()
    with conn:
        conn.execute(
            "UPDATE documents SET parse_status = 'pending', parse_error = NULL "
            "WHERE parse_status = 'parsing'"
        )
        conn.execute(
            "UPDATE tasks SET status = 'pending' WHERE status = 'analyzing'"
        )
