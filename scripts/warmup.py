"""Pre-demo warmup: config, database, memory, mineru and the LLM."""
from __future__ import annotations

import ctypes
import os
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pymupdf

from app import config, paths
from app.db import get_conn, init_db
from app.services import llm, parser, settings

PASS = "PASS"
FAIL = "FAIL"
WARN = "WARN"


def _memory_gb() -> float | None:
    if sys.platform == "win32":
        class MemoryStatus(ctypes.Structure):
            _fields_ = [
                ("length", ctypes.c_ulong),
                ("memory_load", ctypes.c_ulong),
                ("total_phys", ctypes.c_ulonglong),
                ("avail_phys", ctypes.c_ulonglong),
                ("total_page_file", ctypes.c_ulonglong),
                ("avail_page_file", ctypes.c_ulonglong),
                ("total_virtual", ctypes.c_ulonglong),
                ("avail_virtual", ctypes.c_ulonglong),
                ("avail_extended_virtual", ctypes.c_ulonglong),
            ]

        status = MemoryStatus()
        status.length = ctypes.sizeof(MemoryStatus)
        if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
            return round(status.avail_phys / (1024 ** 3), 1)
        return None
    try:
        return round(
            os.sysconf("SC_AVPHYS_PAGES") * os.sysconf("SC_PAGE_SIZE") / (1024 ** 3),
            1,
        )
    except (OSError, ValueError, AttributeError):
        return None


def _step(name: str, function) -> bool:
    started = time.time()
    try:
        detail = function()
        elapsed = int((time.time() - started) * 1000)
        print(f"[{PASS}] {name} ({elapsed}ms) {detail}")
        return True
    except Exception as exc:  # noqa: BLE001
        elapsed = int((time.time() - started) * 1000)
        print(f"[{FAIL}] {name} ({elapsed}ms) {exc}")
        return False


def check_config() -> str:
    paths.ensure_dirs()
    init_db()
    data = settings.public()
    return (
        "model=" + data["llm"]["model"]
        + ", key_set=" + str(data["llm"]["api_key_set"])
        + ", tier=" + data["parse"]["tier"]
    )


def check_database() -> str:
    row = get_conn().execute("PRAGMA quick_check").fetchone()
    if row is None or row[0] != "ok":
        raise RuntimeError("SQLite quick_check 未通过")
    return str(paths.DB_PATH)


def check_memory() -> str:
    available = _memory_gb()
    if available is None:
        return "无法读取，跳过（不阻塞）"
    if available < 2.5:
        raise RuntimeError(f"可用内存仅 {available}GB，请关闭大程序后重试")
    if available < 6:
        print(f"[{WARN}] 可用内存 {available}GB，低于 6GB 建议值；flash 档仍可运行")
    return f"{available}GB 可用"


def check_mineru() -> str:
    if not config.mineru_cmd():
        raise RuntimeError("MINERU_CMD 为空，请在系统设置中填写")
    if not Path(config.mineru_cmd()).is_file():
        raise RuntimeError("MINERU_CMD 指向的文件不存在")
    return str(parser.probe())


def _sample_pdf() -> Path:
    handle = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
    handle.close()
    document = pymupdf.open()
    page = document.new_page(width=595, height=842)
    page.insert_text((72, 90), "Warmup sample news", fontsize=18)
    page.insert_textbox(
        pymupdf.Rect(72, 130, 520, 600),
        "On 5 March 2024 the energy agency reported that oil prices fell by 12 percent. "
        "Analysts expect the market to remain volatile.",
        fontsize=12,
    )
    document.save(handle.name)
    document.close()
    return Path(handle.name)


def check_parse() -> str:
    sample = _sample_pdf()
    try:
        parser.ensure_server()
        output = parser._run_parse(sample)
        if not output.strip():
            raise RuntimeError("mineru 未返回文本")
        return f"{len(output)} chars"
    finally:
        sample.unlink(missing_ok=True)


def check_llm() -> str:
    result = llm.ping()
    return result["model"] + " / " + str(result["latency_ms"]) + "ms"


def main() -> int:
    print("AiViewNews warmup")
    checks = [
        ("config", check_config),
        ("database", check_database),
        ("memory", check_memory),
        ("mineru", check_mineru),
        ("parse", check_parse),
        ("llm", check_llm),
    ]
    results = [_step(name, function) for name, function in checks]
    if all(results):
        print("ALL GREEN")
        return 0
    print("WARMUP FAILED")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
