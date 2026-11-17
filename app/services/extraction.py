"""Per-chunk extraction with validation, repair and source verification."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date

from pydantic import ValidationError

from ..models import ExtractedEvent
from . import llm, prompts, textmatch
from .chunker import Chunk

_FULL_DATE = re.compile(r"^(\d{4})[\u5e74./-](\d{1,2})[\u6708./-](\d{1,2})\u65e5?$")
_MONTH = re.compile(r"^(\d{4})[\u5e74./-](\d{1,2})\u6708?$")
_ISO_PREFIX = re.compile(r"^(\d{4}-\d{2}-\d{2})[T ].*$")


@dataclass
class ChunkOutcome:
    events: list[dict] = field(default_factory=list)
    dropped: int = 0
    calls: int = 0
    error: str = ""


def normalize_event_time(raw: str | None) -> str | None:
    if not raw:
        return None
    value = raw.strip()
    iso = _ISO_PREFIX.match(value)
    if iso:
        value = iso.group(1)
    full = _FULL_DATE.match(value)
    if full:
        year, month, day = (int(part) for part in full.groups())
        try:
            return date(year, month, day).isoformat()
        except ValueError:
            return None
    month = _MONTH.match(value)
    if month:
        year, month_number = (int(part) for part in month.groups())
        try:
            return date(year, month_number, 1).isoformat()
        except ValueError:
            return None
    return None


def _error_text(exc: ValidationError) -> str:
    first = exc.errors()[0]
    location = ".".join(str(part) for part in first.get("loc", ()))
    return location + ": " + str(first.get("msg", "invalid"))


def _validate_item(item) -> tuple[dict | None, str]:
    if not isinstance(item, dict):
        return None, "条目不是 JSON 对象"
    try:
        event = ExtractedEvent.model_validate(item)
    except ValidationError as exc:
        return None, _error_text(exc)
    text = event.event_text.strip()
    quote = event.source_quote.strip()
    if not text or not quote:
        return None, "event_text 或 source_quote 为空"
    return {
        "event_text": text,
        "event_time": normalize_event_time(event.event_time),
        "source_quote": quote,
    }, ""


def _validate_batch(data: dict) -> tuple[list[dict], list, list[str]]:
    items = data.get("events")
    if not isinstance(items, list):
        raise ValueError("JSON 中缺少 events 数组")
    good: list[dict] = []
    bad: list = []
    errors: list[str] = []
    for item in items:
        event, error = _validate_item(item)
        if event is None:
            bad.append(item)
            errors.append(error)
        else:
            good.append(event)
    return good, bad, errors


def _attach_sources(
    events: list[dict],
    document: textmatch.NormalizedDocument,
    chunk: Chunk,
    page_offsets: list[list[int]],
    outcome: ChunkOutcome,
) -> None:
    for event in events:
        located = textmatch.locate_quote(
            document, chunk.text, chunk.start, event["source_quote"]
        )
        if located is None:
            outcome.dropped += 1
            continue
        start, end = located
        event["source_offset"] = {"start": start, "end": end}
        event["page"] = textmatch.page_for_offset(page_offsets, start)
        outcome.events.append(event)


def _extract_once(
    cfg: llm.LlmConfig,
    task_id: int,
    query: str,
    chunk: Chunk,
    chunk_index: int,
    document: textmatch.NormalizedDocument,
    page_offsets: list[list[int]],
    outcome: ChunkOutcome,
) -> None:
    data = llm.call_json(
        cfg,
        prompts.extraction_messages(query, chunk.text),
        task_id=task_id,
        chunk_index=chunk_index,
        attempt=0,
    )
    outcome.calls += 1
    good, bad, errors = _validate_batch(data)
    _attach_sources(good, document, chunk, page_offsets, outcome)

    for attempt in range(1, 3):
        if not bad:
            break
        repaired = llm.call_json(
            cfg,
            prompts.repair_messages(query, chunk.text, bad, errors),
            task_id=task_id,
            chunk_index=chunk_index,
            attempt=attempt,
            temperature=0,
        )
        outcome.calls += 1
        fixed, bad, errors = _validate_batch(repaired)
        _attach_sources(fixed, document, chunk, page_offsets, outcome)


def extract_chunk(
    cfg: llm.LlmConfig,
    task_id: int,
    query: str,
    chunk: Chunk,
    chunk_index: int,
    document: textmatch.NormalizedDocument,
    page_offsets: list[list[int]],
) -> ChunkOutcome:
    outcome = ChunkOutcome()
    try:
        _extract_once(
            cfg, task_id, query, chunk, chunk_index, document, page_offsets, outcome
        )
    except llm.TruncatedOutput:
        if len(chunk.text) < 400:
            outcome.error = "模型输出被截断且无法再拆分"
            return outcome
        middle = len(chunk.text) // 2
        cut = chunk.text.rfind("\n", 0, middle)
        if cut < 100:
            cut = middle
        left = Chunk(chunk.text[:cut], chunk.start, chunk.start + cut)
        right = Chunk(chunk.text[cut:], chunk.start + cut, chunk.end)
        for index, part in enumerate((left, right)):
            try:
                _extract_once(
                    cfg,
                    task_id,
                    query,
                    part,
                    chunk_index * 10 + index,
                    document,
                    page_offsets,
                    outcome,
                )
            except Exception as exc:
                outcome.error = str(exc)
    except Exception as exc:
        outcome.error = str(exc)
    return outcome
