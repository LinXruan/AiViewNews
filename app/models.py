"""Structured shapes the LLM must return (see PLAN/PLAN_1.md section 4)."""
from __future__ import annotations

from pydantic import BaseModel, Field


class ExtractedEvent(BaseModel):
    event_text: str = Field(min_length=1)
    event_time: str | None = None
    source_quote: str = Field(min_length=1, max_length=120)


class EventExtraction(BaseModel):
    events: list[ExtractedEvent] = Field(default_factory=list)


class TimelineSummary(BaseModel):
    timeline_summary: str = Field(min_length=1, max_length=300)


class ReportSection(BaseModel):
    heading: str = Field(min_length=1)
    content: str = Field(min_length=1)


class ReportDraft(BaseModel):
    title: str = Field(min_length=1)
    sections: list[ReportSection] = Field(default_factory=list)
