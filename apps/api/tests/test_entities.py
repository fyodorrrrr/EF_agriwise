from __future__ import annotations

import pytest

from app.entities import extract_entities, wants_overview


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("what is the price outlook for rice in Laguna?", ("Rice", "Laguna")),
        ("kamatis sa Batangas", ("Tomato", "Batangas")),
        ("how are onions doing", ("Red Onion", None)),
        ("magkano ang saging", ("Banana", None)),
        ("palay prices", ("Rice", None)),
        ("how do I keep farm records?", (None, None)),
        ("", (None, None)),
    ],
)
def test_extract_entities(text, expected):
    assert extract_entities(text) == expected


def test_price_word_does_not_match_rice():
    assert extract_entities("what affects the price of vegetables") == (None, None)


def test_wants_overview_trigger_words():
    assert wants_overview("what is a good crop to plant this season") is True
    assert wants_overview("which province has the best opportunity") is True
    assert wants_overview("how do I compute gross margin") is False
