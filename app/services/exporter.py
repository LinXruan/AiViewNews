"""Markdown report to DOCX: Pandoc first, python-docx as the offline fallback."""
from __future__ import annotations

import re
import shutil
import subprocess
import tempfile
from io import BytesIO
from pathlib import Path

from docx import Document
from docx.oxml.ns import qn
from docx.shared import Pt

from .. import config

FONT = "微软雅黑"
PANDOC_TIMEOUT_SECONDS = 60
_BULLET = re.compile(r"^[-*+]\s+(.*)$")
_ORDERED = re.compile(r"^\d+[.)]\s+(.*)$")
_HEADING = re.compile(r"^(#{1,4})\s+(.*)$")
_ILLEGAL = re.compile(r'[\\/:*?"<>|]')


def safe_filename(query: str) -> str:
    summary = _ILLEGAL.sub("", (query or "分析报告").strip())[:40] or "分析报告"
    return summary + "_分析报告.docx"


def _title_line(title: str) -> str:
    return "# " + (title or "分析报告").strip()


def _with_title(title: str, content_md: str) -> str:
    """Pandoc needs the title in the body; skip it when the report already has it."""
    body = content_md.strip()
    if not body:
        return _title_line(title) + "\n"
    first = body.splitlines()[0].strip()
    if first == _title_line(title):
        return body
    return _title_line(title) + "\n\n" + body


def pandoc_executable() -> str | None:
    configured = config.pandoc_cmd()
    if configured and Path(configured).is_file():
        return configured
    return shutil.which("pandoc")


def _run_pandoc(executable: str, markdown: str) -> bytes:
    handle = tempfile.NamedTemporaryFile(suffix=".docx", delete=False)
    handle.close()
    target = Path(handle.name)
    try:
        result = subprocess.run(
            [executable, "--from", "markdown", "--to", "docx", "--output", str(target)],
            input=markdown.encode("utf-8"),
            capture_output=True,
            timeout=PANDOC_TIMEOUT_SECONDS,
            check=False,
        )
        if result.returncode != 0:
            detail = result.stderr.decode("utf-8", "ignore").strip()
            raise RuntimeError(detail[:500] or "pandoc 转换失败")
        data = target.read_bytes()
        if not data:
            raise RuntimeError("pandoc 输出为空")
        return data
    finally:
        target.unlink(missing_ok=True)


def export_docx(title: str, content_md: str) -> bytes:
    executable = pandoc_executable()
    if executable:
        try:
            return _run_pandoc(executable, _with_title(title, content_md))
        except (OSError, RuntimeError, subprocess.SubprocessError):
            pass
    return _export_python_docx(title, content_md)


def _set_font(target) -> None:
    target.font.name = FONT
    rpr = target._element.get_or_add_rPr()
    rpr.get_or_add_rFonts().set(qn("w:eastAsia"), FONT)


def _add_runs(paragraph, text: str) -> None:
    parts = text.split("**")
    for index, part in enumerate(parts):
        if not part:
            continue
        run = paragraph.add_run(part)
        run.bold = index % 2 == 1
        _set_font(run)


def _add_heading(document, text: str, level: int) -> None:
    paragraph = document.add_heading(text, level=min(level, 4))
    for run in paragraph.runs:
        _set_font(run)


def _add_paragraph(document, text: str, style: str | None = None):
    paragraph = document.add_paragraph(style=style) if style else document.add_paragraph()
    _add_runs(paragraph, text)
    return paragraph


def _export_python_docx(title: str, content_md: str) -> bytes:
    document = Document()
    normal = document.styles["Normal"]
    normal.font.name = FONT
    normal.font.size = Pt(10.5)
    normal.element.get_or_add_rPr().get_or_add_rFonts().set(qn("w:eastAsia"), FONT)
    for style_name in ("Title", "Heading 1", "Heading 2", "Heading 3", "Heading 4"):
        try:
            _set_font(document.styles[style_name])
        except KeyError:
            continue

    title_paragraph = document.add_heading(title or "分析报告", 0)
    for run in title_paragraph.runs:
        _set_font(run)
    buffer: list[str] = []

    def flush() -> None:
        if buffer:
            _add_paragraph(document, " ".join(buffer))
            buffer.clear()

    for raw in content_md.replace("\r\n", "\n").split("\n"):
        line = raw.strip()
        if not line:
            flush()
            continue
        heading = _HEADING.match(line)
        if heading:
            flush()
            if len(heading.group(1)) == 1 and heading.group(2).strip() == title:
                continue
            _add_heading(document, heading.group(2).strip(), len(heading.group(1)))
            continue
        bullet = _BULLET.match(line)
        if bullet:
            flush()
            _add_paragraph(document, bullet.group(1), style="List Bullet")
            continue
        ordered = _ORDERED.match(line)
        if ordered:
            flush()
            _add_paragraph(document, ordered.group(1), style="List Number")
            continue
        if line.startswith(">"):
            flush()
            _add_paragraph(document, line.lstrip("> "))
            continue
        if line.startswith("|"):
            flush()
            _add_paragraph(document, line.strip("|").replace("|", " | "))
            continue
        buffer.append(line)
    flush()

    stream = BytesIO()
    document.save(stream)
    return stream.getvalue()
