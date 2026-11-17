"""Task orchestration: extract, deduplicate, summarize and write the report."""
from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

from ..db import get_conn
from ..models import ReportDraft, TimelineSummary
from . import chunker, documents, extraction, llm, prompts, textmatch

MAX_CALLS_PER_TASK = 60
MAX_EVENTS_FOR_REPORT = 20
REPORT_HEADINGS = ["事件概述", "关键节点", "各方立场", "影响分析", "趋势预测", "不确定性说明"]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def mark_analyzing(task_id: int) -> None:
    conn = get_conn()
    with conn:
        conn.execute(
            "UPDATE tasks SET status = 'analyzing', error = NULL, finished_at = NULL "
            "WHERE id = ?",
            (task_id,),
        )
        conn.execute("DELETE FROM events WHERE task_id = ?", (task_id,))


def _load_task(task_id: int) -> dict | None:
    row = get_conn().execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    return dict(row) if row else None


def _load_documents(task_id: int) -> list[dict]:
    rows = get_conn().execute(
        "SELECT d.* FROM documents d JOIN task_documents td ON td.doc_id = d.id "
        "WHERE td.task_id = ? ORDER BY d.id",
        (task_id,),
    ).fetchall()
    return [dict(row) for row in rows]


def _dedupe(events: list[dict]) -> list[dict]:
    seen: set[str] = set()
    merged: list[dict] = []
    for event in events:
        key = textmatch.normalize(event["event_text"]) + "|" + (
            event["event_time"] or ""
        )
        if key in seen:
            continue
        seen.add(key)
        merged.append(event)
    merged.sort(
        key=lambda item: (
            item["event_time"] is None,
            item["event_time"] or "",
            item["source_offset"]["start"] if item.get("source_offset") else 10 ** 9,
        )
    )
    for index, event in enumerate(merged):
        event["order_index"] = index
    return merged


def _collect_events(
    cfg: llm.LlmConfig, task_id: int, query: str, docs: list[dict]
) -> tuple[list[dict], dict]:
    jobs: list[tuple[dict, Chunk, int, textmatch.NormalizedDocument, list]] = []
    failed_chunks = 0
    for doc in docs:
        try:
            text = documents.read_markdown(doc)
        except OSError:
            failed_chunks += 1
            continue
        normalized = textmatch.NormalizedDocument(text)
        offsets = json.loads(doc.get("page_offsets") or "[]")
        chunks = chunker.chunk_markdown(text)
        for index, chunk in enumerate(chunks):
            jobs.append((doc, chunk, index, normalized, offsets))
        if not chunks:
            failed_chunks += 1

    budget = min(MAX_CALLS_PER_TASK, 8 * max(len(docs), 1))
    selected = jobs[:budget]
    skipped = len(jobs) - len(selected)
    results = []
    with ThreadPoolExecutor(max_workers=4, thread_name_prefix="llm") as pool:
        futures = [
            pool.submit(
                extraction.extract_chunk,
                cfg,
                task_id,
                query,
                chunk,
                index,
                normalized,
                offsets,
            )
            for doc, chunk, index, normalized, offsets in selected
        ]
        for future in futures:
            results.append(future.result())

    events: list[dict] = []
    dropped = 0
    for (doc, chunk, index, _, _), outcome in zip(selected, results):
        if outcome.error:
            failed_chunks += 1
        dropped += outcome.dropped
        for position, event in enumerate(outcome.events):
            event["doc_id"] = doc["id"]
            event["eid"] = str(doc["id"]) + "-" + str(index) + "-" + str(position)
            events.append(event)

    stats = {
        "chunks": len(jobs),
        "failed_chunks": failed_chunks,
        "skipped_chunks": skipped,
        "dropped_quotes": dropped,
    }
    return _dedupe(events), stats


def _save_events(task_id: int, events: list[dict]) -> None:
    conn = get_conn()
    with conn:
        conn.execute("DELETE FROM events WHERE task_id = ?", (task_id,))
        conn.executemany(
            "INSERT INTO events (task_id, doc_id, eid, event_text, event_time, page, "
            "source_offset, source_quote, order_index, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [
                (
                    task_id,
                    event["doc_id"],
                    event["eid"],
                    event["event_text"],
                    event["event_time"],
                    event["page"],
                    json.dumps(event["source_offset"], ensure_ascii=False),
                    event["source_quote"],
                    event["order_index"],
                    _now(),
                )
                for event in events
            ],
        )


