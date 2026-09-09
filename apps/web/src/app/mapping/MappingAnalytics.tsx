"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { BrandLoader } from "@/components/BrandLoader";
import { formatValue } from "@/components/forecast/verdict";
import { MapPageClient } from "@/components/map/MapPageClient";
import { COMMODITIES, PROVINCES } from "@/lib/domain";
import { getOutlook } from "@/lib/forecast";
import { heatColor } from "@/lib/gis/styles";
import { listMarkets } from "@/lib/markets";
import { usePreferences } from "@/lib/preferences";
import type { Commodity, OutlookResponse } from "@/types/forecast";
import type { MarketRecord } from "@/types/markets";

type Layer = "demand" | "supply" | "opportunity";

const LAYERS: { id: Layer; label: string }[] = [
  { id: "demand", label: "Demand proxy" },
  { id: "supply", label: "Supply" },
  { id: "opportunity", label: "Opportunity" },
];

function metricFor(
  outlook: OutlookResponse,
  layer: Layer,
): { value: number; unit: string | null } | null {
  if (layer === "opportunity") {
    return outlook.opportunity.score === null
      ? null
      : { value: outlook.opportunity.score, unit: "score" };
  }
  const component = outlook[layer];
  if (component.verdict === "INSUFFICIENT_DATA") return null;
  const series = component.forecast?.length
    ? component.forecast
    : (component.observed ?? []);
  return series.length
    ? { value: series[series.length - 1].value, unit: component.unit }
    : null;
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
  const [markets, setMarkets] = useState<MarketRecord[]>([]);
  const [marketsError, setMarketsError] = useState(false);

  useEffect(() => {
    let cancelled = false;
    listMarkets()
      .then((response) => {
        if (!cancelled) setMarkets(response.markets);
      })
      .catch(() => !cancelled && setMarketsError(true));
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    let cancelled = false;
    Promise.all(PROVINCES.map((province) => getOutlook(commodity, province)))
      .then((responses) => {
        if (cancelled) return;
        setResult({
          commodity,
          outlooks: Object.fromEntries(
            PROVINCES.map((province, index) => [province, responses[index]]),
          ),
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
    ? PROVINCES.map((province) => ({
        province,
        metric: metricFor(outlooks[province], layer),
      }))
    : [];
  const present = rows.filter((row) => row.metric !== null) as {
    province: string;
    metric: { value: number; unit: string | null };
  }[];
  const values = present.map((row) => row.metric.value);
  const min = values.length ? Math.min(...values) : 0;
  const max = values.length ? Math.max(...values) : 0;
  const unit = present[0]?.metric.unit ?? null;
  const provinceMetrics = Object.fromEntries(
    rows.map(({ province, metric }) => [province, metric?.value ?? null]),
  );
  const layerLabel = LAYERS.find((item) => item.id === layer)?.label ?? layer;

  return (
    <div className="flex flex-col gap-4">
      <div className="card flex flex-col gap-3">
        <div className="card-head">
          <div>
            <span className="card-kicker">Province heatmap</span>
            <p className="text-xs text-muted">
              Relative province-level values for the selected layer. A municipality on
              the map resolves to its province—this is never a municipality forecast.
            </p>
          </div>
          <div className="flex w-full flex-col gap-1 sm:w-auto sm:items-end">
            <select
              aria-label="Commodity"
              className="select"
              value={commodity}
              onChange={(event) => setOverride(event.target.value as Commodity)}
            >
              {COMMODITIES.map((item) => (
                <option key={item} value={item}>
                  {item}
                </option>
              ))}
            </select>
            <span className="text-xs text-muted">
              {markets.length} mapped {markets.length === 1 ? "market" : "markets"}
            </span>
          </div>
        </div>

        <div className="chip-group">
          {LAYERS.map((item) => (
            <button
              key={item.id}
              type="button"
              className="chip"
              aria-pressed={layer === item.id}
              onClick={() => setLayer(item.id)}
            >
              {item.label}
            </button>
          ))}
        </div>

        {error && (
          <p className="state state-error">Couldn&apos;t load province analytics.</p>
        )}
        {marketsError && (
          <p className="state state-error">Couldn&apos;t load market locations.</p>
        )}
        {!error && !outlooks && <BrandLoader />}

        {outlooks && (
          <ul className="grid gap-x-6 gap-y-1 text-sm sm:grid-cols-2 lg:grid-cols-5">
            {rows.map(({ province, metric }) => (
              <li key={province} className="flex items-center justify-between gap-3">
                <span className="flex items-center gap-2">
                  <span
                    className="inline-block h-3 w-3 rounded-sm border border-[var(--color-divider)]"
                    style={{ background: heatColor(metric?.value ?? null, min, max) }}
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

      <MapPageClient
        markets={markets}
        provinceMetrics={provinceMetrics}
        heatmapLabel={`${commodity} · ${layerLabel}`}
        heatmapUnit={unit}
        heatmapMin={min}
        heatmapMax={max}
      />
    </div>
  );
}
