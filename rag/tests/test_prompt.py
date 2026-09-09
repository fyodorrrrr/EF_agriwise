from __future__ import annotations

from rag.prompt import MAX_HISTORY_TURNS, SYSTEM_PROMPT, ChatTurn, build_messages
from rag.retriever import RetrievedChunk


def _chunk(title: str, ps: int, pe: int, text: str = "excerpt body") -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id=f"{title}::0", doc_id=title, doc_title=title,
        page_start=ps, page_end=pe, text=text, score=0.5,
    )


def test_system_prompt_first_and_rules_present():
    msgs = build_messages("q", [], [_chunk("Doc", 1, 1)])
    assert msgs[0] == {"role": "system", "content": SYSTEM_PROMPT}
    lowered = SYSTEM_PROMPT.lower()
    assert "cite" in lowered
    assert "do not" in lowered  # refusal / no-outside-knowledge language
    assert "estimated demand proxy" in lowered  # analytics-labelling rule
    assert "not available" in lowered  # refuse-to-estimate rule
    assert "greets you" in lowered  # small-talk / greeting rule


def test_citation_tags_use_page_ranges():
    msgs = build_messages("q", [], [_chunk("GAP Manual", 5, 5), _chunk("FBS Manual", 8, 9)])
    user = msgs[-1]["content"]
    assert "[GAP Manual, p.5]" in user
    assert "[FBS Manual, p.8-9]" in user
    assert user.rstrip().endswith("q")


def test_history_is_trimmed_to_max_turns():
    history = [ChatTurn(role="user", content=f"m{i}") for i in range(10)]
    msgs = build_messages("now", history, [_chunk("Doc", 1, 1)])
    history_msgs = [m for m in msgs if m["content"].startswith("m")]
    assert [m["content"] for m in history_msgs] == [f"m{i}" for i in range(4, 10)]
    assert len(history_msgs) == MAX_HISTORY_TURNS


def test_empty_retrieval_has_explicit_note():
    user = build_messages("q", [], [])[-1]["content"]
    assert "No manual excerpts were retrieved" in user


def test_analytics_context_is_separate_and_optional():
    without = build_messages("q", [], [_chunk("Doc", 1, 1)])
    assert [m["role"] for m in without] == ["system", "user"]

    with_ctx = build_messages(
        "q", [], [_chunk("Doc", 1, 1)], analytics_context="Rice demand: USABLE_PROXY"
    )
    ctx_msgs = [m for m in with_ctx if m["content"].startswith("FORECAST DATA")]
    assert len(ctx_msgs) == 1
    assert ctx_msgs[0]["role"] == "system"
    assert "Rice demand: USABLE_PROXY" in ctx_msgs[0]["content"]
    # ...and it is a distinct message, not folded into the excerpts/question turn
    assert "USABLE_PROXY" not in with_ctx[-1]["content"]
