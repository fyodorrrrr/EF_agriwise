import type { Verdict } from "@/types/forecast";

type MetricKind = "demand" | "supply" | "price";

export const METRIC_INFO: Record<MetricKind, { label: string }> = {
  demand: {
    label: "Estimated Demand Proxy",
  },
  supply: {
    label: "Supply",
  },
  price: {
    label: "Price",
  },
};

export const VERDICT_MEANING: Record<Verdict, string> = {
  PASS: "This badge is about confidence, not the number itself — it means the forecast model behind this number met our accuracy bar.",
  USABLE_PROXY:
    "This badge is about confidence, not the number itself — it means this is a usable estimate, built as a proxy rather than measured directly.",
  CAUTION:
    "This badge is about confidence, not the number itself — treat it as a planning estimate, since recent results have been more variable than usual.",
  INDICATIVE_PROXY:
    "This badge is about confidence, not the number itself — it's an indicative trend only, with lower reliability than an estimate.",
  INSUFFICIENT_DATA:
    "This badge is about confidence, not the number itself — there isn't enough data yet to publish a reliable number here.",
};

const CLASSIFICATION_MEANING: Record<string, string> = {
  HIGH_OPPORTUNITY:
    "Compared to the other CALABARZON provinces, conditions here look the most favorable right now — demand, supply, and price signals are lining up well.",
  UNDERSUPPLY_LEANING:
    "Demand signals here look stronger relative to supply than in most other CALABARZON provinces — this crop may be scarcer than usual.",
  BALANCED:
    "Demand, supply, and price signals here are roughly in line with the CALABARZON average — no strong lean either way.",
  OVERSUPPLY_LEANING:
    "There's more of this crop available here than usual relative to demand and price signals — prices may be softer than normal.",
  SEVERE_OVERSUPPLY:
    "Supply looks well above demand here compared to the other CALABARZON provinces — expect the softest prices among the five.",
};

export function classificationLabel(classification: string | null): string {
  return classification?.replaceAll("_", " ").toLowerCase() ?? "";
}

export function classificationMeaning(classification: string | null): string {
  if (!classification) return "Not enough data to classify this province yet.";
  return (
    CLASSIFICATION_MEANING[classification] ??
    "Compares this province's demand, supply, price, and forecast reliability against the other CALABARZON provinces."
  );
}

export const OPPORTUNITY_SCORE_EXPLAINER =
  "This 0–100 score is not a percentage of anything physical. It's a ranking: how this province compares to the other four CALABARZON provinces on demand pressure, supply scarcity, price, and forecast reliability, combined into one number.";

export const OPPORTUNITY_FACTOR_LABELS: Record<string, string> = {
  demand_pressure_index: "Demand",
  supply_gap_or_scarcity_index: "Limited supply",
  price_opportunity_index: "Price",
  forecast_confidence_index: "Forecast reliability",
};

export function opportunityFactorLabel(key: string): string {
  return OPPORTUNITY_FACTOR_LABELS[key] ?? key.replaceAll("_", " ");
}

export const MARKET_FACTOR_LABELS: Record<string, string> = {
  proximity: "Distance from you",
  market_size_proxy: "Market size",
  data_reliability: "Data reliability",
  commodity_analytics_support: "Forecast data available",
};

export function marketFactorLabel(key: string): string {
  return MARKET_FACTOR_LABELS[key] ?? key.replaceAll("_", " ");
}

export const CONFIDENCE_LABEL: Record<string, string> = {
  HIGH: "High",
  MODERATE: "Moderate",
  NONE: "Not available",
};

export function confidenceLabel(confidence: string | null | undefined): string | null {
  if (!confidence) return null;
  return CONFIDENCE_LABEL[confidence] ?? confidence;
}

export const NO_SUPPLY_DEMAND_RATIO =
  "AgriWise does not calculate a direct “supply ÷ demand” percentage. Demand is measured in expenditure-index points and supply in metric tons — different kinds of units that can't honestly be divided into one ratio. The Opportunity Score above is the closest combined signal we publish: it weighs demand pressure, supply scarcity, price, and forecast confidence together as a ranking, not a physical gap.";
