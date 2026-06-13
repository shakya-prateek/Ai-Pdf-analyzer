import shutil
from pathlib import Path

from ..config import get_settings
from ..database import connect
from .vector_store import delete_document_index


class DocumentProcessingError(Exception):
    pass


def delete_document(doc_id: str, owner_id: str) -> bool:
    with connect() as connection:
        document = connection.execute(
            """SELECT stored_name, status
               FROM documents
               WHERE id = ? AND owner_id = ?""",
            (doc_id, owner_id),
        ).fetchone()
        if not document:
            return False
        if document["status"] not in {"indexed", "failed"}:
            raise DocumentProcessingError(
                "Wait for document processing to finish before deleting it"
            )
        connection.execute(
            "DELETE FROM documents WHERE id = ? AND owner_id = ?",
            (doc_id, owner_id),
        )

    delete_document_index(doc_id)
    settings = get_settings()
    storage_root = settings.storage_dir.resolve()

    original_path = Path(document["stored_name"]).resolve()
    if storage_root in original_path.parents:
        original_path.unlink(missing_ok=True)

    pages_dir = (settings.storage_dir / "pages" / doc_id).resolve()
    if storage_root in pages_dir.parents:
        shutil.rmtree(pages_dir, ignore_errors=True)
    return True
