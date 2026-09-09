"""Curated public-market directory.

Loads ``ml/artifacts/market_coordinates/*.csv`` once. Records with a missing or
out-of-range coordinate are dropped (recorded in ``diagnostics``); approximate
coordinates are kept as-is — nothing is fabricated.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

logger = logging.getLogger("agriwise.markets")

# CALABARZON bounding box (generous) — a sanity filter, not a precise clip.
_LAT_RANGE = (13.0, 15.2)
_LON_RANGE = (120.0, 122.3)
_PROVINCES = ("Batangas", "Cavite", "Laguna", "Quezon", "Rizal")

_MARKETS_CSV = "CALABARZON_market_directory.csv"
_KADIWA_FULL_CSV = "kadiwa_markets_full_registry_agriwise_schema.csv"
_CENTROIDS_CSV = "municipality_centroids.csv"
_CONFIG_REL = Path("config") / "market_recommendation_config.json"


@dataclass(frozen=True)
class MarketRecord:
    market_id: str
    market_name: str
    municipality: str
    province: str
    latitude: float
    longitude: float
    market_type: str | None
    operator: str | None
    coordinate_confidence: str
    source_url: str | None
    notes: str | None
    market_description: str | None = None
    contact_number: str | None = None
    facebook_url: str | None = None
    description_status_note: str | None = None


@dataclass(frozen=True)
class MarketRegistry:
    markets: tuple[MarketRecord, ...]
    config: dict
    diagnostics: tuple[str, ...] = field(default_factory=tuple)
    _centroids: dict[str, tuple[float, float]] = field(default_factory=dict)

    @classmethod
    def load(cls, artifacts_dir: Path) -> MarketRegistry:
        coords_dir = artifacts_dir / "market_coordinates"
        diagnostics: list[str] = []
        config = _read_json(artifacts_dir / _CONFIG_REL, diagnostics)

        seen: set[str] = set()
        markets = _load_markets(coords_dir / _MARKETS_CSV, diagnostics, seen)
        for source in _kadiwa_sources(coords_dir):
            markets.extend(_load_markets(source, diagnostics, seen))
        centroids = _load_centroids(coords_dir / _CENTROIDS_CSV, diagnostics)

        return cls(
            markets=tuple(markets),
            config=config,
            diagnostics=tuple(diagnostics),
            _centroids=centroids,
        )

    def for_province(self, province: str) -> list[MarketRecord]:
        return [m for m in self.markets if m.province == province]

    def province_centroid(self, province: str) -> tuple[float, float] | None:
        points = [
            self._centroids[key]
            for key in self._centroids
            if key.startswith(f"{province}|")
        ]
        if not points:
            # fall back to the mean of the province's own market coordinates
            pts = [(m.latitude, m.longitude) for m in self.for_province(province)]
            points = pts
        if not points:
            return None
        return (
            sum(p[0] for p in points) / len(points),
            sum(p[1] for p in points) / len(points),
        )


def _read_json(path: Path, diagnostics: list[str]) -> dict:
    try:
        return json.loads(path.read_text())
    except FileNotFoundError:
        diagnostics.append(f"config: {path.name} missing")
        return {}
    except (OSError, ValueError):
        diagnostics.append(f"config: {path.name} unreadable")
        return {}


def _kadiwa_sources(coords_dir: Path) -> list[Path]:
    """Prefer the full registry; otherwise load and de-duplicate KADIWA files."""
    full = coords_dir / _KADIWA_FULL_CSV
    if full.is_file():
        return [full]
    return sorted(
        path
        for path in coords_dir.glob("*.csv")
        if "kadiwa" in path.name.lower()
    )


def _load_markets(path: Path, diagnostics: list[str], seen: set[str]) -> list[MarketRecord]:
    if not path.is_file():
        diagnostics.append(f"{path.name} missing; market directory is empty")
        return []
    # Curated CSVs are UTF-8 (with or without a BOM), e.g. "Biñan"; some older
    # exports mix in cp1252 bytes that aren't valid UTF-8. Try UTF-8 first so
    # accented names decode correctly, and only fall back to latin-1 (which
    # never fails, but mangles multi-byte UTF-8 sequences) for those.
    try:
        frame = pd.read_csv(path, encoding="utf-8-sig", dtype=str).fillna("")
    except UnicodeDecodeError:
        frame = pd.read_csv(path, encoding="latin-1", dtype=str).fillna("")
    frame.columns = [c.lstrip("﻿ï»¿") for c in frame.columns]

    records: list[MarketRecord] = []
    for _, row in frame.iterrows():
        mid = row.get("market_id", "").strip()
        province = row.get("province", "").strip()
        if not mid or mid in seen:
            diagnostics.append(f"{path.name}: market row skipped: missing/duplicate id {mid!r}")
            continue
        if province not in _PROVINCES:
            diagnostics.append(f"{mid}: province {province!r} not in CALABARZON")
            continue
        try:
            lat = float(row["latitude"])
            lon = float(row["longitude"])
        except (KeyError, ValueError):
            diagnostics.append(f"{mid}: non-numeric coordinates, skipped")
            continue
        if not (_LAT_RANGE[0] <= lat <= _LAT_RANGE[1] and _LON_RANGE[0] <= lon <= _LON_RANGE[1]):
            diagnostics.append(f"{mid}: coordinates outside CALABARZON, skipped")
            continue

        seen.add(mid)
        confidence = (row.get("coordinate_confidence", "").strip() or "NEEDS_VERIFICATION").upper()
        records.append(
            MarketRecord(
                market_id=mid,
                market_name=row.get("market_name", "").strip() or mid,
                municipality=row.get("municipality_city", "").strip(),
                province=province,
                latitude=lat,
                longitude=lon,
                market_type=row.get("market_type", "").strip() or None,
                operator=row.get("operator", "").strip() or None,
                coordinate_confidence=confidence,
                source_url=row.get("source_url", "").strip() or None,
                notes=row.get("notes", "").strip() or None,
                market_description=row.get("market_description", "").strip() or None,
                contact_number=row.get("contact_number", "").strip() or None,
                facebook_url=row.get("facebook_url", "").strip() or None,
                description_status_note=row.get("description_status_note", "").strip() or None,
            )
        )
    return records


def _load_centroids(path: Path, diagnostics: list[str]) -> dict[str, tuple[float, float]]:
    if not path.is_file():
        diagnostics.append(f"{path.name} missing; using market-coordinate means")
        return {}
    frame = pd.read_csv(path)
    out: dict[str, tuple[float, float]] = {}
    for _, row in frame.iterrows():
        try:
            out[f"{row['province']}|{row['municipality_name']}"] = (
                float(row["latitude"]),
                float(row["longitude"]),
            )
        except (KeyError, ValueError, TypeError):
            continue
    return out
