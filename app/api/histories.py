"""Big-history listing, detail and deletion."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from ..errors import ApiError
from ..services import histories
from ..services.auth import require_user

router = APIRouter(prefix="/api/histories", tags=["histories"])


@router.get("")
def list_histories(q: str = "", user: dict = Depends(require_user)) -> dict:
    return {"histories": histories.list_histories(user["id"], q)}


@router.get("/{history_id}")
def get_history(history_id: int, user: dict = Depends(require_user)) -> dict:
    detail = histories.get_detail(history_id, user["id"])
    if detail is None:
        raise ApiError(404, "history_not_found", "历史记录不存在")
    return detail


@router.delete("/{history_id}")
def delete_history(history_id: int, user: dict = Depends(require_user)) -> dict:
    if histories.get_raw(history_id, user["id"]) is None:
        raise ApiError(404, "history_not_found", "历史记录不存在")
    histories.delete_history(history_id, user["id"])
    return {"ok": True}
