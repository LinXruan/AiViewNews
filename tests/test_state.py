from __future__ import annotations

from app.db import get_conn, reset_interrupted_statuses
from app.services import histories


def test_eight_tables_exist():
    rows = get_conn().execute(
        "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
    ).fetchall()
    names = {row["name"] for row in rows}
    assert {
        "users",
        "histories",
        "documents",
        "tasks",
        "task_documents",
        "events",
        "reports",
        "settings",
    }.issubset(names)


def test_restart_resets_interrupted_statuses():
    conn = get_conn()
    history_id = histories.create_draft(1, is_guest=False)
    with conn:
        cursor = conn.execute(
            "INSERT INTO documents "
            "(user_id, history_id, filename, stored_path, parse_status, created_at) "
            "VALUES (1, ?, 'reset.pdf', 'x.pdf', 'parsing', '2026-11-17T00:00:00+00:00')",
            (history_id,),
        )
        doc_id = cursor.lastrowid
        task = conn.execute(
            "INSERT INTO tasks (user_id, history_id, query, status, created_at) "
            "VALUES (1, ?, 'reset query', 'analyzing', '2026-11-17T00:00:00+00:00')",
            (history_id,),
        )
        task_id = task.lastrowid

    reset_interrupted_statuses()
    assert conn.execute(
        "SELECT parse_status FROM documents WHERE id = ?", (doc_id,)
    ).fetchone()[0] == "pending"
    assert conn.execute(
        "SELECT status FROM tasks WHERE id = ?", (task_id,)
    ).fetchone()[0] == "pending"

    with conn:
        conn.execute("DELETE FROM histories WHERE id = ?", (history_id,))


def test_task_creation_rejects_unparsed_document(admin_client):
    conn = get_conn()
    admin_id = admin_client.get("/api/me").json()["id"]
    history_id = histories.create_draft(admin_id, is_guest=False)
    with conn:
        conn.execute(
            "INSERT INTO documents "
            "(user_id, history_id, filename, stored_path, parse_status, created_at) "
            "VALUES (?, ?, 'unparsed.pdf', 'x.pdf', 'pending', '2026-11-17T00:00:00+00:00')",
            (admin_id, history_id),
        )
        conn.execute("UPDATE histories SET status = 'ready' WHERE id = ?", (history_id,))
    response = admin_client.post(
        "/api/tasks", json={"history_id": history_id, "query": "测试"}
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "no_parsed_document"
    with conn:
        conn.execute("DELETE FROM histories WHERE id = ?", (history_id,))
