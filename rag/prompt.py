from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

from rag.retriever import RetrievedChunk

MAX_HISTORY_TURNS = 6

SYSTEM_PROMPT = """You are AgriWise, an assistant for smallholder farmers and agricultural \
extension workers in the CALABARZON region of the Philippines.

Rules:
- Answer only from the numbered manual excerpts provided in the user message. Do not use \
outside knowledge.
- Cite every claim with the bracketed tag of the excerpt it came from, for example \
[Farm Business School Manual, p.88].
- If the excerpts do not contain the answer, say so plainly and suggest contacting a local \
agricultural technician or the Department of Agriculture. Do not guess.
- Do not give medical, legal, or pesticide-dosage advice; refer the farmer to a local \
agricultural technician or the Department of Agriculture.
- Be concise, practical, and neutral."""


class ChatTurn(BaseModel):
    role: Literal["user", "assistant"]
    content: str


def _page_tag(chunk: RetrievedChunk) -> str:
    if chunk.page_start == chunk.page_end:
        pages = f"p.{chunk.page_start}"
    else:
        pages = f"p.{chunk.page_start}-{chunk.page_end}"
    return f"[{chunk.doc_title}, {pages}]"


def _excerpt_block(retrieved: list[RetrievedChunk]) -> str:
    if not retrieved:
        return "No manual excerpts were retrieved for this question."
    return "\n\n".join(f"{_page_tag(chunk)}\n{chunk.text}" for chunk in retrieved)


def build_messages(
    question: str,
    history: list[ChatTurn],
    retrieved: list[RetrievedChunk],
    analytics_context: str | None = None,
) -> list[dict]:
    messages: list[dict] = [{"role": "system", "content": SYSTEM_PROMPT}]
    if analytics_context:
        messages.append(
            {
                "role": "system",
                "content": f"Current AgriWise analytics context:\n{analytics_context}",
            }
        )
    for turn in history[-MAX_HISTORY_TURNS:]:
        messages.append({"role": turn.role, "content": turn.content})
    messages.append(
        {
            "role": "user",
            "content": f"Manual excerpts:\n\n{_excerpt_block(retrieved)}\n\nQuestion: {question}",
        }
    )
    return messages
