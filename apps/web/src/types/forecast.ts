// Mirrors apps/api/app/schemas/forecast.py — keep the two in sync by hand.

export type Commodity = "Rice" | "Tomato" | "Red Onion" | "Banana";
export type Province = "Batangas" | "Cavite" | "Laguna" | "Quezon" | "Rizal";
export type Verdict =
  | "PASS"
  | "CAUTION"
  | "INSUFFICIENT_DATA"
  | "USABLE_PROXY"
  | "INDICATIVE_PROXY";
export type Frequency = "monthly" | "quarterly";
export type Confidence = "HIGH" | "MODERATE" | "NONE";
export type ForecastComponent = "demand" | "supply" | "price";

export interface CommodityProvincePair {
  commodity: Commodity;
  province: Province;
}

export interface CatalogResponse {
  commodities: Commodity[];
  provinces: Province[];
  pairs: CommodityProvincePair[];
}

export interface SeriesPoint {
  period: string; // ISO date, e.g. "2026-01-01"
  value: number;
}

export interface OutlookComponent {
  verdict: Verdict;
  observed: SeriesPoint[] | null;
  forecast: SeriesPoint[] | null;
  unit: string | null;
  frequency: Frequency | null;
  confidence: Confidence | null;
  source: string | null;
  data_as_of: string | null;
  label: string | null; // demand only
  limitations: string[];
  metrics: Record<string, number>;
}

export interface OpportunityBreakdownEntry {
  raw: number;
  score: number;
  weight: number;
}

export interface OpportunityComponent {
  verdict: Verdict;
  score: number | null;
  classification: string | null;
  shared_quarter: string | null;
  breakdown: Record<string, OpportunityBreakdownEntry>;
  weights_used: Record<string, number>;
}

export interface OutlookResponse {
  commodity: Commodity;
  province: Province;
  resolution_note: string;
  demand: OutlookComponent;
  supply: OutlookComponent;
  price: OutlookComponent;
  opportunity: OpportunityComponent;
}

export interface MunicipalOutlookRecord {
  psgc_code: string;
  municipality: string;
  demand_weight: number;
  demand_value: number;
  demand_unit: string;
  supply_weight: number;
  supply_mt: number | null;
  opportunity_score: number;
  opportunity_classification: string;
}

export interface MunicipalOutlookResponse {
  province: Province;
  commodity: Commodity;
  methodology: string;
  demand_unit: string;
  supply_unit: string;
  municipalities: MunicipalOutlookRecord[];
}

export interface EvidenceComponent {
  commodity: Commodity;
  component: ForecastComponent;
  target: string | null;
  model: string | null;
  verdict: Verdict;
  reason: string | null;
  frequency: Frequency | null;
  province_resolution: string;
  source: string | null;
  schema_version: string | null;
  metrics: Record<string, number>;
  baseline: Record<string, number>;
  province_holdout: Record<string, unknown>[];
  limitations: string[];
}

export interface EvidenceResponse {
  components: EvidenceComponent[];
}

export interface MethodologyResponse {
  schema_version: string | null;
  demand: Record<string, unknown>;
  supply: Record<string, unknown>;
  price: Record<string, unknown>;
  opportunity: Record<string, unknown>;
  commodity_flow: Record<string, unknown>;
  disclaimers: string[];
}
