"""Single source of truth for the commodity/province domain vocabulary.

`apps/api/app/schemas/forecast.py` mirrors these as `Literal` types for
request/response validation; keep the two in sync by hand.
"""

from __future__ import annotations

COMMODITIES: tuple[str, ...] = ("Rice", "Tomato", "Red Onion", "Banana")
PROVINCES: tuple[str, ...] = ("Batangas", "Cavite", "Laguna", "Quezon", "Rizal")

COMPONENTS: tuple[str, ...] = ("demand", "supply", "price")
