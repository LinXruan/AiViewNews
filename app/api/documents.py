"""PDF upload, listing and parsed-asset serving."""
from __future__ import annotations

import uuid
from pathlib import Path

import pymupdf
from fastapi import APIRouter, Depends, File, Form, UploadFile
from fastapi.responses import FileResponse

from .. import paths, workers
from ..errors import ApiError
from ..services import documents, histories
from ..services.auth import require_user

router = APIRouter(prefix="/api/documents", tags=["documents"])

MAX_FILE_BYTES = 50 * 1024 * 1024
MAX_FILES = 10
CHUNK_SIZE = 1024 * 1024


def _validate_filename(filename: str) -> str:
    name = Path(filename or "").name
    if not name or not name.lower().endswith(".pdf"):
        raise ApiError(400, "invalid_file_type", "只支持 PDF 文件")
    return name


def _save_upload(upload: UploadFile, destination: Path) -> None:
    total = 0
    first = True
    with destination.open("wb") as handle:
        while True:
            chunk = upload.file.read(CHUNK_SIZE)
            if not chunk:
                break
            if first:
                if not chunk.startswith(b"%PDF-"):
                    raise ApiError(400, "invalid_pdf", "文件内容不是有效的 PDF")
                first = False
            total += len(chunk)
            if total > MAX_FILE_BYTES:
                raise ApiError(413, "file_too_large", "单个文件不能超过 50MB")
            handle.write(chunk)
    if first:
        raise ApiError(400, "empty_file", "文件为空")


@router.post("")
async def upload_documents(
    files: list[UploadFile] = File(...),
    history_id: int | None = Form(None),
    user: dict = Depends(require_user),
) -> dict:
    if len(files) > MAX_FILES:
        raise ApiError(400, "too_many_files", f"一次最多上传 {MAX_FILES} 个文件")

    paths.ensure_dirs()
    created: list[dict] = []
    saved_paths: list[Path] = []
    draft_created = False
    if history_id is None:
        history_id = histories.create_draft(
            user["id"], is_guest=user["username"] == "guest"
        )
        draft_created = True
    elif histories.get_raw(history_id, user["id"]) is None:
        raise ApiError(404, "history_not_found", "历史记录不存在")

    try:
        for upload in files:
            filename = _validate_filename(upload.filename or "")
            destination = paths.UPLOAD_DIR / (uuid.uuid4().hex + ".pdf")
            saved_paths.append(destination)
            _save_upload(upload, destination)
            try:
                with pymupdf.open(destination) as pdf:
                    page_count = pdf.page_count
            except Exception:
                page_count = None
            created.append(
                documents.create_document(
                    user["id"], history_id, filename, str(destination), page_count
                )
            )
        for doc in created:
            workers.enqueue_parse(doc["id"])
        created = [documents.get_document(doc["id"]) or doc for doc in created]
    except Exception:
        for doc in created:
            documents.delete_document(doc["id"])
        if draft_created:
            histories.delete_history_internal(history_id)
        for path in saved_paths:
            path.unlink(missing_ok=True)
        raise
    finally:
        for upload in files:
            await upload.close()

    return {
        "history_id": history_id,
        "documents": [documents.public_document(doc) for doc in created],
    }


@router.get("")
def list_documents(
    history_id: int | None = None, user: dict = Depends(require_user)
) -> dict:
    return {"documents": documents.list_documents(user["id"], history_id)}


@router.get("/{doc_id}/text")
def get_text(
    doc_id: int,
    offset: int = 0,
    limit: int = 20000,
    user: dict = Depends(require_user),
) -> dict:
    doc = documents.get_document(doc_id, user["id"])
    if doc is None:
        raise ApiError(404, "document_not_found", "文档不存在")
    try:
        text = documents.read_markdown(doc)
    except OSError:
        raise ApiError(409, "document_not_parsed", "文档尚未解析完成")
    offset = max(0, min(offset, len(text)))
    limit = max(1, min(limit, 50000))
    return {
        "text": text[offset : offset + limit],
        "offset": offset,
        "total": len(text),
        "has_more": offset + limit < len(text),
    }


@router.get("/{doc_id}/assets/{name}")
def get_asset(doc_id: int, name: str, user: dict = Depends(require_user)) -> FileResponse:
    if documents.get_document(doc_id, user["id"]) is None:
        raise ApiError(404, "document_not_found", "文档不存在")
    safe_name = Path(name).name
    if safe_name != name:
        raise ApiError(400, "invalid_asset", "非法的资源名")
    asset = paths.PARSED_DIR / str(doc_id) / "images" / safe_name
    if not asset.is_file():
        raise ApiError(404, "asset_not_found", "资源不存在")
    return FileResponse(asset)
