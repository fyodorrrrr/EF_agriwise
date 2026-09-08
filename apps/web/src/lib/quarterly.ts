import type { SeriesPoint } from "@/types/forecast";

// Mirrors `_quarter_start` / `_quarterly` in
// EF_agriwise/ml/forecasting/forecast_service.py — same bucketing so a
// monthly series (price) lines up with the natively quarterly series
// (demand, supply) on one chart.

export function quarterStart(iso: string): string {
  const [year, month] = iso.split("-").map(Number);
  const quarterMonth = Math.floor((month - 1) / 3) * 3 + 1;
  return `${String(year).padStart(4, "0")}-${String(quarterMonth).padStart(2, "0")}-01`;
}

export function toQuarterly(points: SeriesPoint[] | null): SeriesPoint[] {
  if (!points || points.length === 0) return [];
  const buckets = new Map<string, number[]>();
  for (const p of points) {
    const q = quarterStart(p.period);
    const values = buckets.get(q);
    if (values) values.push(p.value);
    else buckets.set(q, [p.value]);
  }
  return [...buckets.entries()]
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([period, values]) => ({
      period,
      value: values.reduce((sum, v) => sum + v, 0) / values.length,
    }));
}
