// Mirrors apps/api/app/schemas/markets.py — keep in sync by hand.
import type { Commodity, Province } from "@/types/forecast";

export interface MarketRecord {
  market_id: string;
  market_name: string;
  municipality: string;
  province: Province;
  latitude: number;
  longitude: number;
  market_type: string | null;
  coordinate_confidence: string;
  source_url: string | null;
  notes: string | null;
}

export interface MarketListResponse {
  markets: MarketRecord[];
  diagnostics: string[];
}

export interface RankedMarket {
  market: MarketRecord;
  score: number;
  distance_km: number;
  breakdown: Record<string, { score: number; weight: number }>;
  why: string;
}

export interface MarketRankingResponse {
  commodity: Commodity;
  province: Province;
  supported_analytics: number; // 0-3
  ranked: RankedMarket[];
  policy: string[];
}
