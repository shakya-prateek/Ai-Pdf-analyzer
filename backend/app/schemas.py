from typing import Literal

from pydantic import BaseModel, Field


class HistoryMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=8000)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    history: list[HistoryMessage] = Field(default_factory=list, max_length=20)


class Citation(BaseModel):
    document_name: str
    page_number: int
    page_image_url: str
    quoted_text: str


class ChatResponse(BaseModel):
    answer: str
    citations: list[Citation]


class ToolRequest(BaseModel):
    tool: Literal[
        "chat",
        "humanize",
        "verify_ai",
        "paraphrase",
        "correct",
        "translate",
        "quiz",
        "flashcards",
        "mind_map",
        "image_prompt",
        "document_draft",
    ]
    text: str = Field(min_length=1, max_length=12000)
    mode: str | None = Field(default=None, max_length=80)
    target_language: str | None = Field(default=None, max_length=80)
    history: list[HistoryMessage] = Field(default_factory=list, max_length=12)


class ToolResponse(BaseModel):
    result: str
    provider: str


class ContentCharacteristics(BaseModel):
    has_tables: bool
    has_handwriting: bool
    is_scanned: bool
    is_image_heavy: bool
    language: str = Field(min_length=1, max_length=80)


class Sensitivity(BaseModel):
    level: Literal["low", "medium", "high"]
    reasons: list[str] = Field(default_factory=list, max_length=20)


class DocumentClassification(BaseModel):
    document_type: Literal[
        "invoice",
        "report",
        "resume",
        "legal",
        "handwritten_note",
        "research_paper",
        "financial",
        "medical",
        "other",
    ]
    topics: list[str] = Field(default_factory=list, max_length=20)
    content_characteristics: ContentCharacteristics
    sensitivity: Sensitivity
    summary: str = Field(min_length=1, max_length=1200)
