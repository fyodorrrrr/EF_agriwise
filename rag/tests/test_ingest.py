from __future__ import annotations

import json

import pytest

from rag.config import RagConfig
from rag.ingest import (
    clean_page,
    detect_running_lines,
    extract_pages,
    ingest,
    prepare_pages,
    strip_running_lines,
)


def test_clean_page_dehyphenates_and_collapses_whitespace():
    raw = "good agri-\nculture   practice\n\n\n\nnext line"
    cleaned = clean_page(raw)
    assert "agriculture practice" in cleaned
    assert "\n\n\n" not in cleaned
    assert "   " not in cleaned


def test_detect_and_strip_running_lines():
    pages = ["HEADER\nreal content one", "HEADER\nreal content two", "HEADER\nreal content three"]
    running = detect_running_lines(pages)
    assert "HEADER" in running
    assert strip_running_lines(pages[0], running).strip() == "real content one"


def test_prepare_pages_drops_short_pages():
    from rag.chunking import PageText

    raw = [
        PageText("d", "D", 1, "x " * 200),          # long -> kept
        PageText("d", "D", 2, "tiny"),               # short -> dropped
    ]
    prepared = prepare_pages(raw)
    assert [p.page_number for p in prepared] == [1]


def test_extract_pages_reads_text(make_pdf):
    pdf = make_pdf(
        "BAFS_explanatory_manual.pdf",
        ["Code of GAP for fruits and vegetables", "page two body"],
    )
    pages = extract_pages(pdf)
    assert len(pages) == 2
    assert pages[0].doc_id == "BAFS_explanatory_manual"
    assert pages[0].doc_title  # mapped title, non-empty
    assert "GAP" in pages[0].text


@pytest.mark.slow
def test_ingest_end_to_end_builds_index(make_pdf, tmp_path):
    pdf = make_pdf(
        "Farm_business_school_manual.pdf",
        [("Farm Business School teaches farmers to record every expense and every sale "
          "so that net income can be computed at the end of the season. ") * 6,
         ("A simple cash book has columns for the date, the item, money in, and money out. "
          "Totals are carried forward each week. ") * 6],
    )
    cfg = RagConfig(index_dir=tmp_path / "idx", chunk_size=500, chunk_overlap=50)
    manifest = ingest(cfg, sources=[pdf], rebuild=True)

    assert manifest["embedding_model"] == cfg.embedding_model
    assert manifest["documents"]["Farm_business_school_manual"]["chunks"] > 0
    assert (cfg.index_dir / "manifest.json").exists()
    saved = json.loads((cfg.index_dir / "manifest.json").read_text())
    assert saved["documents"] == manifest["documents"]

    from rag.store import ChunkStore

    store = ChunkStore(cfg.index_dir, cfg.collection_name)
    assert store.count() == manifest["documents"]["Farm_business_school_manual"]["chunks"]
    hits = store.query(
        __import__("rag.embeddings", fromlist=["Embedder"]).Embedder(cfg.embedding_model).embed_one(
            "how do I record farm expenses"
        ),
        top_k=2,
    )
    assert hits and hits[0].score > 0
