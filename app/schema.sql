-- SQLite schema for AiViewNews (PLAN 14). User version is managed in db.py.
CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    username      TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role          TEXT NOT NULL DEFAULT 'user' CHECK (role IN ('user', 'admin')),
    created_at    TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS histories (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id      INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title        TEXT NOT NULL DEFAULT '',
    status       TEXT NOT NULL DEFAULT 'draft'
                 CHECK (status IN ('draft', 'ready', 'failed')),
    created_at   TEXT NOT NULL,
    updated_at   TEXT NOT NULL,
    published_at TEXT,
    expires_at   TEXT
);

CREATE TABLE IF NOT EXISTS documents (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id       INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    history_id    INTEGER NOT NULL REFERENCES histories(id) ON DELETE CASCADE,
    filename      TEXT NOT NULL,
    stored_path   TEXT,
    pdf_purged_at TEXT,
    md_path       TEXT,
    page_count    INTEGER,
    char_count    INTEGER,
    page_offsets  TEXT,
    parse_status  TEXT NOT NULL DEFAULT 'pending'
                  CHECK (parse_status IN ('pending', 'parsing', 'parsed', 'failed')),
    parse_error   TEXT,
    created_at    TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS tasks (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id          INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    history_id       INTEGER NOT NULL REFERENCES histories(id) ON DELETE CASCADE,
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

CREATE INDEX IF NOT EXISTS idx_histories_user ON histories(user_id, updated_at);
CREATE INDEX IF NOT EXISTS idx_histories_expiry ON histories(expires_at);
CREATE INDEX IF NOT EXISTS idx_documents_user ON documents(user_id);
CREATE INDEX IF NOT EXISTS idx_documents_history ON documents(history_id);
CREATE INDEX IF NOT EXISTS idx_tasks_user ON tasks(user_id);
CREATE INDEX IF NOT EXISTS idx_tasks_history ON tasks(history_id);
CREATE INDEX IF NOT EXISTS idx_events_task ON events(task_id);
CREATE INDEX IF NOT EXISTS idx_events_doc ON events(doc_id);
CREATE INDEX IF NOT EXISTS idx_task_documents_doc ON task_documents(doc_id);
