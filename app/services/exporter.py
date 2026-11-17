"""Markdown report to DOCX, with explicit East Asian fonts."""
from __future__ import annotations

import re
from io import BytesIO

from docx import Document
from docx.oxml.ns import qn
from docx.shared import Pt

FONT = "微软雅黑"
_BULLET = re.compile(r"^[-*+]\s+(.*)$")
_ORDERED = re.compile(r"^\d+[.)]\s+(.*)$")
_HEADING = re.compile(r"^(#{1,4})\s+(.*)$")
_ILLEGAL = re.compile(r'[\\/:*?"<>|]')


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


def safe_filename(query: str) -> str:
    summary = _ILLEGAL.sub("", (query or "分析报告").strip())[:40] or "分析报告"
    return summary + "_分析报告.docx"


def export_docx(title: str, content_md: str) -> bytes:
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
