from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

from rag.chunking import PageText, chunk_pages
from rag.config import RagConfig

RAW_DIR = Path("data/raw")
MIN_PAGE_CHARS = 100

DOC_TITLES: dict[str, str] = {
    "BAFS_explanatory_manual": (
        "Explanatory Manual — PNS Code of GAP for Fruits and Vegetable Farming"
    ),
    "Farm_business_school_manual": "Farm Business School Manual",
    "PAFES_manual_of_operations": "PAFES Manual of Operations",
}

_HYPHEN_BREAK = re.compile(r"(\w)-\n(\w)")
_INLINE_WS = re.compile(r"[ \t]+")
_MANY_NEWLINES = re.compile(r"\n{3,}")


def clean_page(text: str) -> str:
    text = _HYPHEN_BREAK.sub(r"\1\2", text)
    text = _INLINE_WS.sub(" ", text)
    text = _MANY_NEWLINES.sub("\n\n", text)
    return text.strip()


def detect_running_lines(pages: list[str], *, min_fraction: float = 0.5) -> set[str]:
    counter: Counter[str] = Counter()
    for page in pages:
        seen = {ln.strip() for ln in page.splitlines() if 0 < len(ln.strip()) <= 80}
        counter.update(seen)
    threshold = max(3, int(len(pages) * min_fraction))
    return {line for line, count in counter.items() if count >= threshold}


def strip_running_lines(text: str, running: set[str]) -> str:
    kept = [line for line in text.splitlines() if line.strip() not in running]
    return "\n".join(kept).strip()


def extract_pages(pdf_path: Path) -> list[PageText]:
    from pypdf import PdfReader

    doc_id = pdf_path.stem
    title = DOC_TITLES.get(doc_id, doc_id)
    reader = PdfReader(str(pdf_path))
    return [
        PageText(doc_id=doc_id, doc_title=title, page_number=i, text=page.extract_text() or "")
        for i, page in enumerate(reader.pages, start=1)
    ]


def prepare_pages(raw_pages: list[PageText]) -> list[PageText]:
    cleaned = [clean_page(page.text) for page in raw_pages]
    running = detect_running_lines(cleaned)
    prepared: list[PageText] = []
    for page, text in zip(raw_pages, cleaned, strict=True):
        stripped = strip_running_lines(text, running)
        if len(stripped) < MIN_PAGE_CHARS:
            continue
        prepared.append(
            PageText(
                doc_id=page.doc_id,
                doc_title=page.doc_title,
                page_number=page.page_number,
                text=stripped,
            )
        )
    return prepared


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def ingest(
    cfg: RagConfig,
    *,
    sources: list[Path] | None = None,
    rebuild: bool = False,
) -> dict:
    from rag.embeddings import Embedder
    from rag.store import ChunkStore

    paths = sources if sources is not None else sorted(RAW_DIR.glob("*.pdf"))
    if not paths:
        raise SystemExit(f"no PDFs found in {RAW_DIR}")

    cfg.index_dir.mkdir(parents=True, exist_ok=True)
    embedder = Embedder(cfg.embedding_model)
    store = ChunkStore(cfg.index_dir, cfg.collection_name)
    if rebuild:
        store.reset()

    manifest: dict = {
        "embedding_model": cfg.embedding_model,
        "chunk_size": cfg.chunk_size,
        "chunk_overlap": cfg.chunk_overlap,
        "generated_at": datetime.now(UTC).isoformat(),
        "documents": {},
    }

    for path in paths:
        prepared = prepare_pages(extract_pages(path))
        chunks = chunk_pages(prepared, chunk_size=cfg.chunk_size, chunk_overlap=cfg.chunk_overlap)
        if not chunks:
            continue
        store.upsert(
            ids=[c.chunk_id for c in chunks],
            embeddings=embedder.embed([c.text for c in chunks]),
            documents=[c.text for c in chunks],
            metadatas=[
                {
                    "doc_id": c.doc_id,
                    "doc_title": c.doc_title,
                    "page_start": c.page_start,
                    "page_end": c.page_end,
                }
                for c in chunks
            ],
        )
        manifest["documents"][path.stem] = {"chunks": len(chunks), "sha256": _sha256(path)}

    (cfg.index_dir / "manifest.json").write_text(json.dumps(manifest, indent=2))
    return manifest


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Ingest AgriWise source PDFs into the RAG index.")
    parser.add_argument("--source", dest="sources", action="append", type=Path)
    parser.add_argument("--rebuild", action="store_true")
    args = parser.parse_args(argv)

    cfg = RagConfig.from_env()
    manifest = ingest(cfg, sources=args.sources, rebuild=args.rebuild)
    total = sum(doc["chunks"] for doc in manifest["documents"].values())
    print(
        f"ingested {total} chunks from {len(manifest['documents'])} document(s) -> {cfg.index_dir}"
    )


if __name__ == "__main__":
    main()
