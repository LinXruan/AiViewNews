from __future__ import annotations

from app import paths
from app.db import get_conn
from app.services import cleanup, histories


def _parsed_doc(history_id: int, text: str) -> int:
    conn = get_conn()
    with conn:
        cursor = conn.execute(
            "INSERT INTO documents "
            "(user_id, history_id, filename, stored_path, parse_status, created_at) "
            "VALUES (1, ?, 'source.pdf', NULL, 'parsed', '2026-11-17T00:00:00+00:00')",
            (history_id,),
        )
        doc_id = cursor.lastrowid
    target = paths.PARSED_DIR / str(doc_id)
    target.mkdir(parents=True, exist_ok=True)
    (target / "full.md").write_text(text, encoding="utf-8")
    with conn:
        conn.execute(
            "UPDATE documents SET page_count = 1, char_count = ?, page_offsets = ? "
            "WHERE id = ?",
            (len(text), "[[0, 10]]", doc_id),
        )
    return doc_id


def test_read_markdown_ignores_stored_paths():
    """PLAN 17: parsed text is found by id, so folder renames cannot break it."""
    from app.services import documents

    history_id = histories.create_draft(1, is_guest=False)
    doc_id = _parsed_doc(history_id, "正文内容")
    assert documents.read_markdown(doc_id) == "正文内容"
    assert documents.markdown_path(doc_id) == paths.PARSED_DIR / str(doc_id) / "full.md"
    assert documents.upload_path("C:/old/place/a.pdf") == paths.UPLOAD_DIR / "a.pdf"
    assert documents.upload_path(None) is None


def test_history_publish_title_and_search():
    history_id = histories.create_draft(1, is_guest=False)
    doc_id = _parsed_doc(history_id, "\n\n能源市场周报:油价波动\n\n正文内容")
    histories.publish_if_ready(history_id)
    history = histories.get_raw(history_id)
    assert history["status"] == "ready"
    assert history["title"] == "能源市场周报:油价波动"

    conn = get_conn()
    with conn:
        conn.execute(
            "INSERT INTO tasks (user_id, history_id, query, status, created_at) "
            "VALUES (1, ?, '航空业成本', 'done', '2026-11-17T00:00:00+00:00')",
            (history_id,),
        )
    assert any(item["id"] == history_id for item in histories.list_histories(1, "能源"))
    assert any(item["id"] == history_id for item in histories.list_histories(1, "航空"))

    histories.delete_history(history_id, 1)
    assert histories.get_raw(history_id) is None
    assert not (paths.PARSED_DIR / str(doc_id)).exists()


def test_guest_expiry_and_stale_draft_cleanup():
    expired = histories.create_draft(1, is_guest=True)
    stale = histories.create_draft(1, is_guest=False)
    conn = get_conn()
    with conn:
        conn.execute(
            "UPDATE histories SET expires_at = '2000-01-01T00:00:00+00:00' WHERE id = ?",
            (expired,),
        )
        conn.execute(
            "UPDATE histories SET created_at = '2000-01-01T00:00:00+00:00' WHERE id = ?",
            (stale,),
        )
    cleanup.cleanup_once()
    assert histories.get_raw(expired) is None
    assert histories.get_raw(stale) is None
