# Document Intelligence + Agentic RAG

A local-first full-stack application for turning mixed document collections into searchable, page-level evidence. It accepts digital PDFs, scanned PDFs, images, and text files; extracts text and tables; classifies each document; indexes page chunks; and answers questions with citations that open the exact rendered source page.

The project works without a paid API. When Gemini or Groq is not configured, deterministic classification and grounded extractive answers keep the complete workflow available locally.

## Quick Start

The repository root is dedicated to the PDF analyzer. Complete the one-time setup first:

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cd ..
npm run install:frontend
```

Then start the complete application:

```bash
npm run dev
```

This starts FastAPI at `http://localhost:8000` and Next.js at
`http://localhost:3000`. Open the frontend, upload a document, and start asking
questions. Local mode requires no account or access key.

## Features

- Bulk upload for PDF, PNG, JPG, JPEG, and TXT
- Simple private local workspace with no login required
- Permanent document, rendered-page, and search-index deletion
- Digital text extraction with `pdfplumber`
- Structured table extraction with `pdfplumber.extract_tables`
- PDF page rendering with `pdf2image`
- OCR fallback for scans and images with `pytesseract`
- Per-page text, table JSON, and protected page images
- Structured document classification with Gemini, Groq, or local heuristics
- ChromaDB indexing with `all-MiniLM-L6-v2`
- SQLite lexical retrieval fallback when model assets are unavailable
- Multi-turn query rewriting and grounded answers
- Inline `[document_name, page X]` citations
- Citation thumbnails and full-page image modal
- Live upload status polling and classification summaries
- Browser Web Speech API voice input
- Exact no-answer behavior for unrelated questions

## Architecture

```text
Next.js + TypeScript
  |-- /                    Chat, citations, voice input
  |-- /upload              Bulk upload and status polling
  |
  v
FastAPI
  |-- Upload validation -> UUID original storage
  |-- Parser -> pdfplumber / pdf2image / Tesseract / Pillow
  |-- Classifier -> Gemini or Groq -> validated JSON
  |                              \-> heuristic fallback
  |-- Indexer -> MiniLM embeddings -> ChromaDB
  |                         \-> SQLite lexical fallback
  |-- RAG -> query rewrite -> retrieval -> grounded synthesis
  |
  +-- SQLite: documents, pages, chunks, chat logs
  +-- storage/originals: private original files
  +-- storage/pages/{doc_id}: rendered page images
  +-- storage/chroma: persistent vector index
```

## Tech Stack

- Backend: Python, FastAPI, SQLite
- Parsing: pdfplumber, pdf2image, Pillow, pytesseract
- Retrieval: ChromaDB, sentence-transformers
- LLM: optional Gemini or Groq; local fallback by default
- Frontend: Next.js 16, React 19, TypeScript, Tailwind CSS

## Prerequisites

- Python 3.10+
- Node.js 18+
- Tesseract for OCR
- Poppler is recommended for `pdf2image`; `pypdfium2` is used automatically when Poppler is unavailable

macOS:

```bash
brew install poppler tesseract
```

Ubuntu/Debian:

```bash
sudo apt-get install poppler-utils tesseract-ocr
```

## Backend Setup

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```

The API runs at `http://localhost:8000`. Swagger documentation is available at `http://localhost:8000/docs`.

By default, the app uses a locally cached `all-MiniLM-L6-v2` model when available and immediately falls back to SQLite lexical retrieval when it is not. Set `EMBEDDING_LOCAL_ONLY=false` once if you want sentence-transformers to download the free model automatically.

## Frontend Setup

```bash
cd frontend
npm install
cp .env.example .env.local
npm run dev
```

Open `http://localhost:3000`. Upload documents at `/upload` and ask questions at `/`.

## Sample Documents

Five ready-to-use documents are included in `backend/sample_documents`.

```bash
cd backend
source venv/bin/activate
python scripts/ingest_samples.py
```

The script is idempotent by sample filename. After ingestion, try:

- `When is the invoice due?`
- `What improved in the support report?`
- `What is required when using a public network?`
- `What technologies does Maya know?`

## Environment Variables

Backend, from `backend/.env.example`:

| Variable | Default | Purpose |
| --- | --- | --- |
| `DATABASE_URL` | `sqlite:///./app.db` | SQLite database location |
| `FRONTEND_URL` | `http://localhost:3000` | Allowed CORS origin |
| `LLM_PROVIDER` | `mock` | `mock`, `gemini`, or `groq` |
| `GEMINI_API_KEY` | empty | Optional Gemini key |
| `GROQ_API_KEY` | empty | Optional Groq key |
| `GEMINI_MODEL` | `gemini-1.5-flash` | Configurable Gemini model |
| `GROQ_MODEL` | `llama-3.3-70b-versatile` | Configurable Groq model |
| `MAX_UPLOAD_MB` | `10` | Per-file upload limit |
| `MAX_FILES_PER_UPLOAD` | `20` | Files allowed in one request |
| `MAX_PDF_PAGES` | `50` | PDF page limit |
| `MAX_IMAGE_PIXELS` | `40000000` | Image decompression safety limit |
| `STORAGE_DIR` | `./storage` | Private originals and page images |
| `CHROMA_DIR` | `./storage/chroma` | Persistent Chroma directory |
| `RETRIEVAL_SCORE_THRESHOLD` | `0.18` | Minimum semantic similarity |
| `EMBEDDING_MODEL` | `all-MiniLM-L6-v2` | sentence-transformers model |
| `ENABLE_SEMANTIC_SEARCH` | `true` | Enable Chroma semantic retrieval |
| `EMBEDDING_LOCAL_ONLY` | `true` | Avoid network downloads at runtime |
| `SINGLE_USER_MODE` | `true` | Open directly into one private local workspace |
| `WORKSPACE_ACCESS_TOKENS` | empty | Optional keys when single-user mode is disabled |
| `STORE_CHAT_LOGS` | `false` | Persist chat logs only when explicitly enabled |

