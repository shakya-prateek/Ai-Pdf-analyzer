import json
import re
import urllib.request
from datetime import date

from ..config import get_settings
from ..database import connect
from ..schemas import ToolRequest, ToolResponse
from .http_client import load_json


TOOL_INSTRUCTIONS = {
    "chat": (
        "You are a concise AI assistant inside a PDF productivity workspace. "
        "Answer clearly, ask for documents when the user needs document-grounded analysis, "
        "and avoid pretending you have read files unless they are supplied in the prompt."
    ),
    "humanize": (
        "Rewrite the text in a natural, professional human tone. Preserve meaning, facts, "
        "names, numbers, citations, and formatting where possible."
    ),
    "verify_ai": (
        "Review the text for signals that may sound overly AI-generated. Give a short "
        "diagnosis, a confidence level, and practical edits to make it more natural."
    ),
    "paraphrase": (
        "Paraphrase the text while preserving meaning. Respect the requested style. "
        "Keep important terms, names, dates, citations, and numbers intact."
    ),
    "correct": (
        "Correct grammar, spelling, punctuation, and clarity without changing the meaning. "
        "Return the corrected text only unless a short note is necessary."
    ),
    "translate": (
        "Translate the text into the requested language. Preserve formatting, numbers, "
        "proper nouns, and technical terms when appropriate."
    ),
    "quiz": (
        "Create a useful study quiz from the material. Include 5 multiple-choice questions, "
        "the correct answer, and a one-sentence explanation for each."
    ),
    "flashcards": (
        "Create compact study flashcards from the material. Use the format Q: ... A: ... "
        "and focus on high-value concepts."
    ),
    "mind_map": (
        "Create a readable Mermaid mindmap from the material. Return only Mermaid code "
        "inside a fenced mermaid block."
    ),
    "image_prompt": (
        "Turn the user's idea into a polished image-generation prompt. Include subject, "
        "composition, lighting, style, mood, colors, and negative constraints."
    ),
    "document_draft": (
        "Create a structured document draft from the user's title or instructions. "
        "Include a title, outline, and a strong opening section."
    ),
    "healthcare_report": (
        "You are a careful healthcare report explainer for lab-report-style text. "
        "Summarize biomarkers and trends in plain language, identify values the user "
        "may want to discuss with a licensed clinician, and suggest follow-up questions. "
        "Do not diagnose, prescribe treatment, or claim certainty. Always include a "
        "clear note that this is educational and not medical advice."
    ),
}


def _provider_label() -> str:
    settings = get_settings()
    if settings.llm_provider == "groq" and settings.groq_api_key:
        return f"groq:{settings.groq_model}"
    if settings.llm_provider == "gemini" and settings.gemini_api_key:
        return f"gemini:{settings.gemini_model}"
    return "local:fallback"


def _load_document_context(owner_id: str) -> tuple[list[dict[str, str]], str]:
    with connect() as connection:
        docs = connection.execute(
            """SELECT id, original_name, file_type, status, classification_json
               FROM documents
               WHERE owner_id = ?
               ORDER BY created_at DESC""",
            (owner_id,),
        ).fetchall()
        indexed_docs = [doc for doc in docs if doc["status"] == "indexed"]
        summaries: list[dict[str, str]] = []
        context_blocks: list[str] = []
        for doc in indexed_docs[:6]:
            classification = {}
            if doc["classification_json"]:
                try:
                    classification = json.loads(doc["classification_json"])
                except json.JSONDecodeError:
                    classification = {}
            pages = connection.execute(
                """SELECT page_number, text
                   FROM pages
                   WHERE doc_id = ?
                   ORDER BY page_number
                   LIMIT 4""",
                (doc["id"],),
            ).fetchall()
            summary = str(classification.get("summary") or "").strip()
            doc_type = str(classification.get("document_type") or doc["file_type"])
            summaries.append(
                {
                    "name": doc["original_name"],
                    "type": doc_type,
                    "summary": summary,
                }
            )
            page_text = "\n".join(
                f"Page {page['page_number']}: {page['text'][:1600]}"
                for page in pages
                if page["text"]
            )
            block = (
                f"<document name=\"{doc['original_name']}\" type=\"{doc_type}\">\n"
                f"Summary: {summary or 'No summary available.'}\n"
                f"{page_text[:4200]}\n"
                "</document>"
            )
            context_blocks.append(block)
    context = "\n\n".join(context_blocks)
    return summaries, context[:12000]


