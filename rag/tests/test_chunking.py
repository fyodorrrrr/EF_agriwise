from __future__ import annotations

from rag.chunking import Chunk, PageText, chunk_pages


def _pages(*texts: str, doc_id: str = "doc", title: str = "Doc") -> list[PageText]:
    return [
        PageText(doc_id=doc_id, doc_title=title, page_number=i, text=t)
        for i, t in enumerate(texts, start=1)
    ]


def test_empty_input_returns_empty():
    assert chunk_pages([], chunk_size=500, chunk_overlap=50) == []


def test_short_single_page_is_one_chunk():
    chunks = chunk_pages(_pages("Record every farm expense in the ledger."),
                         chunk_size=500, chunk_overlap=50)
    assert len(chunks) == 1
    assert isinstance(chunks[0], Chunk)
    assert chunks[0].chunk_id == "doc::0"
    assert chunks[0].page_start == 1 and chunks[0].page_end == 1
    assert "farm expense" in chunks[0].text


def test_long_text_splits_with_size_and_overlap():
    body = ". ".join(f"sentence number {n} about good agricultural practice" for n in range(60))
    chunks = chunk_pages(_pages(body), chunk_size=200, chunk_overlap=40)
    assert len(chunks) > 3
    for c in chunks:
        assert len(c.text) <= 240  # size + tolerance for the break search window
    # consecutive chunks overlap somewhere
    assert chunks[0].text[-20:] in (chunks[1].text[:120] + chunks[1].text)
    # ids are sequential
    assert [c.chunk_id for c in chunks] == [f"doc::{i}" for i in range(len(chunks))]


def test_page_span_tracks_source_pages():
    p1 = "alpha " * 60          # ~360 chars
    p2 = "bravo " * 60
    chunks = chunk_pages(_pages(p1, p2), chunk_size=200, chunk_overlap=20)
    assert chunks[0].page_start == 1
    assert chunks[-1].page_end == 2
    assert any(c.page_start == 1 and c.page_end == 2 for c in chunks) or (
        chunks[0].page_end == 1 and chunks[-1].page_start == 2
    )


def test_blank_pages_are_skipped_in_concatenation():
    chunks = chunk_pages(_pages("real content here about GAP", "   ", "more real content"),
                         chunk_size=500, chunk_overlap=50)
    assert len(chunks) == 1
    assert "GAP" in chunks[0].text and "more real content" in chunks[0].text
