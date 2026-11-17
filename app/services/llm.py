"""OpenAI-compatible JSON calls, retries and one-line audit logging."""
from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from openai import OpenAI

from .. import config, paths

MAX_RETRIES = 3
_FENCE = re.compile(r"^\s*```(?:json)?\s*|\s*```\s*$", re.IGNORECASE)
_TRAILING_COMMA = re.compile(r",\s*([}\]])")


class LlmCallError(RuntimeError):
    pass


class TruncatedOutput(LlmCallError):
    pass


@dataclass(frozen=True)
class LlmConfig:
    api_key: str
    base_url: str
    model: str
    temperature: float
    timeout: float
    max_tokens: int


def snapshot() -> LlmConfig:
    api_key = config.llm_api_key()
    if not api_key:
        raise LlmCallError("未配置大模型 API Key，请在 .env 或系统设置中填写")
    return LlmConfig(
        api_key=api_key,
        base_url=config.llm_base_url(),
        model=config.llm_model(),
        temperature=config.llm_temperature(),
        timeout=config.llm_timeout(),
        max_tokens=4096,
    )


def _sanitize(message: str, cfg: LlmConfig) -> str:
    cleaned = message.replace(cfg.api_key, "***") if cfg.api_key else message
    return cleaned.replace(cfg.base_url, "***")


def ping() -> dict:
    cfg = snapshot()
    client = OpenAI(api_key=cfg.api_key, base_url=cfg.base_url, timeout=cfg.timeout, max_retries=0)
    started = time.time()
    response = client.chat.completions.create(
        model=cfg.model,
        messages=[{"role": "user", "content": "Return {\"ok\": true} as JSON."}],
        response_format={"type": "json_object"},
        temperature=0,
        max_tokens=20,
    )
    return {
        "model": response.model,
        "latency_ms": int((time.time() - started) * 1000),
    }


def _extract_json(text: str) -> dict:
    value = text.strip().lstrip("\ufeff")
    value = _FENCE.sub("", value).strip()
    start = value.find("{")
    end = value.rfind("}")
    if start == -1 or end <= start:
        raise ValueError("模型输出中没有 JSON 对象")
    candidate = value[start : end + 1]
    for attempt in (candidate, _TRAILING_COMMA.sub(r"\1", candidate)):
        for variant in (
            attempt,
            attempt.replace("\u201c", '"').replace("\u201d", '"'),
        ):
            try:
                data = json.loads(variant, strict=False)
            except json.JSONDecodeError:
                continue
            if isinstance(data, dict):
                return data
    raise ValueError("模型输出的 JSON 无法解析")


def _log(record: dict) -> None:
    paths.ensure_dirs()
    path = Path(paths.LOG_DIR) / "llm.jsonl"
    record["at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def _retryable(exc: Exception) -> bool:
    status = getattr(exc, "status_code", None)
    if status is None:
        return True
    return status == 429 or status >= 500


def call_json(
    cfg: LlmConfig,
    messages: list[dict],
    *,
    task_id: int,
    chunk_index: int,
    attempt: int,
    temperature: float | None = None,
) -> dict:
    client = OpenAI(
        api_key=cfg.api_key,
        base_url=cfg.base_url,
        timeout=cfg.timeout,
        max_retries=0,
    )
    prompt_chars = sum(len(message["content"]) for message in messages)
    last_error = ""
    for retry in range(MAX_RETRIES):
        started = time.time()
        try:
            response = client.chat.completions.create(
                model=cfg.model,
                messages=messages,
                response_format={"type": "json_object"},
                temperature=cfg.temperature if temperature is None else temperature,
                max_tokens=cfg.max_tokens,
            )
            choice = response.choices[0]
            content = choice.message.content or ""
            latency = int((time.time() - started) * 1000)
            finish = choice.finish_reason
            _log(
                {
                    "task_id": task_id,
                    "chunk": chunk_index,
                    "attempt": attempt,
                    "retry": retry,
                    "model": cfg.model,
                    "prompt_chars": prompt_chars,
                    "output_chars": len(content),
                    "latency_ms": latency,
                    "finish_reason": finish,
                    "ok": finish != "length",
                    "error": "" if finish != "length" else "truncated",
                }
            )
            if finish == "length":
                raise TruncatedOutput("模型输出被 max_tokens 截断")
            if not content.strip():
                raise LlmCallError("模型返回空内容")
            return _extract_json(content)
        except TruncatedOutput:
            raise
        except Exception as exc:
            last_error = _sanitize(str(exc), cfg)
            latency = int((time.time() - started) * 1000)
            _log(
                {
                    "task_id": task_id,
                    "chunk": chunk_index,
                    "attempt": attempt,
                    "retry": retry,
                    "model": cfg.model,
                    "prompt_chars": prompt_chars,
                    "output_chars": 0,
                    "latency_ms": latency,
                    "finish_reason": None,
                    "ok": False,
                    "error": type(exc).__name__,
                }
            )
            if retry + 1 >= MAX_RETRIES or not _retryable(exc):
                break
            time.sleep(2 ** retry)
    raise LlmCallError(last_error or "大模型调用失败")
