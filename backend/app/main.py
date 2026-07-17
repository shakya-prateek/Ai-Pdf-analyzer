import mimetypes
import re
import time
import uuid
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated

from fastapi import (
    BackgroundTasks,
    Depends,
    FastAPI,
    File,
    HTTPException,
    Path as PathParameter,
    Request,
    UploadFile,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse

from .auth import require_workspace
from .config import get_settings
from .database import connect, init_db, now_iso, row_to_document
from .schemas import ChatRequest, ChatResponse, ToolRequest, ToolResponse
from .services.processor import process_document
from .services.parser import _render_pdf_page, _save_page_image
from .services.rag import answer_question
from .services.documents import DocumentProcessingError, delete_document
from .services.tools import generate_tool_response


settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    (settings.storage_dir / "originals").mkdir(parents=True, exist_ok=True)
    (settings.storage_dir / "pages").mkdir(parents=True, exist_ok=True)
    yield


app = FastAPI(
    title="AskMyPDF AI",
    version="1.0.0",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.frontend_urls),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

ALLOWED_TYPES = {
    "pdf": {"application/pdf", "application/octet-stream", ""},
    "png": {"image/png", "application/octet-stream", ""},
    "jpg": {"image/jpeg", "application/octet-stream", ""},
    "jpeg": {"image/jpeg", "application/octet-stream", ""},
    "txt": {"text/plain", "application/octet-stream", "text/csv", ""},
}
request_times: dict[str, deque[float]] = defaultdict(deque)


@app.middleware("http")
async def rate_limit(request: Request, call_next):
    if request.url.path in {"/api/upload", "/api/chat", "/api/tools/generate"}:
        client = request.client.host if request.client else "unknown"
        now = time.monotonic()
        bucket = request_times[client]
        while bucket and bucket[0] < now - 60:
            bucket.popleft()
        if len(bucket) >= 60:
            return JSONResponse(status_code=429, content={"detail": "Rate limit exceeded"})
        bucket.append(now)
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), geolocation=()"
    return response


def sanitize_display_name(name: str) -> str:
    clean = Path(name).name
    clean = re.sub(r"[\x00-\x1f\x7f]", "", clean)
    return clean[:180] or "document"


def content_matches_type(content: bytes, extension: str) -> bool:
    if extension == "pdf":
        return content.startswith(b"%PDF-")
    if extension == "png":
        return content.startswith(b"\x89PNG\r\n\x1a\n")
    if extension in {"jpg", "jpeg"}:
        return content.startswith(b"\xff\xd8\xff")
    if extension == "txt":
        if b"\x00" in content[:4096]:
            return False
        try:
            content[:4096].decode("utf-8")
            return True
        except UnicodeDecodeError:
            return False
    return False


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/workspace")
def workspace(owner_id: Annotated[str, Depends(require_workspace)]):
    return {"status": "authenticated", "workspace_id": owner_id[:12]}


@app.get("/api/capabilities")
def capabilities(owner_id: Annotated[str, Depends(require_workspace)]):
    del owner_id
    provider = settings.llm_provider
    configured = (
        provider == "groq" and bool(settings.groq_api_key)
    ) or (
        provider == "gemini" and bool(settings.gemini_api_key)
    )
    return {
        "ai_enabled": configured,
        "provider": provider if configured else "local",
        "model": settings.groq_model if provider == "groq" and configured else (
            settings.gemini_model if provider == "gemini" and configured else None
        ),
    }


@app.post("/api/upload", status_code=202)
async def upload_documents(
    background_tasks: BackgroundTasks,
    owner_id: Annotated[str, Depends(require_workspace)],
    files: list[UploadFile] = File(...),
):
    if not files:
        raise HTTPException(status_code=400, detail="No files supplied")
    if len(files) > settings.max_files_per_upload:
        raise HTTPException(
            status_code=400,
            detail=f"A maximum of {settings.max_files_per_upload} files can be uploaded at once",
        )

    validated: list[tuple[UploadFile, str, str, bytes]] = []
    max_bytes = settings.max_upload_mb * 1024 * 1024
    for upload in files:
        display_name = sanitize_display_name(upload.filename or "")
        extension = Path(display_name).suffix.lower().lstrip(".")
        if extension not in ALLOWED_TYPES:
            raise HTTPException(status_code=415, detail=f"Unsupported file type: {display_name}")
        content_type = (
            upload.content_type or mimetypes.guess_type(display_name)[0] or ""
        ).lower()
        if content_type not in ALLOWED_TYPES[extension]:
            raise HTTPException(status_code=415, detail=f"Invalid MIME type for {display_name}")

        content = await upload.read(max_bytes + 1)
        if not content:
            raise HTTPException(status_code=400, detail=f"{display_name} is empty")
        if len(content) > max_bytes:
            raise HTTPException(
                status_code=413,
                detail=f"{display_name} exceeds the {settings.max_upload_mb} MB limit",
            )
        if not content_matches_type(content, extension):
            raise HTTPException(status_code=415, detail=f"File contents do not match {display_name}")
        validated.append((upload, display_name, extension, content))

    accepted = []
    for upload, display_name, extension, content in validated:
        doc_id = str(uuid.uuid4())
        stored_path = settings.storage_dir / "originals" / f"{doc_id}.{extension}"
        try:
            stored_path.write_bytes(content)
            with connect() as connection:
                connection.execute(
                    """INSERT INTO documents
                       (id, owner_id, original_name, stored_name, file_type, status, created_at)
                       VALUES (?, ?, ?, ?, ?, 'uploaded', ?)""",
                    (
                        doc_id,
                        owner_id,
                        display_name,
                        str(stored_path),
                        extension,
                        now_iso(),
                    ),
                )
        except Exception:
            stored_path.unlink(missing_ok=True)
            raise HTTPException(status_code=500, detail=f"Unable to store {display_name}")
        finally:
            await upload.close()
        background_tasks.add_task(process_document, doc_id)
        accepted.append({"id": doc_id, "original_name": display_name, "status": "uploaded"})
    return {"documents": accepted}


