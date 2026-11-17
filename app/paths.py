"""Filesystem layout. Every writable location is resolved here."""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


def _resolve_data_dir() -> Path:
    configured = os.getenv("DATA_DIR", "").strip()
    base = Path(configured).expanduser() if configured else BASE_DIR / "data"
    return base.resolve()


DATA_DIR = _resolve_data_dir()
UPLOAD_DIR = DATA_DIR / "uploads"
PARSED_DIR = DATA_DIR / "parsed"
LOG_DIR = DATA_DIR / "logs"
DB_PATH = DATA_DIR / "db.sqlite3"
SECRET_PATH = DATA_DIR / "secret.key"

APP_DIR = Path(__file__).resolve().parent
SCHEMA_PATH = APP_DIR / "schema.sql"
WEB_DIR = BASE_DIR / "web"


def ensure_dirs() -> None:
    """Create all writable directories. Safe to call repeatedly."""
    for directory in (DATA_DIR, UPLOAD_DIR, PARSED_DIR, LOG_DIR):
        directory.mkdir(parents=True, exist_ok=True)
