from __future__ import annotations

from app.services import chunker, exporter, extraction, llm, markdown_renderer, textmatch


def test_extract_json_tolerates_fences_and_noise():
    assert llm._extract_json('{"events": []}') == {"events": []}
    assert llm._extract_json('\n\n```json\n{"events": []}\n```\n') == {
        "events": []
    }
    assert llm._extract_json('结果如下：{"events": [],}') == {"events": []}
    assert llm._extract_json('{“events”: []}') == {"events": []}


def test_event_time_normalization():
    assert extraction.normalize_event_time("2024年3月5日") == "2024-03-05"
    assert extraction.normalize_event_time("2024/3/5") == "2024-03-05"
    assert extraction.normalize_event_time("2024-03") == "2024-03-01"
    assert extraction.normalize_event_time("2024-03-05T10:00:00") == "2024-03-05"
    assert extraction.normalize_event_time("近日") is None
    assert extraction.normalize_event_time(None) is None


def test_chunker_limits_and_offsets():
    text = "# 标题\n\n" + ("内容" * 4000)
    chunks = chunker.chunk_markdown(text)
    assert chunks
    assert all(len(chunk.text) <= chunker.MAX_CHARS for chunk in chunks)
    assert all(chunk.start < chunk.end for chunk in chunks)
    assert chunks[0].start == 0


def test_quote_lookup_and_page_mapping():
    document = textmatch.NormalizedDocument("2024 年 3 月 5 日，能源价格下跌。")
    located = textmatch.locate_quote(
        document, "2024 年 3 月 5 日，能源价格下跌。", 0, "能源价格下跌"
    )
    assert located is not None
    start, end = located
    assert document.text  # normalized text is non-empty
    assert textmatch.page_for_offset([[0, 10], [10, 20]], 15) == 2
    assert textmatch.page_for_offset([[0, 10], [10, 20]], 0) == 1


def test_markdown_renderer_escapes_html():
    html = markdown_renderer.render("# 标题\n\n<script>alert(1)</script>\n\n- **加粗**")
    assert "<h1>标题</h1>" in html
    assert "&lt;script&gt;" in html
    assert "<script>" not in html
    assert "<strong>加粗</strong>" in html


def test_empty_docx_exports():
    data = exporter.export_docx("空报告", "")
    assert data.startswith(b"PK")
    assert exporter.safe_filename('报告/测试:1').endswith("_分析报告.docx")
