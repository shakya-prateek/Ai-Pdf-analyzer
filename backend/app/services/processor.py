import json
from pathlib import Path

from ..database import connect
from .classifier import classify_document
from .parser import parse_document, serialize_tables
from .vector_store import index_pages


def _status(doc_id: str, status: str, error: str | None = None) -> None:
    with connect() as connection:
        connection.execute(
            "UPDATE documents SET status = ?, error_message = ? WHERE id = ?",
            (status, error, doc_id),
        )


def process_document(doc_id: str) -> None:
    try:
        with connect() as connection:
            document = connection.execute("SELECT * FROM documents WHERE id = ?", (doc_id,)).fetchone()
        if not document:
            return
        file_path = Path(document["stored_name"])

        _status(doc_id, "parsing")
        pages = parse_document(file_path, document["file_type"], doc_id)
        readable_pages = [
            page for page in pages
            if page["text"].strip() or page.get("tables")
        ]
        if not readable_pages:
            raise ValueError(
                "No readable text was found. Upload a searchable PDF, TXT file, or a clearer scan."
            )
        with connect() as connection:
            connection.execute("DELETE FROM pages WHERE doc_id = ?", (doc_id,))
            for page in pages:
                connection.execute(
                    """INSERT INTO pages (doc_id, page_number, text, tables_json, image_path)
                       VALUES (?, ?, ?, ?, ?)""",
                    (
                        doc_id,
                        page["page_number"],
                        page["text"],
                        serialize_tables(page["tables"]),
                        page["image_path"],
                    ),
                )

        _status(doc_id, "classifying")
        full_text = "\n".join(page["text"] for page in pages)
        classification = classify_document(
            full_text,
            any(page["tables"] for page in pages),
            document["file_type"],
        )
        with connect() as connection:
            connection.execute(
                "UPDATE documents SET classification_json = ? WHERE id = ?",
                (json.dumps(classification, ensure_ascii=False), doc_id),
            )

        _status(doc_id, "indexing")
        index_pages(doc_id, document["owner_id"], document["original_name"], pages)
        _status(doc_id, "indexed")
    except Exception as exc:
        _status(doc_id, "failed", str(exc)[:500])
