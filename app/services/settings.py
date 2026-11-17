"""Runtime settings stored in SQLite, with env and built-in fallbacks."""
from __future__ import annotations

import os
import time
from datetime import datetime, timezone

from ..db import get_conn

DEFAULTS = {
    "llm.base_url": "https://api.deepseek.com",
    "llm.model": "deepseek-chat",
    "llm.api_key": "",
    "llm.temperature": "0.2",
    "llm.timeout": "60",
    "parse.mineru_cmd": "",
    "parse.tier": "flash",
    "ui.first_run_done": "false",
}

ENV_NAMES = {
    "llm.base_url": "DEEPSEEK_BASE_URL",
    "llm.model": "DEEPSEEK_MODEL",
    "llm.api_key": "DEEPSEEK_API_KEY",
    "llm.temperature": "DEEPSEEK_TEMPERATURE",
    "llm.timeout": "DEEPSEEK_TIMEOUT",
    "parse.mineru_cmd": "MINERU_CMD",
    "parse.tier": "MINERU_TIER",
}

_TTL_SECONDS = 1.0
_cache: dict[str, str] = {}
_cache_at = 0.0


def _reload() -> None:
    global _cache, _cache_at
    rows = get_conn().execute("SELECT key, value FROM settings").fetchall()
    _cache = {row["key"]: (row["value"] or "") for row in rows}
    _cache_at = time.monotonic()


def _ensure_cache() -> None:
    if time.monotonic() - _cache_at > _TTL_SECONDS:
        _reload()


def invalidate() -> None:
    global _cache_at
    _cache_at = 0.0


def value(key: str) -> str:
    _ensure_cache()
    if key in _cache:
        return _cache[key]
    env_name = ENV_NAMES.get(key)
    if env_name and os.getenv(env_name) is not None:
        return os.getenv(env_name, "").strip()
    return DEFAULTS.get(key, "")


def mask(secret: str) -> str:
    if not secret:
        return ""
    if len(secret) <= 8:
        return "****"
    return secret[:3] + "****" + secret[-4:]


def public() -> dict:
    api_key = value("llm.api_key")
    return {
        "llm": {
            "base_url": value("llm.base_url"),
            "model": value("llm.model"),
            "api_key": mask(api_key),
            "api_key_set": bool(api_key),
            "temperature": value("llm.temperature"),
            "timeout": value("llm.timeout"),
        },
        "parse": {
            "mineru_cmd": value("parse.mineru_cmd"),
            "tier": value("parse.tier"),
        },
        "first_run_done": value("ui.first_run_done") == "true",
    }


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def save(values: dict[str, str | None], user_id: int) -> None:
    conn = get_conn()
    with conn:
        for key, raw in values.items():
            if raw is None:
                continue
            conn.execute(
                "INSERT INTO settings (key, value, updated_at, updated_by) VALUES (?, ?, ?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value = excluded.value, "
                "updated_at = excluded.updated_at, updated_by = excluded.updated_by",
                (key, raw, _now(), user_id),
            )
    invalidate()
    complete = bool(value("llm.api_key")) and bool(value("parse.mineru_cmd"))
    if complete and value("ui.first_run_done") != "true":
        save({"ui.first_run_done": "true"}, user_id)
