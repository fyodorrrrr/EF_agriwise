"""Escalation contacts — DA regional, provincial (OPAg), and city/municipal
agriculture offices for CALABARZON. Loaded from a small verified CSV and looked
up by province/municipality; deliberately NOT part of the RAG index.

Used when the chatbot cannot fully answer a farmer's question, so it can hand
the farmer a real person to call instead of a dead end.
"""

from __future__ import annotations

import csv
from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel

from ml.forecasting.domain import PROVINCES

_CSV = Path("data/raw/CALABARZON_Agricultural_Extension_Contacts.csv")
_HEAD_WORDS = (
    "agriculturist", "head", "chief", "director", "coordinator",
    "officer-in-charge", "oic",
)


class ContactInfo(BaseModel):
    name: str
    position: str
    organization: str
    office: str
    phone: str
    email: str
    how_to_reach: str
    verified: str
    scope: str  # e.g. "Batangas City", "Laguna province", "DA CALABARZON (regional)"


@lru_cache(maxsize=1)
def _rows() -> list[dict]:
    if not _CSV.exists():
        return []
    with _CSV.open(encoding="utf-8-sig", newline="") as handle:
        return [
            {k: (v or "").strip() for k, v in row.items()}
            for row in csv.DictReader(handle)
        ]


@lru_cache(maxsize=1)
def municipalities() -> tuple[str, ...]:
    return tuple(
        sorted(
            {
                r["city_municipality"]
                for r in _rows()
                if r["level"] in ("City", "Municipal") and r["city_municipality"]
            }
        )
    )


def municipality_in(text: str) -> str | None:
    low = (text or "").lower()
    return next((m for m in municipalities() if m.lower() in low), None)


def _is_head(position: str) -> bool:
    low = position.lower()
    return any(word in low for word in _HEAD_WORDS)


def _to_contact(row: dict, scope: str) -> ContactInfo:
    return ContactInfo(
        name=row["contact_person"],
        position=row["position"],
        organization=row["organization"],
        office=row["office_or_unit"],
        phone=row["phone"],
        email=row["email"],
        how_to_reach=row["services_notes"],
        verified=row["source_freshness"],
        scope=scope,
    )


def find_contact(
    province: str | None, municipality: str | None = None
) -> ContactInfo | None:
    """Most specific match wins: municipal office → provincial OPAg → APCO →
    the DA CALABARZON regional line."""
    rows = _rows()
    if not rows:
        return None

    if municipality:
        muni = [
            r
            for r in rows
            if r["level"] in ("City", "Municipal")
            and r["city_municipality"].lower() == municipality.lower()
        ]
        if muni:
            muni.sort(key=lambda r: 0 if _is_head(r["position"]) else 1)
            return _to_contact(muni[0], municipality)

    if province in PROVINCES:
        provincial = [
            r for r in rows if r["level"] == "Provincial" and r["province"] == province
        ]
        if provincial:
            return _to_contact(provincial[0], f"{province} province")
        apco = [
            r for r in rows if "APCO" in r["office_or_unit"] and r["province"] == province
        ]
        if apco:
            return _to_contact(apco[0], f"{province} province")

    regional = [
        r
        for r in rows
        if r["level"] == "Regional" and "Regional Field Office" in r["organization"]
    ]
    return _to_contact(regional[0] if regional else rows[0], "DA CALABARZON (regional)")
