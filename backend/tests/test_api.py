import os
import tempfile
from pathlib import Path

TEST_ROOT = Path(tempfile.mkdtemp(prefix="docuscope-tests-"))
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_ROOT / 'test.db'}"
os.environ["STORAGE_DIR"] = str(TEST_ROOT / "storage")
os.environ["CHROMA_DIR"] = str(TEST_ROOT / "chroma")
os.environ["ENABLE_SEMANTIC_SEARCH"] = "false"
os.environ["LLM_PROVIDER"] = "mock"
TOKEN_A = "test-private-workspace-a"
TOKEN_B = "test-private-workspace-b"
os.environ["WORKSPACE_ACCESS_TOKENS"] = f"{TOKEN_A},{TOKEN_B}"
os.environ["SINGLE_USER_MODE"] = "false"
os.environ["STORE_CHAT_LOGS"] = "false"

import pytest
from httpx import ASGITransport, AsyncClient

from app.auth import workspace_id_from_token
from app.database import connect
from app.main import app
from app.services.rag import NO_ANSWER

HEADERS_A = {"Authorization": f"Bearer {TOKEN_A}"}
HEADERS_B = {"Authorization": f"Bearer {TOKEN_B}"}


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
async def client():
    async with app.router.lifespan_context(app):
        with connect() as connection:
            connection.execute("DELETE FROM chat_logs")
            connection.execute("DELETE FROM chunks")
            connection.execute("DELETE FROM pages")
            connection.execute("DELETE FROM documents")
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as test_client:
            yield test_client


@pytest.mark.anyio
async def test_health_and_empty_library(client: AsyncClient):
    response = await client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

    unauthorized = await client.get("/api/documents")
    assert unauthorized.status_code == 401

    invalid = await client.get(
        "/api/workspace",
        headers={"Authorization": "Bearer incorrect"},
    )
    assert invalid.status_code == 401

    workspace = await client.get("/api/workspace", headers=HEADERS_A)
    assert workspace.status_code == 200
    assert workspace.json()["workspace_id"] == workspace_id_from_token(TOKEN_A)[:12]

    documents = await client.get("/api/documents", headers=HEADERS_A)
    assert documents.status_code == 200
    assert documents.json() == {"documents": []}

    tool = await client.post(
        "/api/tools/generate",
        headers=HEADERS_A,
        json={"tool": "paraphrase", "text": "This project analyzes uploaded PDF files."},
    )
    assert tool.status_code == 200
    assert tool.json()["provider"] == "local:fallback"
    assert "project" in tool.json()["result"].lower()

    healthcare = await client.post(
        "/api/tools/generate",
        headers=HEADERS_A,
        json={
            "tool": "healthcare_report",
            "text": "Hemoglobin 13.2 g/dL\nGlucose fasting 106 mg/dL\nLDL cholesterol 142 mg/dL",
        },
    )
    assert healthcare.status_code == 200
    assert "not medical advice" in healthcare.json()["result"].lower()
    assert "glucose" in healthcare.json()["result"].lower()


