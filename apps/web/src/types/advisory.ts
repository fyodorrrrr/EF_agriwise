import type { Confidence, Frequency, Province, Verdict } from "@/types/forecast";

export type AdvisoryType = "OPPORTUNITY" | "MARKET_WATCH" | "RISK" | "PRICE_UPDATE" | "MARKET_ACCESS";

export interface AdvisoryComponent {
  value: number | null;
  unit: string | null;
  frequency: Frequency | null;
  verdict: Verdict;
  confidence: Confidence | null;
  source: string | null;
  limitations: string[];
}

export interface AdvisoryRecord {
  commodity: string;
  province: Province;
  period: string | null;
  advisory_type: AdvisoryType;
  priority: number;
  headline: string;
  summary: string;
  farmer_consideration: string;
  opportunity: { score: number | null; classification: string | null };
  signals: { demand_growth_pct: number | null; supply_growth_pct: number | null; price_growth_pct: number | null; physical_gap: number | null; gap_ratio: number | null };
  demand: AdvisoryComponent;
  supply: AdvisoryComponent;
  price: AdvisoryComponent;
  markets: { market_id: string; market_name: string; municipality: string; market_type: string | null; coordinate_confidence: string; distance_km: number }[];
  confidence: Confidence;
  limitations: string[];
}

export interface AdvisoryResponse {
  province: Province;
  period: string | null;
  market_brief: Record<AdvisoryType, number>;
  advisories: AdvisoryRecord[];
}
