from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=4000)


class RagQueryRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    history: list[ChatMessage] = Field(default_factory=list, max_length=50)


class Citation(BaseModel):
    doc_id: str
    doc_title: str
    page_start: int
    page_end: int


class RagQueryResponse(BaseModel):
    answer: str
    citations: list[Citation]