@pytest.mark.anyio
async def test_upload_index_chat_and_page_image(client: AsyncClient):
    invoice = (
        "NORTHSTAR OFFICE SUPPLIES\n"
        "Invoice INV-2026-1042\n"
        "Amount due: $1,404.00\n"
        "Payment terms: Net 30.\n"
        "Payment is due June 13, 2026.\n"
    )
    upload = await client.post(
        "/api/upload",
        headers=HEADERS_A,
        files={"files": ("../../sample_invoice.txt", invoice, "text/plain")},
    )
    assert upload.status_code == 202
    document = upload.json()["documents"][0]
    assert document["original_name"] == "sample_invoice.txt"

    listing = (await client.get("/api/documents", headers=HEADERS_A)).json()["documents"]
    assert len(listing) == 1
    assert listing[0]["status"] == "indexed"
    assert "stored_name" not in listing[0]
    assert listing[0]["classification"]["document_type"] == "invoice"

    chat = await client.post(
        "/api/chat",
        headers=HEADERS_A,
        json={"message": "When is the invoice due?", "history": []},
    )
    payload = chat.json()
    assert chat.status_code == 200
    assert "June 13, 2026" in payload["answer"]
    assert "[sample_invoice.txt, page 1]" in payload["answer"]
    assert len(payload["citations"]) == 1

    count = await client.post(
        "/api/chat",
        headers=HEADERS_A,
        json={"message": "How many PDFs do I have?", "history": []},
    )
    assert count.json() == {
        "answer": "You have 0 PDFs.",
        "citations": [],
    }

    document_count = await client.post(
        "/api/chat",
        headers=HEADERS_A,
        json={"message": "How many documents are uploaded?", "history": []},
    )
    assert "You have 1 indexed document: sample_invoice.txt." == document_count.json()["answer"]

    shared_tool_count = await client.post(
        "/api/tools/generate",
        headers=HEADERS_A,
        json={
            "tool": "chat",
            "text": "How many documents have I uploaded?",
            "history": [],
        },
    )
    assert shared_tool_count.status_code == 200
    assert shared_tool_count.json()["result"] == "You have 1 indexed document: sample_invoice.txt."

    summary = await client.post(
        "/api/chat",
        headers=HEADERS_A,
        json={"message": "Summarize my uploaded documents.", "history": []},
    )
    assert "sample_invoice.txt:" in summary.json()["answer"]
    assert "[sample_invoice.txt, page 1]" in summary.json()["answer"]
    assert len(summary.json()["citations"]) == 1

    executive_summary = await client.post(
        "/api/chat",
        headers=HEADERS_A,
        json={"message": "Create an executive summary of the uploaded document.", "history": []},
    )
    assert "sample_invoice.txt:" in executive_summary.json()["answer"]
    assert "[sample_invoice.txt, page 1]" in executive_summary.json()["answer"]

    private_page = await client.get(payload["citations"][0]["page_image_url"])
    assert private_page.status_code == 401

    page = await client.get(
        payload["citations"][0]["page_image_url"],
        headers=HEADERS_A,
    )
    assert page.status_code == 200
    assert page.headers["content-type"] == "image/png"
    assert page.content.startswith(b"\x89PNG")

    unrelated = await client.post(
        "/api/chat",
        headers=HEADERS_A,
        json={"message": "What is the orbital period of Neptune?", "history": []},
    )
    assert unrelated.json() == {"answer": NO_ANSWER, "citations": []}

    with connect() as connection:
        assert connection.execute("SELECT COUNT(*) AS count FROM chat_logs").fetchone()["count"] == 0


@pytest.mark.anyio
async def test_resume_section_questions_return_actual_section(client: AsyncClient):
    resume = (
        "Prateek Shakya\n"
        "PROFESSIONAL SUMMARY\n"
        "Data science student focused on predictive modeling.\n"
        "TECHNICAL SKILLS\n"
        "Languages: Python, SQL, JavaScript\n"
        "Machine Learning: Scikit-learn, Logistic Regression, Random Forest\n"
        "Data Visualization: Tableau, Power BI\n"
        "PROJECTS\n"
        "Hotel Booking Cancellation Analysis [GitHub]\n"
        "Built a data science project using Python, Pandas, and Scikit-learn.\n"
        "FlightOps Dashboard — US Flight Delay Analysis [GitHub]\n"
        "Created Tableau dashboards for delay patterns and route performance.\n"
        "CERTIFICATIONS & HACKATHONS\n"
        "Deloitte Australia Data Analytics Job Simulation\n"
    )
    upload = await client.post(
        "/api/upload",
        headers=HEADERS_A,
        files={"files": ("resume.txt", resume, "text/plain")},
    )
    assert upload.status_code == 202

    skills = await client.post(
        "/api/chat",
        headers=HEADERS_A,
        json={"message": "What skills are mentioned in the uploaded resume?", "history": []},
    )
    payload = skills.json()
    assert skills.status_code == 200
    assert "Technical skills:" in payload["answer"]
    assert "Python, SQL, JavaScript" in payload["answer"]
    assert "Scikit-learn" in payload["answer"]
    assert "[resume.txt, page 1]" in payload["answer"]

    projects = await client.post(
        "/api/chat",
        headers=HEADERS_A,
        json={"message": "project in my resume ds", "history": []},
    )
    project_payload = projects.json()
    assert projects.status_code == 200
    assert "Projects:" in project_payload["answer"]
    assert "Hotel Booking Cancellation Analysis" in project_payload["answer"]
    assert "FlightOps Dashboard" in project_payload["answer"]
    assert "[resume.txt, page 1]" in project_payload["answer"]


