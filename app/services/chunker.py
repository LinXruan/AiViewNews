"""Split markdown into LLM-sized chunks while keeping global offsets."""
from __future__ import annotations

import re
from dataclasses import dataclass

MAX_CHARS = 6000
OVERLAP_CHARS = 200
_HEADING = re.compile(r"^#{1,6} .*$", re.MULTILINE)


@dataclass(frozen=True)
class Chunk:
    text: str
    start: int
    end: int


def _sections(text: str) -> list[tuple[int, int]]:
    starts = [match.start() for match in _HEADING.finditer(text)]
    if not starts:
        return [(0, len(text))]
    sections: list[tuple[int, int]] = []
    if starts[0] > 0:
        sections.append((0, starts[0]))
    for index, start in enumerate(starts):
        end = starts[index + 1] if index + 1 < len(starts) else len(text)
        sections.append((start, end))
    return sections


def _split_long(text: str, start: int, end: int) -> list[Chunk]:
    chunks: list[Chunk] = []
    position = start
    while position < end:
        hard_end = min(position + MAX_CHARS, end)
        if hard_end < end:
            cut = text.rfind("\n\n", position + MAX_CHARS // 2, hard_end)
            if cut == -1:
                cut = text.rfind("\n", position + MAX_CHARS // 2, hard_end)
            if cut == -1:
                cut = hard_end
        else:
            cut = end
        chunks.append(Chunk(text[position:cut], position, cut))
        if cut >= end:
            break
        position = max(cut - OVERLAP_CHARS, position + 1)
    return chunks


def chunk_markdown(text: str) -> list[Chunk]:
    if len(text) <= MAX_CHARS:
        return [Chunk(text, 0, len(text))] if text.strip() else []
    chunks: list[Chunk] = []
    for start, end in _sections(text):
        if not text[start:end].strip():
            continue
        if end - start <= MAX_CHARS:
            chunks.append(Chunk(text[start:end], start, end))
        else:
            chunks.extend(_split_long(text, start, end))
    return chunks
