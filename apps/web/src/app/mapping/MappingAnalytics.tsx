"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { formatValue } from "@/components/forecast/verdict";
import { COMMODITIES, PROVINCES } from "@/lib/domain";
import { getOutlook } from "@/lib/forecast";
import { usePreferences } from "@/lib/preferences";
import type { Commodity, OutlookResponse } from "@/types/forecast";

type Layer = "demand" | "supply" | "price" | "opportunity";
const LAYERS: { id: Layer; label: string }[] = [
  { id: "demand", label: "Demand proxy" },
  { id: "supply", label: "Supply" },
  { id: "price", label: "Price" },
  { id: "opportunity", label: "Opportunity" },
];

function metricFor(outlook: OutlookResponse, layer: Layer): { value: number; unit: string | null } | null {
  if (layer === "opportunity") {
    return outlook.opportunity.score === null
      ? null
      : { value: outlook.opportunity.score, unit: "score" };
  }
  const c = outlook[layer];
  if (c.verdict === "INSUFFICIENT_DATA") return null;
  const series = c.forecast?.length ? c.forecast : c.observed ?? [];
  return series.length ? { value: series[series.length - 1].value, unit: c.unit } : null;
}

// Relative shade within the visible provinces — a legend cue, not a choropleth.
function shade(value: number, min: number, max: number): string {
  const t = max === min ? 0.5 : (value - min) / (max - min);
  const lightness = 88 - t * 45;
  return `hsl(168 40% ${lightness}%)`;
}

export function MappingAnalytics() {
  const { preferences, isHydrated } = usePreferences();
  const [override, setOverride] = useState<Commodity | null>(null);
  const commodity = override ?? preferences.commodity ?? "Rice";
  const [layer, setLayer] = useState<Layer>("demand");
  const [result, setResult] = useState<{
    commodity: string;
    outlooks: Record<string, OutlookResponse>;
  } | null>(null);
  const [errorCommodity, setErrorCommodity] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    Promise.all(PROVINCES.map((p) => getOutlook(commodity, p)))
      .then((res) => {
        if (cancelled) return;
        setResult({
          commodity,
          outlooks: Object.fromEntries(PROVINCES.map((p, i) => [p, res[i]])),
        });
      })
      .catch(() => !cancelled && setErrorCommodity(commodity));
    return () => {
      cancelled = true;
    };
  }, [commodity]);

  if (!isHydrated) return null;

  const outlooks = result?.commodity === commodity ? result.outlooks : null;
  const error = errorCommodity === commodity;

  const rows = outlooks
    ? PROVINCES.map((p) => ({ province: p, metric: metricFor(outlooks[p], layer) }))
    : [];
  const present = rows.filter((r) => r.metric !== null) as {
    province: string;
    metric: { value: number; unit: string | null };
  }[];
  const values = present.map((r) => r.metric.value);
  const min = Math.min(...values);
  const max = Math.max(...values);

  return (
    <div className="card flex flex-col gap-3">
      <div className="card-head">
        <div>
          <span className="card-kicker">Province analytics</span>
          <p className="text-xs text-muted">
            Province-resolution values for the selected layer. A municipality on the map
            resolves to its province — this is never a municipality forecast.
          </p>
        </div>
        <div className="flex gap-2">
          <select
            aria-label="Commodity"
            className="input-bare border rounded-md px-2 py-1 text-sm"
            value={commodity}
            onChange={(e) => setOverride(e.target.value as Commodity)}
          >
            {COMMODITIES.map((c) => (
              <option key={c} value={c}>
                {c}
              </option>
            ))}
          </select>
        </div>
      </div>

      <div className="chip-group">
        {LAYERS.map((l) => (
          <button
            key={l.id}
            type="button"
            className="chip"
            aria-pressed={layer === l.id}
            onClick={() => setLayer(l.id)}
          >
            {l.label}
          </button>
        ))}
      </div>

      {error && <p className="state state-error">Couldn&apos;t load province analytics.</p>}
      {!error && !outlooks && <p className="state state-loading">Loading…</p>}

      {outlooks && (
        <ul className="flex flex-col gap-1 text-sm">
          {rows.map(({ province, metric }) => (
            <li key={province} className="flex items-center justify-between gap-3">
              <span className="flex items-center gap-2">
                <span
                  className="inline-block h-3 w-3 rounded-sm border border-[var(--color-divider)]"
                  style={{
                    background: metric ? shade(metric.value, min, max) : "transparent",
                  }}
                />
                {province}
              </span>
              <span className="text-muted">
                {metric
                  ? metric.unit === "score"
                    ? metric.value.toFixed(1)
                    : formatValue(metric.value, metric.unit)
                  : "not available"}
              </span>
            </li>
          ))}
        </ul>
      )}

      <Link href="/forecasting" className="btn btn-ghost btn-sm self-start text-xs">
        Open in Forecasting →
      </Link>
    </div>
  );
}