Frontend, from `frontend/.env.example`:

| Variable | Default | Purpose |
| --- | --- | --- |
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000` | Browser-visible backend URL |

Do not commit `.env` or `.env.local` files.

## API Overview

| Method | Route | Description |
| --- | --- | --- |
| `GET` | `/api/health` | Health check |
| `GET` | `/api/workspace` | Check workspace availability |
| `GET` | `/api/capabilities` | Report configured AI provider and model |
| `POST` | `/api/upload` | Upload multiple documents |
| `GET` | `/api/documents` | List documents, status, and classification |
| `GET` | `/api/documents/{doc_id}` | Get document metadata and pages |
| `GET` | `/api/documents/{doc_id}/status` | Poll processing status |
| `GET` | `/api/documents/{doc_id}/pages/{page_number}` | Serve a protected page image |
| `POST` | `/api/chat` | Ask a grounded question with history |
| `DELETE` | `/api/chat/history` | Clear persisted workspace chat history |
| `DELETE` | `/api/documents/{doc_id}` | Permanently delete a workspace document |

Processing states are `uploaded`, `parsing`, `classifying`, `indexing`, `indexed`, and `failed`.

## Deployment

### Render Backend

1. Create a Python web service rooted at `backend`.
2. Install Poppler and Tesseract in the service image or use a Docker deployment.
3. Set the build command to `pip install -r requirements.txt`.
4. Set the start command to `uvicorn app.main:app --host 0.0.0.0 --port $PORT`.
5. Set `FRONTEND_URL` to the Vercel origin.
6. Keep `SINGLE_USER_MODE=true` for a simple private demo, or disable it and
   configure `WORKSPACE_ACCESS_TOKENS` for multiple isolated workspaces.
7. Configure optional LLM keys.

The included `render.yaml` uses Render's free ephemeral filesystem under `/tmp`. Uploaded data resets when the service is recreated or idled. Persistent SQLite, Chroma, and uploaded files require a persistent disk or external storage; for a free assessment demo, rerun sample ingestion after deployment.

### Vercel Frontend

1. Import the repository and set the root directory to `frontend`.
2. Set `NEXT_PUBLIC_API_URL` to the public Render backend URL.
3. Deploy with the standard Next.js build settings.

## Security Decisions

### Implemented

* File uploads are restricted to PDF, PNG, JPG, JPEG, and TXT.
* Files are renamed using UUIDs, so user-provided filenames are not trusted.
* Uploaded documents are stored outside the frontend public directory.
* Page images are served through authenticated backend API routes instead of direct public paths.
* Documents, chunks, chat logs, and retrieval are isolated by hashed workspace ownership.
* Chat logging is disabled by default.
* File size and page count limits are enforced to reduce abuse.
* API keys are loaded from environment variables and are not committed.
* Retrieval responses only expose cited pages used in the answer.
* The chatbot is instructed to answer only from retrieved context and return a no-answer response when relevant content is not found.
* Basic CORS configuration is controlled by environment variables.

Additional implemented controls include MIME and extension checks, empty-file rejection, bounded request history, display-name sanitization, a basic in-memory API rate limit, path containment checks for page images, safe error truncation, and no document-text logging.

### Considered but skipped

* Full account registration and role-based access control.
* Virus scanning with ClamAV.
* Encryption at rest for uploaded files.
* Separate worker sandbox for OCR processing.
* Signed URLs for page image access.

### Given more time

* Add user accounts and per-user document isolation.
* Add encrypted object storage.
* Add audit logs for document access.
* Add malware scanning before parsing.
* Add background job queue using Celery or Redis Queue.

## Operational Notes

- FastAPI background tasks are suitable for this MVP. Production processing should use a durable worker queue.
- The mock answer mode is extractive by design and always appends source citations.
- Table data is stored as JSON on each page; page text remains the primary retrieval surface.
- Uploaded originals are retained for processing but are not exposed by any API route.

## Verification

Install test dependencies and run the automated checks:

```bash
cd backend
source venv/bin/activate
pip install -r requirements-dev.txt
cd ..
npm run test:backend
npm run typecheck
npm run build
```

The backend suite covers upload validation, filename sanitization, classification, table indexing, grounded chat answers, exact no-answer behavior, and protected page images.