@app.get("/api/documents")
def list_documents(owner_id: Annotated[str, Depends(require_workspace)]):
    with connect() as connection:
        rows = connection.execute(
            "SELECT * FROM documents WHERE owner_id = ? ORDER BY created_at DESC",
            (owner_id,),
        ).fetchall()
    return {"documents": [row_to_document(row) for row in rows]}


@app.get("/api/documents/{doc_id}")
def get_document(
    doc_id: str,
    owner_id: Annotated[str, Depends(require_workspace)],
):
    with connect() as connection:
        row = connection.execute(
            "SELECT * FROM documents WHERE id = ? AND owner_id = ?",
            (doc_id, owner_id),
        ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Document not found")
    return row_to_document(row, include_pages=True, owner_id=owner_id)


@app.get("/api/documents/{doc_id}/status")
def document_status(
    doc_id: str,
    owner_id: Annotated[str, Depends(require_workspace)],
):
    with connect() as connection:
        row = connection.execute(
            """SELECT id, original_name, status, classification_json, error_message
               FROM documents WHERE id = ? AND owner_id = ?""",
            (doc_id, owner_id),
        ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Document not found")
    result = dict(row)
    raw = result.pop("classification_json")
    if raw:
        import json

        try:
            result["classification"] = json.loads(raw)
        except json.JSONDecodeError:
            result["classification"] = None
    else:
        result["classification"] = None
    return result


@app.get("/api/documents/{doc_id}/pages/{page_number}")
def page_image(
    doc_id: str,
    owner_id: Annotated[str, Depends(require_workspace)],
    page_number: int = PathParameter(ge=1),
):
    with connect() as connection:
        row = connection.execute(
            """SELECT p.image_path, d.stored_name, d.file_type FROM pages p
               JOIN documents d ON d.id = p.doc_id
               WHERE p.doc_id = ? AND p.page_number = ? AND d.owner_id = ?""",
            (doc_id, page_number, owner_id),
        ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Page not found")
    path = Path(row["image_path"])
    resolved_path = path.resolve()
    storage_root = settings.storage_dir.resolve()
    if storage_root not in resolved_path.parents:
        raise HTTPException(status_code=404, detail="Page image unavailable")
    if not resolved_path.is_file():
        source_path = Path(row["stored_name"]).resolve()
        if (
            row["file_type"] != "pdf"
            or storage_root not in source_path.parents
            or not source_path.is_file()
        ):
            raise HTTPException(status_code=404, detail="Page image unavailable")
        try:
            image = _render_pdf_page(
                source_path,
                page_number,
                settings.pdf_render_dpi,
            )
            _save_page_image(image, resolved_path)
        except Exception as exc:
            raise HTTPException(status_code=404, detail="Page image unavailable") from exc
    return FileResponse(
        resolved_path,
        media_type="image/png",
        headers={"Cache-Control": "private, no-store"},
    )


@app.delete("/api/documents/{doc_id}", status_code=204)
def remove_document(
    doc_id: str,
    owner_id: Annotated[str, Depends(require_workspace)],
):
    try:
        deleted = delete_document(doc_id, owner_id)
    except DocumentProcessingError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if not deleted:
        raise HTTPException(status_code=404, detail="Document not found")
    return None


@app.post("/api/chat", response_model=ChatResponse)
def chat(
    payload: ChatRequest,
    owner_id: Annotated[str, Depends(require_workspace)],
):
    return answer_question(
        payload.message.strip(),
        [{"role": item.role, "content": item.content} for item in payload.history],
        owner_id,
    )


@app.post("/api/tools/generate", response_model=ToolResponse)
def generate_tool(
    payload: ToolRequest,
    owner_id: Annotated[str, Depends(require_workspace)],
):
    return generate_tool_response(payload, owner_id)


@app.delete("/api/chat/history", status_code=204)
def clear_chat_history(owner_id: Annotated[str, Depends(require_workspace)]):
    with connect() as connection:
        connection.execute("DELETE FROM chat_logs WHERE owner_id = ?", (owner_id,))
    return None
