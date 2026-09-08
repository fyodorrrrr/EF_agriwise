// Mirrors apps/api/app/schemas/forecast.py — keep the two in sync by hand.

export type Commodity = "Rice" | "Tomato" | "Red Onion" | "Banana";
export type Province = "Batangas" | "Cavite" | "Laguna" | "Quezon" | "Rizal";
export type Verdict = "PASS" | "CAUTION" | "INSUFFICIENT_DATA" | "USABLE_PROXY";
export type Frequency = "monthly" | "quarterly";
export type Confidence = "HIGH" | "MODERATE" | "NONE";

export interface CommodityProvincePair {
  commodity: Commodity;
  province: Province;
}

export interface CatalogResponse {
  commodities: Commodity[];
  provinces: Province[];
  pairs: CommodityProvincePair[];
}

export interface OutlookComponent {
  verdict: Verdict;
  values: number[] | null;
  unit: string | null;
  frequency: Frequency | null;
  confidence: Confidence | null;
  source: string | null;
  data_as_of: string | null;
  limitations: string[];
}

export interface OpportunityComponent {
  verdict: Verdict;
  score: number | null;
  classification: string | null;
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