def _document_count_answer(payload: ToolRequest, documents: list[dict[str, str]]) -> str | None:
    normalized = payload.text.lower()
    if not re.search(r"\bhow many\b", normalized):
        return None
    if not re.search(r"\b(documents?|pdfs?|files?|uploads?|uploaded)\b", normalized):
        return None
    count = len(documents)
    if count == 0:
        return "You do not have any files ready for AI yet. Upload a document from the Documents page first."
    names = ", ".join(item["name"] for item in documents[:5])
    suffix = "" if count <= 5 else f", and {count - 5} more"
    noun = "file" if count == 1 else "files"
    return f"You have {count} {noun} ready for AI: {names}{suffix}."


def _remote_generate(
    payload: ToolRequest,
    document_context: str,
    documents: list[dict[str, str]],
) -> str | None:
    settings = get_settings()
    instruction = TOOL_INSTRUCTIONS[payload.tool]
    mode_line = f"\nRequested mode: {payload.mode}" if payload.mode else ""
    language_line = (
        f"\nTarget language: {payload.target_language}" if payload.target_language else ""
    )
    user_content = f"Text or request:\n{payload.text}{mode_line}{language_line}"
    messages = [
        {
            "role": "system",
            "content": (
                f"{instruction} Be practical and production-quality. "
                "Do not include unsupported claims. "
                f"Current date: {date.today().isoformat()}. "
                "If the user asks about uploaded documents, use the workspace document "
                "library context supplied below. If the context is insufficient, say so."
            ),
        }
    ]
    if document_context:
        document_names = ", ".join(item["name"] for item in documents[:8])
        messages.append(
            {
                "role": "system",
                "content": (
                    f"Workspace document library ({len(documents)} indexed): {document_names}\n\n"
                    f"{document_context}"
                ),
            }
        )
    messages.extend(
        {"role": item.role, "content": item.content[:2500]}
        for item in payload.history[-6:]
    )
    messages.append({"role": "user", "content": user_content})
    try:
        if settings.llm_provider == "groq" and settings.groq_api_key:
            request = urllib.request.Request(
                "https://api.groq.com/openai/v1/chat/completions",
                data=json.dumps(
                    {
                        "model": settings.groq_model,
                        "messages": messages,
                        "temperature": 0.35,
                        "max_completion_tokens": 1200,
                    }
                ).encode(),
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {settings.groq_api_key}",
                },
            )
            data = load_json(request, timeout=24, retries=0)
            return data["choices"][0]["message"]["content"].strip()
        if settings.llm_provider == "gemini" and settings.gemini_api_key:
            prompt = "\n\n".join(
                f"{message['role'].upper()}: {message['content']}" for message in messages
            )
            request = urllib.request.Request(
                "https://generativelanguage.googleapis.com/v1beta/models/"
                f"{settings.gemini_model}:generateContent?key={settings.gemini_api_key}",
                data=json.dumps({"contents": [{"parts": [{"text": prompt}]}]}).encode(),
                headers={"Content-Type": "application/json"},
            )
            data = load_json(request, timeout=24, retries=0)
            return data["candidates"][0]["content"]["parts"][0]["text"].strip()
    except Exception:
        return None
    return None


def _sentences(text: str) -> list[str]:
    cleaned = re.sub(r"\s+", " ", text).strip()
    return [part.strip() for part in re.split(r"(?<=[.!?])\s+", cleaned) if part.strip()]


def _extract_lab_lines(text: str) -> list[str]:
    lab_pattern = re.compile(
        r"\b(?:hemoglobin|glucose|cholesterol|hdl|ldl|triglycerides|wbc|rbc|"
        r"platelet|creatinine|urea|bilirubin|alt|ast|tsh|vitamin|sodium|"
        r"potassium|calcium|urine|blood|serum|protein|ketone|hba1c)\b|"
        r"\b\d+(?:\.\d+)?\s?(?:mg/dl|g/dl|mmol/l|iu/l|u/l|ng/ml|pg/ml|%)\b",
        re.IGNORECASE,
    )
    lines = [
        re.sub(r"\s+", " ", line).strip(" -")
        for line in text.splitlines()
        if re.sub(r"\s+", " ", line).strip(" -")
    ]
    matches = [line for line in lines if lab_pattern.search(line)]
    return matches[:12]


def _document_summary(documents: list[dict[str, str]]) -> str:
    if not documents:
        return "No indexed documents are available in this workspace yet."
    return "\n".join(
        f"- {item['name']}: {item['summary'] or item['type']}"
        for item in documents[:8]
    )


