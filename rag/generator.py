from __future__ import annotations

from functools import cached_property


class RagGenerationError(RuntimeError):
    pass


class Generator:
    def __init__(self, api_key: str, model: str, *, timeout_s: float = 30.0) -> None:
        self._api_key = api_key
        self._model = model
        self._timeout_s = timeout_s

    @cached_property
    def _client(self):
        from groq import Groq

        return Groq(api_key=self._api_key, timeout=self._timeout_s)

    def generate(self, messages: list[dict]) -> str:
        try:
            response = self._client.chat.completions.create(
                model=self._model, messages=messages, temperature=0.2
            )
        except Exception as exc:  # deliberately wrap any client failure
            raise RagGenerationError(str(exc)) from exc
        return response.choices[0].message.content or ""
