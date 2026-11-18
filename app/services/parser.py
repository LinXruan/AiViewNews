"""mineru CLI adapter. Never imports mineru, only runs its executable."""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from pathlib import Path

from .. import config, paths
from . import documents, histories

PARSE_TIMEOUT_SECONDS = 600
SERVER_START_TIMEOUT_SECONDS = 120
_PAGE_MARKER = re.compile(r"<!--\s*page\s+(\d+)\s+of\s+(\d+)\s*-->")
_IMAGE_REF = re.compile(r"\]\(images/([^)\s]+)\)")


class ParserError(RuntimeError):
    pass


def _command_prefix() -> list[str]:
    configured = config.mineru_cmd()
    if configured:
        executable = Path(configured)
    else:
        found = shutil.which("mineru")
        if not found:
            raise ParserError("未配置 MINERU_CMD，且 PATH 中找不到 mineru")
        executable = Path(found)
    if executable.name.lower().startswith("python"):
        return [str(executable), "-m", "mineru"]
    return [str(executable)]


def _kill_tree(pid: int) -> None:
    if os.name == "nt":
        subprocess.run(
            ["taskkill", "/T", "/F", "/PID", str(pid)],
            capture_output=True,
            check=False,
        )
    else:
        try:
            os.kill(pid, 9)
        except OSError:
            pass


def _run(args: list[str], timeout: int) -> subprocess.CompletedProcess:
    flags = subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0
    process = subprocess.Popen(
        args,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        creationflags=flags,
    )
    try:
        stdout, stderr = process.communicate(timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        _kill_tree(process.pid)
        process.communicate()
        raise ParserError(f"mineru 超过 {timeout} 秒未完成") from exc
    return subprocess.CompletedProcess(args, process.returncode, stdout, stderr)


def ensure_server() -> None:
    prefix = _command_prefix()
    status = _run(prefix + ["server", "status"], 30)
    if status.returncode == 0:
        return
    started = _run(prefix + ["server", "start"], SERVER_START_TIMEOUT_SECONDS)
    if started.returncode != 0:
        tail = (started.stderr or started.stdout or "").strip()[-1000:]
        raise ParserError(f"mineru 服务启动失败：{tail}")


def _run_parse(pdf_path: Path) -> str:
    prefix = _command_prefix()
    args = prefix + [
        "parse",
        str(pdf_path),
        "--pages",
        "all",
        "--tier",
        config.mineru_tier(),
        "-o",
        "-",
        "--wait",
        str(PARSE_TIMEOUT_SECONDS),
    ]
    result = _run(args, PARSE_TIMEOUT_SECONDS + 30)
    output = (result.stdout or "").strip()
    if "解析仍在进行中" in output or "解析任务 ID" in output:
        raise ParserError("mineru 解析超时，任务仍在后台运行")
    if result.returncode != 0 or not output or output.startswith("错误:"):
        tail = ((result.stderr or "") + "\n" + (result.stdout or "")).strip()[-2000:]
        raise ParserError(f"mineru 解析失败：{tail}")
    return output


def _split_pages(markdown: str) -> tuple[str, list[list[int]]]:
    """Remove mineru page markers and record each page's range in the text."""
    parts: list[str] = []
    cursor = 0
    for match in _PAGE_MARKER.finditer(markdown):
        segment = markdown[cursor:match.start()]
        if not parts and not segment.strip():
            cursor = match.end()
            continue
        parts.append(segment)
        cursor = match.end()
    tail = markdown[cursor:]
    if tail.strip() or not parts:
        parts.append(tail)

    offsets: list[list[int]] = []
    position = 0
    for part in parts:
        offsets.append([position, position + len(part)])
        position += len(part)
    return "".join(parts), offsets


def _rewrite_images(markdown: str, doc_id: int) -> str:
    return _IMAGE_REF.sub(
        lambda match: "](/api/documents/" + str(doc_id) + "/assets/" + match.group(1) + ")",
        markdown,
    )


def forget_source(pdf_path: str) -> None:
    """Remove mineru's own doclib record/cache for a source file."""
    if not pdf_path:
        return
    try:
        prefix = _command_prefix()
        _run(prefix + ["forget", pdf_path, "--no-dry-run"], 60)
    except Exception:
        pass


def probe() -> dict:
    prefix = _command_prefix()
    version = _run(prefix + ["--version"], 30)
    status = _run(prefix + ["server", "status"], 30)
    first_line = (version.stdout or version.stderr or "").strip().splitlines()
    return {
        "version": first_line[0] if first_line else "",
        "server_running": status.returncode == 0,
    }


def parse_document(doc_id: int) -> None:
    doc = documents.get_document(doc_id)
    if doc is None:
        return
    try:
        ensure_server()
        source = documents.upload_path(doc.get("stored_path"))
        if source is None:
            raise ParserError("上传的 PDF 已被清理，请重新上传")
        markdown = _run_parse(source)
        full_md, page_offsets = _split_pages(markdown)
        full_md = _rewrite_images(full_md, doc_id)
        if not full_md.strip():
            raise ParserError("mineru 未返回任何正文")

        target_dir = paths.PARSED_DIR / str(doc_id)
        target_dir.mkdir(parents=True, exist_ok=True)
        (target_dir / "images").mkdir(exist_ok=True)
        md_path = target_dir / "full.md"
        md_path.write_text(full_md, encoding="utf-8")

        page_count = doc["page_count"] or len(page_offsets)
        while len(page_offsets) < page_count:
            page_offsets.append([len(full_md), len(full_md)])
        documents.mark_parsed(
            doc_id,
            page_count,
            len(full_md),
            json.dumps(page_offsets, ensure_ascii=False),
        )
    except Exception as exc:
        documents.mark_failed(doc_id, str(exc))
    finally:
        forget_source(doc.get("stored_path") or "")
        documents.purge_pdf(doc_id)
        histories.publish_if_ready(doc["history_id"])
