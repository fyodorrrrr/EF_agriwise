from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from app.contacts import ContactInfo


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=4000)


class RagQueryRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    history: list[ChatMessage] = Field(default_factory=list, max_length=50)
    # Selectors only — the server resolves the actual analytics figures.
    commodity: str | None = Field(default=None, max_length=32)
    province: str | None = Field(default=None, max_length=32)


class Citation(BaseModel):
    doc_id: str
    doc_title: str
    page_start: int
    page_end: int


class RagQueryResponse(BaseModel):
    answer: str
    citations: list[Citation]
    analytics_context_used: bool = False
    # Human-readable scope of the analytics used, e.g. "Rice · Laguna",
    # "Tomato · all provinces", "CALABARZON overview". None when unused.
    analytics_scope: str | None = None
    # A real DA / provincial / municipal agriculture office for the farmer to
    # reach — attached when the bot could not fully answer, or the farmer asked.
    contact: ContactInfo | None = None
