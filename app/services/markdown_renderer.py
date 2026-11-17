"""Small, dependency-free markdown renderer with HTML escaping."""
from __future__ import annotations

import html
import re

_HEADING = re.compile(r"^(#{1,4})\s+(.*)$")
_BULLET = re.compile(r"^[-*+]\s+(.*)$")
_ORDERED = re.compile(r"^\d+[.)]\s+(.*)$")
_BOLD = re.compile(r"\*\*(.+?)\*\*")
_ITALIC = re.compile(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)")
_CODE = re.compile(r"`([^`]+)`")
_TABLE_DIVIDER = re.compile(r"^\s*\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)+\|?\s*$")


def _inline(text: str) -> str:
    value = html.escape(text, quote=False)
    value = _BOLD.sub(r"<strong>\1</strong>", value)
    value = _ITALIC.sub(r"<em>\1</em>", value)
    value = _CODE.sub(r"<code>\1</code>", value)
    return value


def _cells(line: str) -> list[str]:
    stripped = line.strip().strip("|")
    return [cell.strip() for cell in stripped.split("|")]


def render(markdown: str) -> str:
    lines = markdown.replace("\r\n", "\n").split("\n")
    out: list[str] = []
    paragraph: list[str] = []
    list_items: list[str] = []
    list_tag = ""
    index = 0

    def flush_paragraph() -> None:
        if paragraph:
            out.append("<p>" + _inline(" ".join(paragraph)) + "</p>")
            paragraph.clear()

    def flush_list() -> None:
        nonlocal list_tag
        if list_items:
            out.append("<" + list_tag + ">" + "".join(list_items) + "</" + list_tag + ">")
            list_items.clear()
        list_tag = ""

    while index < len(lines):
        line = lines[index]
        stripped = line.strip()
        if stripped.startswith("```"):
            flush_paragraph()
            flush_list()
            index += 1
            code: list[str] = []
            while index < len(lines) and not lines[index].strip().startswith("```"):
                code.append(lines[index])
                index += 1
            out.append("<pre><code>" + html.escape("\n".join(code)) + "</code></pre>")
            index += 1
            continue
        if not stripped:
            flush_paragraph()
            flush_list()
            index += 1
            continue
        heading = _HEADING.match(stripped)
        if heading:
            flush_paragraph()
            flush_list()
            level = len(heading.group(1))
            out.append("<h" + str(level) + ">" + _inline(heading.group(2)) + "</h" + str(level) + ">")
            index += 1
            continue
        if "|" in stripped and index + 1 < len(lines) and _TABLE_DIVIDER.match(lines[index + 1]):
            flush_paragraph()
            flush_list()
            header = _cells(stripped)
            index += 2
            rows: list[list[str]] = []
            while index < len(lines) and "|" in lines[index] and lines[index].strip():
                rows.append(_cells(lines[index]))
                index += 1
            table = ["<table><thead><tr>"]
            table.extend("<th>" + _inline(cell) + "</th>" for cell in header)
            table.append("</tr></thead><tbody>")
            for row in rows:
                table.append("<tr>")
                table.extend("<td>" + _inline(cell) + "</td>" for cell in row)
                table.append("</tr>")
            table.append("</tbody></table>")
            out.extend(table)
            continue
        bullet = _BULLET.match(stripped)
        ordered = _ORDERED.match(stripped)
        if bullet or ordered:
            flush_paragraph()
            tag = "ul" if bullet else "ol"
            if list_tag and list_tag != tag:
                flush_list()
            list_tag = tag
            list_items.append("<li>" + _inline((bullet or ordered).group(1)) + "</li>")
            index += 1
            continue
        if stripped.startswith(">"):
            flush_paragraph()
            flush_list()
            out.append("<blockquote>" + _inline(stripped.lstrip("> ")) + "</blockquote>")
            index += 1
            continue
        paragraph.append(stripped)
        index += 1

    flush_paragraph()
    flush_list()
    return "".join(out)
