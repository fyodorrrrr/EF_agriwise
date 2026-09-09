"""Pull commodity/province mentions out of a free-text chat question.

The domain is closed — four commodities, five provinces — so this is
vocabulary matching, not NLP. Explicit selectors sent by the client always
take priority over anything found here; this only fills the gaps so a farmer
who types "price of tomato in Batangas" gets analytics without touching the
scope dropdowns.
"""

from __future__ import annotations

import re

from ml.forecasting.domain import COMMODITIES, PROVINCES

_COMMODITY_ALIASES: dict[str, tuple[str, ...]] = {
    "Rice": ("rice", "palay", "bigas"),
    "Tomato": ("tomato", "tomatoes", "kamatis"),
    "Red Onion": ("red onion", "red onions", "onion", "onions", "sibuyas"),
    "Banana": ("banana", "bananas", "saging"),
}

_PROVINCE_ALIASES: dict[str, tuple[str, ...]] = {
    "Batangas": ("batangas",),
    "Cavite": ("cavite",),
    "Laguna": ("laguna",),
    "Quezon": ("quezon",),
    "Rizal": ("rizal",),
}

# Question mentions something analytics-shaped but names no commodity — worth
# attaching the CALABARZON overview digest.
_OVERVIEW_TRIGGERS: tuple[str, ...] = (
    "plant", "planting", "grow", "growing", "profitable", "profit",
    "best crop", "what crop", "which crop", "what to plant", "which province",
    "opportunity", "demand", "forecast", "outlook", "price", "market", "sell",
    "selling", "season", "invest", "dashboard",
)

# Question is about where to sell / which market — attach the market ranking.
_MARKET_TRIGGERS: tuple[str, ...] = (
    "market", "markets", "sell", "selling", "sold", "buyer", "buyers",
    "where to sell", "palengke", "bagsakan", "talipapa", "trading post",
    "wholesale", "wholesaler", "bentahan", "pamilihan",
)


def _mentions(text: str, aliases: tuple[str, ...]) -> bool:
    return any(re.search(rf"\b{re.escape(alias)}\b", text) for alias in aliases)


def extract_entities(text: str) -> tuple[str | None, str | None]:
    """Return (commodity, province) found in the text, each or both may be None."""
    low = (text or "").lower()
    commodity = next(
        (c for c in COMMODITIES if _mentions(low, _COMMODITY_ALIASES[c])), None
    )
    province = next(
        (p for p in PROVINCES if _mentions(low, _PROVINCE_ALIASES[p])), None
    )
    return commodity, province


def wants_overview(text: str) -> bool:
    low = (text or "").lower()
    return any(trigger in low for trigger in _OVERVIEW_TRIGGERS)


def wants_markets(text: str) -> bool:
    low = (text or "").lower()
    return any(trigger in low for trigger in _MARKET_TRIGGERS)
