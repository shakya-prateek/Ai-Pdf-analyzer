import json
import re
import urllib.request
from typing import Any

from ..config import get_settings
from ..schemas import DocumentClassification
from .http_client import load_json


def _heuristic(text: str, has_tables: bool, file_type: str) -> dict[str, Any]:
    lower = text.lower()
    keyword_types = [
        ("invoice", ["invoice", "subtotal", "amount due", "bill to"]),
        ("resume", ["resume", "curriculum vitae", "work experience", "education", "skills"]),
        ("legal", ["agreement", "policy", "hereby", "terms and conditions", "liability"]),
        ("research_paper", ["abstract", "methodology", "references", "hypothesis"]),
        ("financial", ["balance sheet", "cash flow", "revenue", "fiscal year"]),
        ("medical", ["patient", "diagnosis", "prescription", "medical"]),
        ("report", ["report", "executive summary", "findings", "recommendations"]),
        ("handwritten_note", ["handwritten", "personal note", "reminder"]),
    ]
    document_type = "other"
    for candidate, keywords in keyword_types:
        if any(keyword in lower for keyword in keywords):
            document_type = candidate
            break

    topic_words = re.findall(r"\b[a-zA-Z][a-zA-Z-]{4,}\b", lower)
    stop = {"about", "their", "there", "which", "would", "these", "document", "page", "with", "from"}
    frequencies: dict[str, int] = {}
    for word in topic_words:
        if word not in stop:
            frequencies[word] = frequencies.get(word, 0) + 1
    topics = [word for word, _ in sorted(frequencies.items(), key=lambda item: (-item[1], item[0]))[:5]]

    sensitive_terms = ["patient", "diagnosis", "social security", "bank account", "confidential", "salary"]
    reasons = [term for term in sensitive_terms if term in lower]
    level = "high" if document_type == "medical" or len(reasons) > 1 else "medium" if reasons else "low"
    summary_source = re.sub(r"\s+", " ", text).strip()
    summary = summary_source[:280] + ("..." if len(summary_source) > 280 else "")
    return {
        "document_type": document_type,
        "topics": topics or [document_type.replace("_", " ")],
        "content_characteristics": {
            "has_tables": has_tables,
            "has_handwriting": document_type == "handwritten_note",
            "is_scanned": file_type in {"png", "jpg", "jpeg"} or len(text.strip()) < 80,
            "is_image_heavy": file_type in {"png", "jpg", "jpeg"},
            "language": "English",
        },
        "sensitivity": {"level": level, "reasons": reasons},
        "summary": summary or "No readable text was extracted.",
    }


def _prompt(text: str, has_tables: bool) -> str:
    return f"""Classify the document. Return JSON only with this exact shape:
{{
  "document_type": "invoice | report | resume | legal | handwritten_note | research_paper | financial | medical | other",
  "topics": ["string"],
  "content_characteristics": {{
    "has_tables": true,
    "has_handwriting": false,
    "is_scanned": false,
    "is_image_heavy": false,
    "language": "English"
  }},
  "sensitivity": {{"level": "low | medium | high", "reasons": ["string"]}},
  "summary": "short summary"
}}
Known table presence: {has_tables}
Document text:
{text[:12000]}"""


def _remote_classify(text: str, has_tables: bool) -> dict[str, Any] | None:
    settings = get_settings()
    prompt = _prompt(text, has_tables)
    try:
        if settings.llm_provider == "gemini" and settings.gemini_api_key:
            url = (
                "https://generativelanguage.googleapis.com/v1beta/models/"
                f"{settings.gemini_model}:generateContent?key={settings.gemini_api_key}"
            )
            payload = {"contents": [{"parts": [{"text": prompt}]}]}
            request = urllib.request.Request(
                url, data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"}
            )
            data = load_json(request)
            raw = data["candidates"][0]["content"]["parts"][0]["text"]
        elif settings.llm_provider == "groq" and settings.groq_api_key:
            payload = {
                "model": settings.groq_model,
                "messages": [{"role": "user", "content": prompt}],
                "response_format": {"type": "json_object"},
                "temperature": 0,
            }
            request = urllib.request.Request(
                "https://api.groq.com/openai/v1/chat/completions",
                data=json.dumps(payload).encode(),
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {settings.groq_api_key}",
                },
            )
            data = load_json(request)
            raw = data["choices"][0]["message"]["content"]
        else:
            return None
        raw = raw.strip().removeprefix("```json").removesuffix("```").strip()
        return json.loads(raw)
    except Exception:
        return None


def classify_document(text: str, has_tables: bool, file_type: str) -> dict[str, Any]:
    remote = (
        _remote_classify(text, has_tables)
        if get_settings().enable_ai_classification
        else None
    )
    if remote:
        try:
            return DocumentClassification.model_validate(remote).model_dump()
        except Exception:
            pass
    return DocumentClassification.model_validate(
        _heuristic(text, has_tables, file_type)
    ).model_dump()
