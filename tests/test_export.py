from __future__ import annotations

from io import BytesIO

from docx import Document

from app.services import exporter


def test_docx_round_trip_with_chinese_font():
    markdown = (
        "# 能源分析报告\n\n"
        "## 事件概述\n\n"
        "这是正文段落。\n\n"
        "- 第一条\n"
        "- **第二条**\n"
    )
    data = exporter.export_docx("能源分析报告", markdown)
    assert data.startswith(b"PK")
    document = Document(BytesIO(data))
    texts = [paragraph.text.strip() for paragraph in document.paragraphs]
    assert "能源分析报告" in texts
    assert "事件概述" in texts
    assert any("第一条" in text for text in texts)
    assert any("第二条" in text for text in texts)
    if exporter.pandoc_executable() is None:
        assert document.paragraphs[0].runs[0].font.name == exporter.FONT
