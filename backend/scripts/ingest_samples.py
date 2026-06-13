import sys
import uuid
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from app.config import get_settings  # noqa: E402
from app.auth import LOCAL_WORKSPACE_ID, workspace_id_from_token  # noqa: E402
from app.database import connect, init_db, now_iso  # noqa: E402
from app.services.processor import process_document  # noqa: E402


def main() -> None:
    settings = get_settings()
    if settings.single_user_mode:
        owner_id = LOCAL_WORKSPACE_ID
    elif settings.workspace_access_tokens:
        owner_id = workspace_id_from_token(settings.workspace_access_tokens[0])
    else:
        raise SystemExit("Set WORKSPACE_ACCESS_TOKENS before ingesting samples.")
    init_db()
    originals = settings.storage_dir / "originals"
    originals.mkdir(parents=True, exist_ok=True)
    samples = BACKEND_DIR / "sample_documents"

    for source in sorted(samples.glob("*.txt")):
        with connect() as connection:
            existing = connection.execute(
                """SELECT id, status FROM documents
                   WHERE original_name = ? AND owner_id = ?""",
                (source.name, owner_id),
            ).fetchone()
        if existing:
            print(f"Skipping {source.name}: already {existing['status']}")
            continue

        doc_id = str(uuid.uuid4())
        destination = originals / f"{doc_id}.txt"
        destination.write_bytes(source.read_bytes())
        with connect() as connection:
            connection.execute(
                """INSERT INTO documents
                   (id, owner_id, original_name, stored_name, file_type, status, created_at)
                   VALUES (?, ?, ?, ?, 'txt', 'uploaded', ?)""",
                (doc_id, owner_id, source.name, str(destination), now_iso()),
            )
        print(f"Ingesting {source.name}...")
        process_document(doc_id)
        with connect() as connection:
            result = connection.execute(
                "SELECT status, error_message FROM documents WHERE id = ?", (doc_id,)
            ).fetchone()
        print(f"  {result['status']}" + (f": {result['error_message']}" if result["error_message"] else ""))


if __name__ == "__main__":
    main()
