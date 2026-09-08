from __future__ import annotations

from functools import cached_property


class Embedder:
    def __init__(self, model_name: str) -> None:
        self.model_name = model_name

    @cached_property
    def _model(self):
        from sentence_transformers import SentenceTransformer

        return SentenceTransformer(self.model_name)

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        vectors = self._model.encode(texts, normalize_embeddings=True, batch_size=32)
        return [list(map(float, row)) for row in vectors]

    def embed_one(self, text: str) -> list[float]:
        return self.embed([text])[0]
