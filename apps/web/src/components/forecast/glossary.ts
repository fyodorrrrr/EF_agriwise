import type { Verdict } from "@/types/forecast";

type MetricKind = "demand" | "supply" | "price";

export const METRIC_INFO: Record<
  MetricKind,
  { label: string; whatItMeans: string; unitNote?: string }
> = {
  demand: {
    label: "Estimated Demand Proxy",
    whatItMeans:
      "This is not a percentage. It's a demand-pressure index built from household spending data: about 100 means a typical level for this area, higher means demand pressure is above normal, lower means below.",
  },
  supply: {
    label: "Supply",
    whatItMeans: "How much of this crop is available, in metric tons.",
    unitNote: "MT = metric tons = 1,000 kg.",
  },
  price: {
    label: "Price",
    whatItMeans: "The typical farmgate price for this crop.",
    unitNote: "₱/kg = pesos per kilogram.",
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

export const NO_SUPPLY_DEMAND_RATIO =
  "AgriWise does not calculate a direct “supply ÷ demand” percentage. Demand is measured in expenditure-index points and supply in metric tons — different kinds of units that can't honestly be divided into one ratio. The Opportunity Score above is the closest combined signal we publish: it weighs demand pressure, supply scarcity, price, and forecast confidence together as a ranking, not a physical gap.";
