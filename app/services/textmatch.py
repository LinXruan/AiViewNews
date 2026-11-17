"""Normalized quote lookup and character-offset to page mapping."""
from __future__ import annotations

from bisect import bisect_right

_PUNCT = {
    "\u3002": ".",
    "\uff0c": ",",
    "\uff1a": ":",
    "\uff1b": ";",
    "\uff01": "!",
    "\uff1f": "?",
    "\uff08": "(",
    "\uff09": ")",
    "\u201c": '"',
    "\u201d": '"',
    "\u2018": "'",
    "\u2019": "'",
    "\uff0d": "-",
    "\u2014": "-",
    "\u2013": "-",
    "\u3001": ",",
}


def normalize_with_map(text: str) -> tuple[str, list[int]]:
    chars: list[str] = []
    mapping: list[int] = []
    for index, char in enumerate(text):
        if char.isspace():
            continue
        chars.append(_PUNCT.get(char, char.lower()))
        mapping.append(index)
    return "".join(chars), mapping


def normalize(text: str) -> str:
    return normalize_with_map(text)[0]


class NormalizedDocument:
    def __init__(self, text: str) -> None:
        self.text, self._mapping = normalize_with_map(text)

    def find(self, quote: str) -> tuple[int, int] | None:
        target = normalize(quote)
        if not target:
            return None
        position = self.text.find(target)
        if position < 0:
            return None
        start = self._mapping[position]
        end = self._mapping[position + len(target) - 1] + 1
        return start, end


def locate_quote(
    document: NormalizedDocument,
    chunk_text: str,
    chunk_start: int,
    quote: str,
) -> tuple[int, int] | None:
    local_text, local_map = normalize_with_map(chunk_text)
    target = normalize(quote)
    if target:
        position = local_text.find(target)
        if position >= 0:
            start = chunk_start + local_map[position]
            end = chunk_start + local_map[position + len(target) - 1] + 1
            return start, end
    return document.find(quote)


def page_for_offset(page_offsets: list[list[int]], offset: int) -> int | None:
    if not page_offsets:
        return None
    starts = [entry[0] for entry in page_offsets]
    index = bisect_right(starts, offset) - 1
    if index < 0:
        return 1
    start, end = page_offsets[index]
    if offset <= end:
        return index + 1
    return len(page_offsets)
