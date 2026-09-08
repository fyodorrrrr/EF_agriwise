from __future__ import annotations

import sys
import types
from typing import ClassVar

import pytest

from rag.embeddings import Embedder


class _FakeST:
    instances: ClassVar[list[str]] = []

    def __init__(self, model_name: str):
        self.model_name = model_name
        _FakeST.instances.append(model_name)

    def encode(self, texts, normalize_embeddings=False, batch_size=32):
        import numpy as np

        return np.array([[float(len(t)), 1.0, 0.0] for t in texts])


@pytest.fixture(autouse=True)
def _fake_sentence_transformers(monkeypatch):
    _FakeST.instances = []
    module = types.ModuleType("sentence_transformers")
    module.SentenceTransformer = _FakeST
    monkeypatch.setitem(sys.modules, "sentence_transformers", module)
    yield


def test_embed_empty_returns_empty_without_loading_model():
    embedder = Embedder("all-MiniLM-L6-v2")
    assert embedder.embed([]) == []
    assert _FakeST.instances == []


def test_embed_returns_plain_lists():
    embedder = Embedder("all-MiniLM-L6-v2")
    out = embedder.embed(["ab", "abcd"])
    assert out == [[2.0, 1.0, 0.0], [4.0, 1.0, 0.0]]
    assert isinstance(out[0], list)


def test_model_constructed_once_and_cached():
    embedder = Embedder("all-MiniLM-L6-v2")
    embedder.embed(["x"])
    embedder.embed_one("y")
    assert _FakeST.instances == ["all-MiniLM-L6-v2"]
