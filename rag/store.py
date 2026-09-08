from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class StoredChunk:
    chunk_id: str
    text: str
    metadata: dict
    score: float


class ChunkStore:
    def __init__(self, index_dir: Path, collection_name: str) -> None:
        import chromadb

        self._name = collection_name
        self._client = chromadb.PersistentClient(path=str(index_dir))
        self._collection = self._client.get_or_create_collection(
            name=collection_name, metadata={"hnsw:space": "cosine"}
        )

    def upsert(
        self,
        *,
        ids: list[str],
        embeddings: list[list[float]],
        documents: list[str],
        metadatas: list[dict],
    ) -> None:
        # Convert empty dicts to None as Chroma doesn't accept empty metadata
        normalized_metadatas = [m if m else None for m in metadatas]
        self._collection.upsert(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=normalized_metadatas,
        )

    def query(self, embedding: list[float], top_k: int) -> list[StoredChunk]:
        res = self._collection.query(query_embeddings=[embedding], n_results=top_k)
        ids = res["ids"][0]
        documents = res["documents"][0]
        metadatas = res["metadatas"][0]
        distances = res["distances"][0]
        out: list[StoredChunk] = []
        for chunk_id, text, meta, distance in zip(
            ids, documents, metadatas, distances, strict=True
        ):
            out.append(
                StoredChunk(
                    chunk_id=chunk_id,
                    text=text,
                    metadata=dict(meta or {}),
                    score=max(0.0, 1.0 - float(distance)),
                )
            )
        return out

    def reset(self) -> None:
        self._client.delete_collection(self._name)
        self._collection = self._client.get_or_create_collection(
            name=self._name, metadata={"hnsw:space": "cosine"}
        )

    def count(self) -> int:
        return self._collection.count()
