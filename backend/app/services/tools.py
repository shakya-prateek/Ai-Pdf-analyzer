import json
import re
import urllib.request

from ..config import get_settings
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
}


def _provider_label() -> str:
    settings = get_settings()
    if settings.llm_provider == "groq" and settings.groq_api_key:
        return f"groq:{settings.groq_model}"
    if settings.llm_provider == "gemini" and settings.gemini_api_key:
        return f"gemini:{settings.gemini_model}"
    return "local:fallback"


def _remote_generate(payload: ToolRequest) -> str | None:
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
                "Do not include unsupported claims."
            ),
        }
    ]
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


def _local_generate(payload: ToolRequest) -> str:
    text = payload.text.strip()
    sentences = _sentences(text)
    sample = " ".join(sentences[:3]) if sentences else text
    if payload.tool == "chat":
        return (
            "I can help with writing, summarizing, study material, and PDF analysis. "
            "For document-grounded answers, upload a file and open Investigator."
        )
    if payload.tool == "humanize":
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
        basis = sentences[:5] or [text]
        return "\n\n".join(
            f"{index}. Which point is supported by the material?\n"
            f"A. {sentence[:120]}\nB. An unrelated claim\nC. A missing citation\n"
            f"D. None of the above\nAnswer: A\nExplanation: It appears directly in the supplied material."
            for index, sentence in enumerate(basis, start=1)
        )
    if payload.tool == "flashcards":
        basis = sentences[:8] or [text]
        return "\n\n".join(
            f"Q: What is a key point from section {index}?\nA: {sentence[:220]}"
            for index, sentence in enumerate(basis, start=1)
        )
    if payload.tool == "mind_map":
        branches = "\n".join(
            f"    Point {index}\n      {sentence[:70].replace(':', '-')}"
            for index, sentence in enumerate((sentences[:6] or [text]), start=1)
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
    return sample


def generate_tool_response(payload: ToolRequest) -> ToolResponse:
    result = _remote_generate(payload) or _local_generate(payload)
    return ToolResponse(result=result, provider=_provider_label())
