// Mirrors ml/forecasting/domain.py — keep in sync by hand.
import type { Commodity, Province } from "@/types/forecast";

export const COMMODITIES: readonly Commodity[] = ["Rice", "Tomato", "Red Onion", "Banana"];
export const PROVINCES: readonly Province[] = [
  "Batangas",
  "Cavite",
  "Laguna",
  "Quezon",
  "Rizal",
];
