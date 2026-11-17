-- SQLite schema. Keep in sync with PLAN/PLAN_1.md section 2.
CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    username      TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role          TEXT NOT NULL DEFAULT 'user' CHECK (role IN ('user', 'admin')),
    created_at    TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS documents (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id      INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    filename     TEXT NOT NULL,
    stored_path  TEXT NOT NULL,
    md_path      TEXT,
    page_count   INTEGER,
    char_count   INTEGER,
    page_offsets TEXT,
    parse_status TEXT NOT NULL DEFAULT 'pending'
                 CHECK (parse_status IN ('pending', 'parsing', 'parsed', 'failed')),
    parse_error  TEXT,
    created_at   TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS tasks (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id          INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    query            TEXT NOT NULL,
    status           TEXT NOT NULL DEFAULT 'pending'
                     CHECK (status IN ('pending', 'analyzing', 'done', 'partial', 'failed')),
    timeline_summary TEXT,
    error            TEXT,
    created_at       TEXT NOT NULL,
    finished_at      TEXT
);

CREATE TABLE IF NOT EXISTS task_documents (
    task_id INTEGER NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    doc_id  INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    PRIMARY KEY (task_id, doc_id)
);

CREATE TABLE IF NOT EXISTS events (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id       INTEGER NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    doc_id        INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    eid           TEXT NOT NULL,
    event_text    TEXT NOT NULL,
    event_time    TEXT,
    page          INTEGER,
    source_offset TEXT,
    source_quote  TEXT,
    order_index   INTEGER NOT NULL DEFAULT 0,
    created_at    TEXT NOT NULL,
    UNIQUE (task_id, eid)
);

CREATE TABLE IF NOT EXISTS reports (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id    INTEGER NOT NULL UNIQUE REFERENCES tasks(id) ON DELETE CASCADE,
    title      TEXT NOT NULL,
    content_md TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    edited_at  TEXT
);

CREATE TABLE IF NOT EXISTS settings (
    key        TEXT PRIMARY KEY,
    value      TEXT,
    updated_at TEXT,
    updated_by INTEGER REFERENCES users(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_documents_user ON documents(user_id);
CREATE INDEX IF NOT EXISTS idx_tasks_user ON tasks(user_id);
CREATE INDEX IF NOT EXISTS idx_events_task ON events(task_id);
CREATE INDEX IF NOT EXISTS idx_events_doc ON events(doc_id);
CREATE INDEX IF NOT EXISTS idx_task_documents_doc ON task_documents(doc_id);
