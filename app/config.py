from __future__ import annotations

import os
import secrets

from . import paths

DEFAULT_LLM_BASE_URL = "https://api.deepseek.com"
DEFAULT_LLM_MODEL = "deepseek-chat"
SESSION_MAX_AGE_SECONDS = 7 * 24 * 3600


def _env(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


def _setting(key: str) -> str:
    from .services import settings

    return settings.value(key)


def llm_base_url() -> str:
    return _setting("llm.base_url")


def llm_model() -> str:
    return _setting("llm.model")


def llm_api_key() -> str:
    return _setting("llm.api_key")


def llm_temperature() -> float:
    try:
        return float(_setting("llm.temperature"))
    except ValueError:
        return 0.2


def llm_timeout() -> float:
    try:
        return float(_setting("llm.timeout"))
    except ValueError:
        return 60.0


def admin_username() -> str:
    return _env("ADMIN_USERNAME", "admin")


def admin_password() -> str:
    return _env("ADMIN_PASSWORD")


def demo_password() -> str:
    return _env("DEMO_PASSWORD")


def mineru_cmd() -> str:
    return _setting("parse.mineru_cmd")


def mineru_tier() -> str:
    return _setting("parse.tier") or "flash"


def pandoc_cmd() -> str:
    return _setting("export.pandoc")


def session_secret() -> str:
    """Prefer .env, otherwise generate once and keep it in DATA_DIR."""
    configured = _env("SESSION_SECRET")
    if configured:
        return configured
    if paths.SECRET_PATH.exists():
        stored = paths.SECRET_PATH.read_text(encoding="utf-8").strip()
        if stored:
            return stored
    secret = secrets.token_hex(32)
    paths.ensure_dirs()
    paths.SECRET_PATH.write_text(secret, encoding="utf-8")
    try:
        os.chmod(paths.SECRET_PATH, 0o600)
    except OSError:
        pass
    return secret
