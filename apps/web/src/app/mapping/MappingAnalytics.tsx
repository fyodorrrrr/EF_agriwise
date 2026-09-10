"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { BrandLoader } from "@/components/BrandLoader";
import { formatValue } from "@/components/forecast/verdict";
import type { MunicipalMetric } from "@/components/map/CalabarzonMap";
import { MapPageClient } from "@/components/map/MapPageClient";
import { COMMODITIES, PROVINCES } from "@/lib/domain";
import { getMunicipalOutlook, getOutlook } from "@/lib/forecast";
import { heatColor, type HeatPalette } from "@/lib/gis/styles";
import { listMarkets } from "@/lib/markets";
import type {
  Commodity,
  MunicipalOutlookResponse,
  OutlookResponse,
  Province,
} from "@/types/forecast";
import type { MarketRecord } from "@/types/markets";

type Layer = "demand" | "supply" | "opportunity";
type GeographicView = "province" | "municipality";

const LAYERS: { id: Layer; label: string }[] = [
  { id: "demand", label: "Demand proxy" },
  { id: "supply", label: "Supply" },
  { id: "opportunity", label: "Opportunity" },
];

// Opportunity and Supply have a clear "higher is better" direction (green=high, red=low).
// Demand proxy has no such direction, so it keeps the neutral amber->red scale.
function paletteFor(layer: Layer): HeatPalette {
  return layer === "opportunity" || layer === "supply" ? "goodHigh" : "default";
}

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
  const [commodity, setCommodity] = useState<Commodity>("Rice");
  const [layer, setLayer] = useState<Layer>("demand");
  const [geographicView, setGeographicView] = useState<GeographicView>("province");
  const [result, setResult] = useState<{
    commodity: string;
    outlooks: Record<string, OutlookResponse>;
  } | null>(null);
  const [errorCommodity, setErrorCommodity] = useState<string | null>(null);
  const [markets, setMarkets] = useState<MarketRecord[]>([]);
  const [marketsError, setMarketsError] = useState(false);
  const [municipalResult, setMunicipalResult] = useState<{
    commodity: Commodity;
    outlooks: Record<Province, MunicipalOutlookResponse>;
  } | null>(null);
  const [municipalError, setMunicipalError] = useState<string | null>(null);

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

  useEffect(() => {
    if (geographicView !== "municipality") return;
    let cancelled = false;
    Promise.all(PROVINCES.map((province) => getMunicipalOutlook(commodity, province)))
      .then((responses) => {
        if (cancelled) return;
        setMunicipalResult({
          commodity,
          outlooks: Object.fromEntries(
            PROVINCES.map((province, index) => [province, responses[index]]),
          ) as Record<Province, MunicipalOutlookResponse>,
        });
      })
      .catch(() => !cancelled && setMunicipalError(commodity));
    return () => {
      cancelled = true;
    };
  }, [commodity, geographicView]);

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
  const provinceValues = present.map((row) => row.metric.value);
  const provinceMin = provinceValues.length ? Math.min(...provinceValues) : 0;
  const provinceMax = provinceValues.length ? Math.max(...provinceValues) : 0;
  const provinceUnit = present[0]?.metric.unit ?? null;
  const provinceMetrics = Object.fromEntries(
    rows.map(({ province, metric }) => [province, metric?.value ?? null]),
  );
  const layerLabel = LAYERS.find((item) => item.id === layer)?.label ?? layer;
  const palette = paletteFor(layer);

  const municipalOutlooks =
    municipalResult?.commodity === commodity ? municipalResult.outlooks : null;
  const municipalRecords = municipalOutlooks
    ? PROVINCES.flatMap((province) => municipalOutlooks[province].municipalities)
    : [];
  const municipalityMetrics: Record<string, MunicipalMetric> = Object.fromEntries(
    municipalRecords.map((municipality) => {
      if (layer === "demand") {
        return [
          municipality.psgc_code,
          {
            value: municipality.demand_value,
            unit: "%",
            label: "Synthetic Demand Share",
          },
        ];
      }
      if (layer === "supply") {
        return [
          municipality.psgc_code,
          {
            value: municipality.supply_mt,
            unit: "MT",
            label: "Synthetic Municipal Supply",
          },
        ];
      }
      return [
        municipality.psgc_code,
        {
          value: municipality.opportunity_score,
          unit: "/ 100",
          label: "Municipal Opportunity",
          classification: municipality.opportunity_classification,
        },
      ];
    }),
  );
  const municipalValues = Object.values(municipalityMetrics)
    .map((metric) => metric.value)
    .filter((value): value is number => value !== null && Number.isFinite(value));
  const municipalMin = municipalValues.length ? Math.min(...municipalValues) : 0;
  const municipalMax = municipalValues.length ? Math.max(...municipalValues) : 0;
  const municipalUnit = layer === "demand" ? "%" : layer === "supply" ? "MT" : "/ 100";
  const heatmapLabel =
    geographicView === "municipality"
      ? `${commodity} · ${layer === "demand" ? "Synthetic Demand Share" : layerLabel}`
      : `${commodity} · ${layerLabel}`;

  return (
    <div className="flex min-w-0 flex-col gap-4">
      <div className="card flex flex-col gap-3">
        <div className="card-head">
          <div>
            <span className="card-kicker">
              {geographicView === "province" ? "Province heatmap" : "Municipal heatmap"}
            </span>
            <p className="text-xs text-muted">
              {geographicView === "province"
                ? "Relative province-level values for the selected layer. A municipality on the map resolves to its province—this is never a municipality forecast."
                : "Synthetic municipal benchmarks for CALABARZON. Municipalities without a benchmark remain no-data."}
            </p>
          </div>
          <div className="flex w-full flex-col gap-1 sm:w-auto sm:items-end">
            <select
              aria-label="Commodity"
              className="select"
              value={commodity}
              onChange={(event) => setCommodity(event.target.value as Commodity)}
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

        <div className="flex flex-col gap-1">
          <span className="text-xs font-medium text-ink">Geographic View</span>
          <div className="chip-group">
            <button
              type="button"
              className="chip"
              aria-pressed={geographicView === "province"}
              onClick={() => setGeographicView("province")}
            >
              Provincial
            </button>
            <button
              type="button"
              className="chip"
              aria-pressed={geographicView === "municipality"}
              onClick={() => setGeographicView("municipality")}
            >
              Municipal
            </button>
          </div>
        </div>

        {error && (
          <p className="state state-error">Couldn&apos;t load province analytics.</p>
        )}
        {marketsError && (
          <p className="state state-error">Couldn&apos;t load market locations.</p>
        )}
        {geographicView === "municipality" && municipalError === commodity && (
          <p className="state state-error">Couldn&apos;t load the municipal benchmark.</p>
        )}
        {!error && !outlooks && <BrandLoader />}

        {outlooks && (
          <ul className="grid gap-x-6 gap-y-1 text-sm sm:grid-cols-2 lg:grid-cols-5">
            {rows.map(({ province, metric }) => (
              <li key={province} className="flex items-center justify-between gap-3">
                <span className="flex items-center gap-2">
                  <span
                    className="inline-block h-3 w-3 rounded-sm border border-[var(--color-divider)]"
                    style={{
                      background: heatColor(
                        metric?.value ?? null,
                        provinceMin,
                        provinceMax,
                        palette,
                      ),
                    }}
                  />
                  {province}
                </span>
                <span className="text-muted">
                  {metric
                    ? metric.unit === "score"
                      ? `${metric.value.toFixed(1)} out of 100`
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
        geographicView={geographicView}
        provinceMetrics={provinceMetrics}
        municipalityMetrics={municipalityMetrics}
        heatmapLabel={heatmapLabel}
        heatmapUnit={geographicView === "municipality" ? municipalUnit : provinceUnit}
        heatmapMin={geographicView === "municipality" ? municipalMin : provinceMin}
        heatmapMax={geographicView === "municipality" ? municipalMax : provinceMax}
        heatPalette={palette}
      />
    </div>
  );
}