@pytest.mark.anyio
async def test_rejects_empty_unsupported_and_spoofed_files(client: AsyncClient):
    empty = await client.post(
        "/api/upload",
        headers=HEADERS_A,
        files={"files": ("empty.txt", b"", "text/plain")},
    )
    assert empty.status_code == 400

    unsupported = await client.post(
        "/api/upload",
        headers=HEADERS_A,
        files={"files": ("payload.exe", b"MZ", "application/octet-stream")},
    )
    assert unsupported.status_code == 415

    spoofed = await client.post(
        "/api/upload",
        headers=HEADERS_A,
        files={"files": ("fake.pdf", b"not a pdf", "application/pdf")},
    )
    assert spoofed.status_code == 415

    octet_stream_pdf = await client.post(
        "/api/upload",
        headers=HEADERS_A,
        files={
            "files": (
                "minimal.pdf",
                b"%PDF-1.4\n%test\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF",
                "application/octet-stream",
            )
        },
    )
    assert octet_stream_pdf.status_code == 202


@pytest.mark.anyio
async def test_table_rows_are_in_search_index(client: AsyncClient):
    from app.services.vector_store import index_pages

    with connect() as connection:
        connection.execute(
            """INSERT INTO documents
               (id, owner_id, original_name, stored_name, file_type, status, created_at)
               VALUES ('table-doc', ?, 'table.pdf', 'private.pdf', 'pdf', 'indexed', '2026-01-01')""",
            (workspace_id_from_token(TOKEN_A),),
        )
    index_pages(
        "table-doc",
        workspace_id_from_token(TOKEN_A),
        "table.pdf",
        [{
            "page_number": 2,
            "text": "Quarterly results",
            "tables": [{"rows": [["Region", "Revenue"], ["West", "$85,000"]]}],
        }],
    )
    with connect() as connection:
        chunk = connection.execute(
            "SELECT chunk_text FROM chunks WHERE doc_id = 'table-doc'"
        ).fetchone()
    assert "West | $85,000" in chunk["chunk_text"]


@pytest.mark.anyio
async def test_workspace_isolation_and_document_deletion(client: AsyncClient):
    upload = await client.post(
        "/api/upload",
        headers=HEADERS_A,
        files={
            "files": (
                "private_notes.txt",
                "Project Atlas launch date is September 18, 2026.",
                "text/plain",
            )
        },
    )
    assert upload.status_code == 202
    doc_id = upload.json()["documents"][0]["id"]

    with connect() as connection:
        document = connection.execute(
            "SELECT stored_name FROM documents WHERE id = ?",
            (doc_id,),
        ).fetchone()
        page = connection.execute(
            "SELECT image_path FROM pages WHERE doc_id = ?",
            (doc_id,),
        ).fetchone()
    original_path = Path(document["stored_name"])
    page_path = Path(page["image_path"])
    assert original_path.is_file()
    assert page_path.is_file()

    listing_b = await client.get("/api/documents", headers=HEADERS_B)
    assert listing_b.json() == {"documents": []}

    hidden = await client.get(f"/api/documents/{doc_id}", headers=HEADERS_B)
    assert hidden.status_code == 404
    hidden_page = await client.get(
        f"/api/documents/{doc_id}/pages/1",
        headers=HEADERS_B,
    )
    assert hidden_page.status_code == 404
    hidden_delete = await client.delete(f"/api/documents/{doc_id}", headers=HEADERS_B)
    assert hidden_delete.status_code == 404

    chat_b = await client.post(
        "/api/chat",
        headers=HEADERS_B,
        json={"message": "When is Project Atlas launching?", "history": []},
    )
    assert chat_b.json() == {"answer": NO_ANSWER, "citations": []}

    deleted = await client.delete(f"/api/documents/{doc_id}", headers=HEADERS_A)
    assert deleted.status_code == 204
    assert not original_path.exists()
    assert not page_path.exists()
    assert (await client.get("/api/documents", headers=HEADERS_A)).json() == {
        "documents": []
    }
    with connect() as connection:
        assert connection.execute(
            "SELECT COUNT(*) AS count FROM chunks WHERE doc_id = ?",
            (doc_id,),
        ).fetchone()["count"] == 0


def test_pdf_renderer_falls_back_when_poppler_is_unavailable(monkeypatch):
    import pdf2image
    from PIL import Image

    from app.services.parser import _render_pdf_page

    pdf_path = TEST_ROOT / "fallback.pdf"
    Image.new("RGB", (240, 320), "white").save(pdf_path, "PDF")

    def unavailable(*args, **kwargs):
        raise RuntimeError("Poppler unavailable")

    monkeypatch.setattr(pdf2image, "convert_from_path", unavailable)
    rendered = _render_pdf_page(pdf_path, 1)
    assert rendered.width > 0
    assert rendered.height > 0
