import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Iterator

from .config import get_settings


SCHEMA = """
CREATE TABLE IF NOT EXISTS documents (
    id TEXT PRIMARY KEY,
    owner_id TEXT NOT NULL,
    original_name TEXT NOT NULL,
    stored_name TEXT NOT NULL,
    file_type TEXT NOT NULL,
    status TEXT NOT NULL,
    classification_json TEXT,
    created_at TEXT NOT NULL,
    error_message TEXT
);
CREATE TABLE IF NOT EXISTS pages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    doc_id TEXT NOT NULL,
    page_number INTEGER NOT NULL,
    text TEXT NOT NULL,
    tables_json TEXT NOT NULL DEFAULT '[]',
    image_path TEXT NOT NULL,
    UNIQUE(doc_id, page_number),
    FOREIGN KEY(doc_id) REFERENCES documents(id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS chunks (
    id TEXT PRIMARY KEY,
    owner_id TEXT NOT NULL,
    doc_id TEXT NOT NULL,
    page_number INTEGER NOT NULL,
    chunk_text TEXT NOT NULL,
    chroma_id TEXT,
    FOREIGN KEY(doc_id) REFERENCES documents(id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS chat_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    owner_id TEXT NOT NULL,
    question TEXT NOT NULL,
    answer TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_pages_doc ON pages(doc_id);
CREATE INDEX IF NOT EXISTS idx_chunks_doc ON chunks(doc_id);
"""


@contextmanager
def connect() -> Iterator[sqlite3.Connection]:
    settings = get_settings()
    settings.database_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(settings.database_path, timeout=30)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    try:
        yield connection
        connection.commit()
    finally:
        connection.close()


def init_db() -> None:
    with connect() as connection:
        connection.executescript(SCHEMA)
        _ensure_column(connection, "documents", "owner_id", "TEXT NOT NULL DEFAULT ''")
        _ensure_column(connection, "chunks", "owner_id", "TEXT NOT NULL DEFAULT ''")
        _ensure_column(connection, "chat_logs", "owner_id", "TEXT NOT NULL DEFAULT ''")
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_documents_owner ON documents(owner_id)"
        )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_chunks_owner ON chunks(owner_id)"
        )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_chat_logs_owner ON chat_logs(owner_id)"
        )


def _ensure_column(
    connection: sqlite3.Connection,
    table: str,
    column: str,
    definition: str,
) -> None:
    columns = {
        row["name"]
        for row in connection.execute(f"PRAGMA table_info({table})").fetchall()
    }
    if column not in columns:
        connection.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def row_to_document(
    row: sqlite3.Row,
    include_pages: bool = False,
    owner_id: str | None = None,
) -> dict[str, Any]:
    document = dict(row)
    document.pop("stored_name", None)
    document.pop("owner_id", None)
    raw = document.pop("classification_json", None)
    try:
        document["classification"] = json.loads(raw) if raw else None
    except json.JSONDecodeError:
        document["classification"] = None
    if include_pages:
        with connect() as connection:
            pages = connection.execute(
                """SELECT p.page_number, p.text, p.tables_json
                   FROM pages p JOIN documents d ON d.id = p.doc_id
                   WHERE p.doc_id = ? AND d.owner_id = ?
                   ORDER BY p.page_number""",
                (document["id"], owner_id or ""),
            ).fetchall()
        document["pages"] = [
            {
                "page_number": page["page_number"],
                "text": page["text"],
                "tables": json.loads(page["tables_json"] or "[]"),
                "page_image_url": f"/api/documents/{document['id']}/pages/{page['page_number']}",
            }
            for page in pages
        ]
    return document
