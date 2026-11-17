"""Periodic cleanup for guest history, stale drafts and orphan PDFs."""
from __future__ import annotations

import threading
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .. import paths
from . import histories

_stop = threading.Event()
_thread: threading.Thread | None = None
ORPHAN_UPLOAD_HOURS = 6


def _remove_orphan_uploads() -> None:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=ORPHAN_UPLOAD_HOURS)
    for path in paths.UPLOAD_DIR.glob("*.pdf"):
        try:
            modified = datetime.fromtimestamp(path.stat().st_mtime, timezone.utc)
        except OSError:
            continue
        if modified < cutoff:
            path.unlink(missing_ok=True)


def cleanup_once() -> None:
    for history_id in histories.expired_history_ids():
        histories.delete_history_internal(history_id)
    for history_id in histories.stale_draft_ids():
        histories.delete_history_internal(history_id)
    _remove_orphan_uploads()


def _loop() -> None:
    while not _stop.is_set():
        try:
            cleanup_once()
        except Exception:
            pass
        _stop.wait(3600)


def start() -> None:
    global _thread
    if _thread and _thread.is_alive():
        return
    _stop.clear()
    _thread = threading.Thread(target=_loop, name="cleanup", daemon=True)
    _thread.start()


def stop() -> None:
    _stop.set()