def _simple_events(events: list[dict]) -> list[dict]:
    if len(events) > 40:
        step = len(events) / MAX_EVENTS_FOR_REPORT
        sampled = [events[int(index * step)] for index in range(MAX_EVENTS_FOR_REPORT)]
    else:
        sampled = events[:MAX_EVENTS_FOR_REPORT]
    return [{"event_time": event.get("event_time"), "event_text": event["event_text"]} for event in sampled]


def _fallback_summary(events: list[dict]) -> str:
    dated = [event["event_time"] for event in events if event.get("event_time")]
    if dated:
        return (
            "共抽取 " + str(len(events)) + " 条相关事件，时间范围为 "
            + min(dated) + " 至 " + max(dated) + "。"
        )
    return "共抽取 " + str(len(events)) + " 条相关事件，均未标注具体日期。"


def _timeline_summary(cfg: llm.LlmConfig, task_id: int, events: list[dict]) -> tuple[str, bool]:
    try:
        data = llm.call_json(
            cfg,
            prompts.timeline_messages(_simple_events(events)),
            task_id=task_id,
            chunk_index=-1,
            attempt=0,
        )
        return TimelineSummary.model_validate(data).timeline_summary, True
    except Exception:
        return _fallback_summary(events), False


def _report_markdown(draft: ReportDraft) -> str:
    lines = ["# " + draft.title, ""]
    sections = draft.sections
    order = {heading: index for index, heading in enumerate(REPORT_HEADINGS)}
    sections = sorted(sections, key=lambda section: order.get(section.heading, 99))
    for section in sections:
        lines.extend(["## " + section.heading, "", section.content, ""])
    return "\n".join(lines).strip() + "\n"


def _generate_report(cfg: llm.LlmConfig, task_id: int, query: str, events: list[dict]) -> tuple[bool, str]:
    existing = get_conn().execute(
        "SELECT id FROM reports WHERE task_id = ?", (task_id,)
    ).fetchone()
    if existing:
        return True, ""
    try:
        data = llm.call_json(
            cfg,
            prompts.report_messages(query, _simple_events(events)),
            task_id=task_id,
            chunk_index=-1,
            attempt=0,
        )
        draft = ReportDraft.model_validate(data)
        conn = get_conn()
        with conn:
            conn.execute(
                "INSERT INTO reports (task_id, title, content_md, created_at) "
                "VALUES (?, ?, ?, ?) ON CONFLICT(task_id) DO NOTHING",
                (task_id, draft.title, _report_markdown(draft), _now()),
            )
        return True, ""
    except Exception as exc:
        return False, "报告生成失败：" + str(exc)[:300]


def _finish(task_id: int, status: str, summary: str, note: str) -> None:
    conn = get_conn()
    with conn:
        conn.execute(
            "UPDATE tasks SET status = ?, timeline_summary = ?, error = ?, finished_at = ? "
            "WHERE id = ?",
            (status, summary, note or None, _now(), task_id),
        )


def analyze_task(task_id: int) -> None:
    task = _load_task(task_id)
    if task is None:
        return
    try:
        cfg = llm.snapshot()
        docs = _load_documents(task_id)
        if not docs:
            raise RuntimeError("任务没有关联文档")
        events, stats = _collect_events(cfg, task_id, task["query"], docs)
        _save_events(task_id, events)

        summary = ""
        report_ok = False
        report_error = ""
        if events:
            summary, summary_ok = _timeline_summary(cfg, task_id, events)
            report_ok, report_error = _generate_report(cfg, task_id, task["query"], events)
        else:
            summary_ok = True

        notes = []
        if stats["failed_chunks"]:
            notes.append(str(stats["failed_chunks"]) + " 个分块失败")
        if stats["skipped_chunks"]:
            notes.append(str(stats["skipped_chunks"]) + " 个分块超出调用预算")
        if stats["dropped_quotes"]:
            notes.append(str(stats["dropped_quotes"]) + " 条引用未在原文中找到")
        if not summary_ok:
            notes.append("时间线摘要已降级")
        if report_error:
            notes.append(report_error)

        if not events:
            if stats["chunks"] and stats["failed_chunks"] >= stats["chunks"]:
                _finish(task_id, "failed", summary, "；".join(notes) or "所有分块分析失败")
            else:
                _finish(task_id, "done", summary, "；".join(notes))
            return
        status = "partial" if (stats["failed_chunks"] or stats["skipped_chunks"] or not report_ok) else "done"
        _finish(task_id, status, summary, "；".join(notes))
    except Exception as exc:
        _finish(task_id, "failed", "", str(exc)[:1000])
