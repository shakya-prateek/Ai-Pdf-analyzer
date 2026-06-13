import math
import re
import uuid
from functools import lru_cache
from typing import Any

from ..config import get_settings
from ..database import connect


TOKEN_PATTERN = re.compile(r"[a-zA-Z0-9][a-zA-Z0-9_-]+")
STOP_WORDS = {
    "about", "after", "again", "also", "and", "are", "because", "been", "before",
    "being", "can", "could", "did", "does", "for", "from", "had", "has", "have",
    "how", "into", "its", "may", "more", "most", "not", "of", "on", "only", "or",
    "our", "should", "than", "that", "the", "their", "them", "then", "there",
    "these", "they", "this", "to", "was", "were", "what", "when", "where", "which",
    "who", "will", "with", "would", "you", "your",
}


def chunk_text(text: str, size: int = 850, overlap: int = 140) -> list[str]:
    clean = re.sub(r"[ \t]+", " ", text)
    clean = re.sub(r"\n{3,}", "\n\n", clean).strip()
    if not clean:
        return []
    chunks = []
    start = 0
    while start < len(clean):
        end = min(len(clean), start + size)
        if end < len(clean):
            boundary = clean.rfind(" ", start, end)
            if boundary > start + size // 2:
                end = boundary
        chunks.append(clean[start:end].strip())
        if end >= len(clean):
            break
        start = max(start + 1, end - overlap)
    return chunks


@lru_cache
def _embedding_model():
    settings = get_settings()
    if not settings.enable_semantic_search:
        return None
    try:
        from sentence_transformers import SentenceTransformer

        return SentenceTransformer(
            settings.embedding_model,
            local_files_only=settings.embedding_local_only,
        )
    except Exception:
        return None


@lru_cache
def _collection():
    if not get_settings().enable_semantic_search:
        return None
    try:
        import chromadb

        settings = get_settings()
        settings.chroma_dir.mkdir(parents=True, exist_ok=True)
        client = chromadb.PersistentClient(path=str(settings.chroma_dir))
        return client.get_or_create_collection("document_chunks", metadata={"hnsw:space": "cosine"})
    except Exception:
        return None


def index_pages(
    doc_id: str,
    owner_id: str,
    document_name: str,
    pages: list[dict[str, Any]],
) -> None:
    model = _embedding_model()
    collection = _collection()
    ids: list[str] = []
    texts: list[str] = []
    metadata: list[dict[str, Any]] = []
    with connect() as connection:
        connection.execute("DELETE FROM chunks WHERE doc_id = ?", (doc_id,))
        for page in pages:
            table_text = "\n".join(
                " | ".join(str(cell) for cell in row if str(cell).strip())
                for table in page.get("tables", [])
                for row in table.get("rows", [])
            )
            searchable_text = page["text"]
            if table_text:
                searchable_text = f"{searchable_text}\n\nExtracted table:\n{table_text}".strip()
            for text in chunk_text(searchable_text):
                chunk_id = str(uuid.uuid4())
                ids.append(chunk_id)
                texts.append(text)
                metadata.append(
                    {
                        "doc_id": doc_id,
                        "owner_id": owner_id,
                        "document_name": document_name,
                        "page_number": page["page_number"],
                        "page_image_url": f"/api/documents/{doc_id}/pages/{page['page_number']}",
                        "chunk_id": chunk_id,
                    }
                )
                connection.execute(
                    """INSERT INTO chunks
                       (id, owner_id, doc_id, page_number, chunk_text, chroma_id)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (chunk_id, owner_id, doc_id, page["page_number"], text, chunk_id),
                )
    if collection and model and texts:
        try:
            embeddings = model.encode(texts, normalize_embeddings=True).tolist()
            collection.delete(where={"doc_id": doc_id})
        except Exception:
            pass
        else:
            try:
                collection.add(ids=ids, documents=texts, metadatas=metadata, embeddings=embeddings)
            except Exception:
                pass


def _tokens(text: str) -> set[str]:
    return {
        token.lower()
        for token in TOKEN_PATTERN.findall(text)
        if len(token) > 2 and token.lower() not in STOP_WORDS
    }


def _lexical_retrieve(query: str, owner_id: str, limit: int) -> list[dict[str, Any]]:
    query_tokens = _tokens(query)
    if not query_tokens:
        return []
    with connect() as connection:
        rows = connection.execute(
            """SELECT c.id, c.doc_id, c.page_number, c.chunk_text, d.original_name
               FROM chunks c JOIN documents d ON d.id = c.doc_id
               WHERE d.status = 'indexed' AND d.owner_id = ? AND c.owner_id = ?""",
            (owner_id, owner_id),
        ).fetchall()
    scored = []
    for row in rows:
        text_tokens = _tokens(row["chunk_text"])
        overlap = query_tokens & text_tokens
        if not overlap:
            continue
        score = len(overlap) / math.sqrt(len(query_tokens) * max(1, len(text_tokens)))
        scored.append(
            {
                "text": row["chunk_text"],
                "score": score,
                "metadata": {
                    "doc_id": row["doc_id"],
                    "document_name": row["original_name"],
                    "page_number": row["page_number"],
                    "page_image_url": f"/api/documents/{row['doc_id']}/pages/{row['page_number']}",
                    "chunk_id": row["id"],
                },
            }
        )
    ranked = sorted(scored, key=lambda item: item["score"], reverse=True)
    if not ranked:
        return []
    minimum = max(0.08, ranked[0]["score"] * 0.5)
    return [item for item in ranked if item["score"] >= minimum][:limit]


def retrieve(query: str, owner_id: str, limit: int = 5) -> list[dict[str, Any]]:
    model = _embedding_model()
    collection = _collection()
    if collection and model:
        try:
            embedding = model.encode([query], normalize_embeddings=True).tolist()
            result = collection.query(
                query_embeddings=embedding,
                n_results=limit,
                where={"owner_id": owner_id},
                include=["documents", "metadatas", "distances"],
            )
            matches = []
            with connect() as connection:
                indexed_doc_ids = {
                    row["id"]
                    for row in connection.execute(
                        "SELECT id FROM documents WHERE status = 'indexed' AND owner_id = ?",
                        (owner_id,),
                    ).fetchall()
                }
            for text, metadata, distance in zip(
                result["documents"][0], result["metadatas"][0], result["distances"][0]
            ):
                score = 1 - float(distance)
                if (
                    metadata.get("doc_id") in indexed_doc_ids
                    and score >= get_settings().retrieval_threshold
                ):
                    matches.append({"text": text, "metadata": metadata, "score": score})
            if matches:
                return matches
        except Exception:
            pass
    return _lexical_retrieve(query, owner_id, limit)


def delete_document_index(doc_id: str) -> None:
    collection = _collection()
    if not collection:
        return
    try:
        collection.delete(where={"doc_id": doc_id})
    except Exception:
        pass
