import type { Verdict } from "@/types/forecast";

const BADGE: Record<Verdict, string> = {
  PASS: "badge-leaf",
  USABLE_PROXY: "badge-info",
  CAUTION: "badge-warn",
  INDICATIVE_PROXY: "badge-warn",
  INSUFFICIENT_DATA: "badge-neutral",
};

const LABEL: Record<Verdict, string> = {
  PASS: "Pass",
  USABLE_PROXY: "Usable proxy",
  CAUTION: "Caution",
  INDICATIVE_PROXY: "Indicative proxy",
  INSUFFICIENT_DATA: "Insufficient data",
};

export function verdictBadgeClass(verdict: Verdict): string {
  return `badge ${BADGE[verdict]}`;
}

export function verdictLabel(verdict: Verdict): string {
  return LABEL[verdict];
}

export function formatValue(value: number, unit: string | null): string {
  const abs = Math.abs(value);
  const digits = abs >= 100 ? 0 : abs >= 1 ? 1 : 2;
  const rounded = value.toLocaleString(undefined, { maximumFractionDigits: digits });
  if (!unit) return rounded;
  if (unit.startsWith("index")) return `${rounded}`;
  if (unit === "PHP/kg") return `₱${rounded}/kg`;
  if (unit === "MT") return `${rounded} MT`;
  return `${rounded} ${unit}`;
}

export function formatQuarter(iso: string): string {
  const [year, month] = iso.split("-").map(Number);
  return `Q${Math.floor((month - 1) / 3) + 1} ${year}`;
}
