from __future__ import annotations

from app.db import get_conn, reset_interrupted_statuses


def test_seven_tables_exist():
    rows = get_conn().execute(
        "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
    ).fetchall()
    names = {row["name"] for row in rows}
    assert {
        "users",
        "documents",
        "tasks",
        "task_documents",
        "events",
        "reports",
        "settings",
    }.issubset(names)


def test_restart_resets_interrupted_statuses():
    conn = get_conn()
    with conn:
        cursor = conn.execute(
            "INSERT INTO documents (user_id, filename, stored_path, parse_status, created_at) "
            "VALUES (1, 'reset.pdf', 'x.pdf', 'parsing', '2026-11-17T00:00:00+00:00')"
        )
        doc_id = cursor.lastrowid
        task = conn.execute(
            "INSERT INTO tasks (user_id, query, status, created_at) "
            "VALUES (1, 'reset query', 'analyzing', '2026-11-17T00:00:00+00:00')"
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
        conn.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
        conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))


def test_task_creation_rejects_unparsed_document(admin_client):
    conn = get_conn()
    with conn:
        cursor = conn.execute(
            "INSERT INTO documents (user_id, filename, stored_path, parse_status, created_at) "
            "VALUES (1, 'unparsed.pdf', 'x.pdf', 'pending', '2026-11-17T00:00:00+00:00')"
        )
        doc_id = cursor.lastrowid
    response = admin_client.post(
        "/api/tasks", json={"doc_ids": [doc_id], "query": "测试"}
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "document_not_ready"
    with conn:
        conn.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
