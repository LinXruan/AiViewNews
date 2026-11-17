"""Read-only setup completeness for the first-run banner."""
from __future__ import annotations

import shutil
from pathlib import Path

from fastapi import APIRouter, Depends

from ..services import settings
from ..services.auth import require_user

router = APIRouter(prefix="/api/setup", tags=["setup"])


@router.get("/status")
def setup_status(_: dict = Depends(require_user)) -> dict:
    mineru_cmd = settings.value("parse.mineru_cmd")
    parse_ok = bool(shutil.which("mineru")) or bool(mineru_cmd and Path(mineru_cmd).is_file())
    return {
        "llm_ok": bool(settings.value("llm.api_key")),
        "parse_ok": parse_ok,
        "first_run_done": settings.value("ui.first_run_done") == "true",
    }
