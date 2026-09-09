"use client";

import type { CSSProperties } from "react";
import {
  CartesianGrid,
  Line,
  LineChart,
  ReferenceArea,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { formatQuarter, formatValue } from "@/components/forecast/verdict";
import type { SeriesPoint } from "@/types/forecast";

interface ChartRow {
  period: string;
  observed?: number;
  forecast?: number;
}

// A short number for the axis ticks that repeat down the whole chart — the
// fully spelled-out unit ("104 demand index") belongs on the tooltip and
// the caption text below, where it appears once, not on every gridline.
function axisTick(value: number, unit: string | null): string {
  const abs = Math.abs(value);
  const digits = abs >= 100 ? 0 : abs >= 1 ? 1 : 2;
  const rounded = value.toLocaleString(undefined, { maximumFractionDigits: digits });
  return unit === "PHP/kg" ? `₱${rounded}` : rounded;
}

/**
 * Observed history joined to a forecast segment on a shared quarterly
 * x-axis. The forecast quarters are shaded and marked off by a "Today"
 * line, so the split reads without a legend. `quartersToShow` trims the
 * forecast to however many of the available future quarters the caller
 * asked to see — it never implies more quarters than the API returned.
 */
export function QuarterlyForecastChart({
  observed,
  forecast,
  unit,
  quartersToShow,
  height = 140,
  showAvailabilityNote = true,
}: {
  observed: SeriesPoint[] | null;
  forecast: SeriesPoint[] | null;
  unit: string | null;
  quartersToShow: number;
  height?: number;
  /** Suppress the "N of M quarters available" note — only meaningful where
   * the caller lets someone pick a horizon (Forecasting's quarter chips). */
  showAvailabilityNote?: boolean;
}) {
  const obs = observed ?? [];
  const available = forecast ?? [];
  const fc = available.slice(0, quartersToShow);

  if (obs.length + fc.length < 2) return null;

  const shortBy = available.length < quartersToShow;
  const large = height >= 280;

  const rows: ChartRow[] = obs.map((p) => ({ period: p.period, observed: p.value }));
  const todayPeriod = rows.length > 0 ? rows[rows.length - 1].period : undefined;
  if (rows.length > 0 && fc.length > 0) {
    // Repeat the last observed value under the "forecast" key so the two
    // line segments visually connect at the boundary point.
    rows[rows.length - 1].forecast = rows[rows.length - 1].observed;
  }
  for (const p of fc) {
    rows.push({ period: p.period, forecast: p.value });
  }
  const lastPeriod = rows.length > 0 ? rows[rows.length - 1].period : undefined;

  return (
    <div className="flex flex-col gap-1">
      <div
        className={`chart-frame${large ? " chart-frame-lg" : ""}`}
        style={{ "--chart-height": `${height}px` } as CSSProperties}
      >
        <ResponsiveContainer>
          <LineChart data={rows} margin={{ top: 8, right: 12, bottom: 0, left: 0 }}>
            <CartesianGrid stroke="var(--color-viz-track)" vertical={false} />
            {fc.length > 0 && todayPeriod && lastPeriod && (
              <ReferenceArea
                x1={todayPeriod}
                x2={lastPeriod}
                fill="var(--color-viz-to)"
                fillOpacity={0.09}
                stroke="none"
              />
            )}
            <XAxis
              dataKey="period"
              tickFormatter={formatQuarter}
              tick={{ fontSize: large ? 12 : 11, fill: "var(--color-viz-muted)" }}
              axisLine={{ stroke: "var(--color-viz-track)" }}
              tickLine={false}
            />
            <YAxis
              width={large ? 56 : 48}
              tickFormatter={(v: number) => axisTick(v, unit)}
              tick={{ fontSize: large ? 12 : 11, fill: "var(--color-viz-muted)" }}
              axisLine={false}
              tickLine={false}
            />
            <Tooltip
              labelFormatter={(label) => (typeof label === "string" ? formatQuarter(label) : label)}
              formatter={(value) => (typeof value === "number" ? formatValue(value, unit) : value)}
            />
            {fc.length > 0 && todayPeriod && (
              <ReferenceLine
                x={todayPeriod}
                stroke="var(--color-viz-muted)"
                strokeDasharray="3 3"
                label={{
                  value: "Today",
                  position: "insideTopRight",
                  fill: "var(--color-viz-muted)",
                  fontSize: large ? 12 : 11,
                }}
              />
            )}
            <Line
              type="monotone"
              dataKey="observed"
              name="History"
              stroke="var(--color-viz-line)"
              strokeWidth={large ? 3 : 2}
              dot={{ r: large ? 3 : 2 }}
              connectNulls
            />
            <Line
              type="monotone"
              dataKey="forecast"
              name="Forecast"
              stroke="var(--color-viz-line)"
              strokeWidth={large ? 3 : 2}
              strokeDasharray="5 4"
              dot={{ r: large ? 3 : 2 }}
              connectNulls
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
      {showAvailabilityNote && shortBy && (
        <p className="text-xs text-muted">
          {available.length} of {quartersToShow} quarters available for this series.
        </p>
      )}
    </div>
  );
}
