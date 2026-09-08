from __future__ import annotations

from dataclasses import dataclass

_BREAKS = ("\n\n", "\n", ". ", " ")


@dataclass(frozen=True)
class PageText:
    doc_id: str
    doc_title: str
    page_number: int
    text: str


@dataclass(frozen=True)
class Chunk:
    chunk_id: str
    doc_id: str
    doc_title: str
    page_start: int
    page_end: int
    text: str


def _best_break(window: str) -> int:
    half = len(window) // 2
    for sep in _BREAKS:
        pos = window.rfind(sep)
        if pos > half:
            return pos + len(sep)
    return len(window)


def chunk_pages(pages: list[PageText], *, chunk_size: int, chunk_overlap: int) -> list[Chunk]:
    if not pages:
        return []
    doc_id = pages[0].doc_id
    doc_title = pages[0].doc_title

    parts: list[str] = []
    page_at: list[int] = []
    for page in pages:
        text = page.text.strip()
        if not text:
            continue
        if parts:
            parts.append("\n\n")
            page_at.extend([page.page_number, page.page_number])
        parts.append(text)
        page_at.extend([page.page_number] * len(text))
    full = "".join(parts)
    if not full:
        return []

    chunks: list[Chunk] = []
    start = 0
    index = 0
    length = len(full)
    while start < length:
        end = min(start + chunk_size, length)
        if end < length:
            end = start + _best_break(full[start:end])
        piece = full[start:end].strip()
        if piece:
            lo = page_at[min(start, len(page_at) - 1)]
            hi = page_at[min(end - 1, len(page_at) - 1)]
            chunks.append(
                Chunk(
                    chunk_id=f"{doc_id}::{index}",
                    doc_id=doc_id,
                    doc_title=doc_title,
                    page_start=min(lo, hi),
                    page_end=max(lo, hi),
                    text=piece,
                )
            )
            index += 1
        if end >= length:
            break
        start = max(end - chunk_overlap, start + 1)
    return chunks
