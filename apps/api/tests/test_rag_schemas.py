from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.schemas.rag import ChatMessage, RagQueryRequest, RagQueryResponse


def test_request_defaults_history_to_empty_list():
    req = RagQueryRequest(question="how to compost")
    assert req.history == []


def test_request_rejects_blank_question():
    with pytest.raises(ValidationError):
        RagQueryRequest(question="")


def test_request_rejects_overlong_question():
    with pytest.raises(ValidationError):
        RagQueryRequest(question="x" * 2001)


def test_chat_message_role_is_constrained():
    with pytest.raises(ValidationError):
        ChatMessage(role="system", content="nope")


def test_request_rejects_overlong_history():
    turns = [{"role": "user", "content": "hi"} for _ in range(51)]
    with pytest.raises(ValidationError):
        RagQueryRequest(question="ok", history=turns)


def test_response_shape():
    resp = RagQueryResponse(
        answer="Record expenses in a cash book.",
        citations=[
            {"doc_id": "fbs", "doc_title": "Farm Business School Manual",
             "page_start": 88, "page_end": 89}
        ],
    )
    assert resp.citations[0].page_end == 89
