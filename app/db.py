"""SQLite access: one connection per thread, WAL, foreign keys on."""
from __future__ import annotations

import sqlite3
import threading

from . import paths

_local = threading.local()


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


def init_db() -> None:
    """Apply the idempotent schema. Safe on every startup."""
    paths.ensure_dirs()
    conn = get_conn()
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA synchronous = NORMAL")
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
