from __future__ import annotations

import sys
import types

import pytest

from rag.generator import Generator, RagGenerationError


class _Msg:
    def __init__(self, content):
        self.message = types.SimpleNamespace(content=content)


class _FakeCompletions:
    def __init__(self, *, content="hello", boom=False):
        self.content = content
        self.boom = boom
        self.calls: list[dict] = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        if self.boom:
            raise RuntimeError("groq is down")
        return types.SimpleNamespace(choices=[_Msg(self.content)])


class _FakeGroq:
    last: _FakeGroq | None = None

    def __init__(self, api_key=None, timeout=None):
        self.api_key = api_key
        self.timeout = timeout
        self.completions = _FakeCompletions()
        self.chat = types.SimpleNamespace(completions=self.completions)
        _FakeGroq.last = self


@pytest.fixture(autouse=True)
def _fake_groq(monkeypatch):
    module = types.ModuleType("groq")
    module.Groq = _FakeGroq
    monkeypatch.setitem(sys.modules, "groq", module)
    yield


def test_generate_passes_model_and_temperature():
    gen = Generator("sk-test", "openai/gpt-oss-120b")
    out = gen.generate([{"role": "user", "content": "hi"}])
    assert out == "hello"
    call = _FakeGroq.last.completions.calls[0]
    assert call["model"] == "openai/gpt-oss-120b"
    assert call["temperature"] == 0.2
    assert _FakeGroq.last.api_key == "sk-test"


def test_none_content_becomes_empty_string():
    gen = Generator("sk-test", "m")
    _FakeGroq.last = None
    gen.generate([{"role": "user", "content": "hi"}])
    _FakeGroq.last.completions.content = None
    assert gen.generate([{"role": "user", "content": "hi"}]) == ""


def test_client_errors_are_wrapped():
    gen = Generator("sk-test", "m")
    gen.generate([{"role": "user", "content": "hi"}])
    _FakeGroq.last.completions.boom = True
    with pytest.raises(RagGenerationError):
        gen.generate([{"role": "user", "content": "hi"}])