def _local_generate(
    payload: ToolRequest,
    document_context: str,
    documents: list[dict[str, str]],
) -> str:
    text = payload.text.strip()
    sentences = _sentences(text)
    sample = " ".join(sentences[:3]) if sentences else text
    count_answer = _document_count_answer(payload, documents)
    if count_answer:
        return count_answer
    wants_docs = bool(
        re.search(
            r"\b(uploaded|documents?|pdfs?|files?|library|resume|report|source)\b",
            text,
            re.IGNORECASE,
        )
    )
    if payload.tool == "chat":
        if wants_docs:
            return (
                "I can access your indexed workspace documents.\n\n"
                f"{_document_summary(documents)}"
            )
        return (
            "I can help with writing, summarizing, study material, and PDF analysis. "
            "For document-grounded answers, upload a file and open Investigator."
        )
    if payload.tool == "humanize":
        if wants_docs and document_context:
            sample = document_context[:900]
        return (
            "Here is a cleaner, more natural version:\n\n"
            f"{sample}\n\n"
            "Tip: replace generic phrases with specific examples, use active voice, "
            "and vary sentence length."
        )
    if payload.tool == "verify_ai":
        return (
            "AI-likeness review: medium confidence.\n\n"
            "- The text may sound generic if it lacks specific examples or personal context.\n"
            "- Add concrete details, vary sentence length, and remove repeated transition words.\n"
            "- Keep the strongest sentence and make the rest more direct."
        )
    if payload.tool in {"paraphrase", "correct"}:
        mode = payload.mode or "clear"
        return f"{mode.title()} version:\n\n{sample}"
    if payload.tool == "translate":
        language = payload.target_language or payload.mode or "the target language"
        return (
            f"Translation to {language} requires the configured AI provider. "
            "The original text is kept below for editing:\n\n"
            f"{text}"
        )
    if payload.tool == "quiz":
        basis = sentences[:5] or _sentences(document_context)[:5] or [text]
        return "\n\n".join(
            f"{index}. Which point is supported by the material?\n"
            f"A. {sentence[:120]}\nB. An unrelated claim\nC. A missing citation\n"
            f"D. None of the above\nAnswer: A\nExplanation: It appears directly in the supplied material."
            for index, sentence in enumerate(basis, start=1)
        )
    if payload.tool == "flashcards":
        basis = sentences[:8] or _sentences(document_context)[:8] or [text]
        return "\n\n".join(
            f"Q: What is a key point from section {index}?\nA: {sentence[:220]}"
            for index, sentence in enumerate(basis, start=1)
        )
    if payload.tool == "mind_map":
        mindmap_sentences = sentences[:6] or _sentences(document_context)[:6] or [text]
        branches = "\n".join(
            f"    Point {index}\n      {sentence[:70].replace(':', '-')}"
            for index, sentence in enumerate(mindmap_sentences, start=1)
        )
        return f"```mermaid\nmindmap\n  Study Material\n{branches}\n```"
    if payload.tool == "image_prompt":
        return (
            f"Create a high-quality image of {text}. Use a clean composition, realistic "
            "lighting, sharp detail, balanced color grading, and professional visual style. "
            "Avoid text artifacts, distorted faces, extra limbs, and low-resolution output."
        )
    if payload.tool == "document_draft":
        return (
            f"# {text[:90]}\n\n"
            "## Outline\n"
            "1. Introduction and context\n"
            "2. Main arguments or findings\n"
            "3. Evidence and examples\n"
            "4. Conclusion and next steps\n\n"
            "## Opening Draft\n"
            "This document introduces the topic, clarifies the objective, and organizes the "
            "main points into a clear structure for further editing."
        )
    if payload.tool == "healthcare_report":
        source_text = f"{text}\n{document_context}" if wants_docs else text
        lab_lines = _extract_lab_lines(source_text)
        values = "\n".join(f"- {line}" for line in lab_lines) or "- No clear biomarker values were detected in the pasted text."
        return (
            "Educational healthcare summary\n\n"
            "This is not medical advice and is not a diagnosis. Use it to prepare for a "
            "conversation with a licensed clinician.\n\n"
            "Values noticed:\n"
            f"{values}\n\n"
            "What to review:\n"
            "- Compare each value with the reference range printed on the original report.\n"
            "- Look for repeated abnormal markers across multiple reports rather than one value alone.\n"
            "- Consider symptoms, medications, fasting status, age, and medical history before drawing conclusions.\n\n"
            "Questions to ask your clinician:\n"
            "- Which values are outside the lab reference range?\n"
            "- Do any results require repeat testing or urgent follow-up?\n"
            "- Could diet, medication, hydration, or recent illness affect these numbers?"
        )
    return sample


def generate_tool_response(payload: ToolRequest, owner_id: str) -> ToolResponse:
    documents, document_context = _load_document_context(owner_id)
    deterministic_answer = _document_count_answer(payload, documents)
    result = (
        deterministic_answer
        or _remote_generate(payload, document_context, documents)
        or _local_generate(payload, document_context, documents)
    )
    return ToolResponse(result=result, provider=_provider_label())
