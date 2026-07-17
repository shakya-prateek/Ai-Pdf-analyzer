from dataclasses import dataclass
from functools import lru_cache
import os
from pathlib import Path

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parents[1]
load_dotenv(BASE_DIR / ".env")


@dataclass(frozen=True)
class Settings:
    database_path: Path
    frontend_urls: tuple[str, ...]
    llm_provider: str
    gemini_api_key: str
    groq_api_key: str
    gemini_model: str
    groq_model: str
    max_upload_mb: int
    max_files_per_upload: int
    max_pdf_pages: int
    pdf_render_dpi: int
    max_image_pixels: int
    chroma_dir: Path
    storage_dir: Path
    retrieval_threshold: float
    embedding_model: str
    enable_semantic_search: bool
    embedding_local_only: bool
    enable_ai_classification: bool
    workspace_access_tokens: tuple[str, ...]
    single_user_mode: bool
    store_chat_logs: bool


def _as_bool(value: str, default: bool) -> bool:
    normalized = value.strip().lower()
    if not normalized:
        return default
    return normalized in {"1", "true", "yes", "on"}


@lru_cache
def get_settings() -> Settings:
    database_url = os.getenv("DATABASE_URL", "sqlite:///./app.db")
    database_value = database_url.removeprefix("sqlite:///")
    database_path = Path(database_value)
    if not database_path.is_absolute():
        database_path = BASE_DIR / database_path

    chroma_dir = Path(os.getenv("CHROMA_DIR", "./storage/chroma"))
    if not chroma_dir.is_absolute():
        chroma_dir = BASE_DIR / chroma_dir

    storage_dir = Path(os.getenv("STORAGE_DIR", "./storage"))
    if not storage_dir.is_absolute():
        storage_dir = BASE_DIR / storage_dir

    access_tokens = tuple(
        token.strip()
        for token in os.getenv(
            "WORKSPACE_ACCESS_TOKENS",
            os.getenv("WORKSPACE_ACCESS_TOKEN", ""),
        ).split(",")
        if token.strip()
    )

    return Settings(
        database_path=database_path,
        frontend_urls=tuple(
            item.strip()
            for item in os.getenv("FRONTEND_URL", "http://localhost:3000").split(",")
            if item.strip()
        ),
        llm_provider=os.getenv("LLM_PROVIDER", "mock").lower(),
        gemini_api_key=os.getenv("GEMINI_API_KEY", ""),
        groq_api_key=os.getenv("GROQ_API_KEY", ""),
        gemini_model=os.getenv("GEMINI_MODEL", "gemini-1.5-flash"),
        groq_model=os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
        max_upload_mb=int(os.getenv("MAX_UPLOAD_MB", "10")),
        max_files_per_upload=int(os.getenv("MAX_FILES_PER_UPLOAD", "20")),
        max_pdf_pages=int(os.getenv("MAX_PDF_PAGES", "50")),
        pdf_render_dpi=int(os.getenv("PDF_RENDER_DPI", "96")),
        max_image_pixels=int(os.getenv("MAX_IMAGE_PIXELS", "40000000")),
        chroma_dir=chroma_dir,
        storage_dir=storage_dir,
        retrieval_threshold=float(os.getenv("RETRIEVAL_SCORE_THRESHOLD", "0.18")),
        embedding_model=os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2"),
        enable_semantic_search=_as_bool(os.getenv("ENABLE_SEMANTIC_SEARCH", "false"), False),
        embedding_local_only=_as_bool(os.getenv("EMBEDDING_LOCAL_ONLY", "true"), True),
        enable_ai_classification=_as_bool(
            os.getenv("ENABLE_AI_CLASSIFICATION", "false"), False
        ),
        workspace_access_tokens=access_tokens,
        single_user_mode=_as_bool(os.getenv("SINGLE_USER_MODE", "true"), True),
        store_chat_logs=_as_bool(os.getenv("STORE_CHAT_LOGS", "false"), False),
    )
