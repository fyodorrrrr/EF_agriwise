"use client";

import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
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

/**
 * Observed history (solid) joined to a forecast segment (dashed), on a
 * shared quarterly x-axis. `quartersToShow` trims the forecast to however
 * many of the available future quarters the user asked to see (2–4) —
 * it never implies more quarters than the API actually returned.
 */
export function QuarterlyForecastChart({
  observed,
  forecast,
  unit,
  quartersToShow,
}: {
  observed: SeriesPoint[] | null;
  forecast: SeriesPoint[] | null;
  unit: string | null;
  quartersToShow: number;
}) {
  const obs = observed ?? [];
  const available = forecast ?? [];
  const fc = available.slice(0, quartersToShow);

  if (obs.length + fc.length < 2) return null;

  const shortBy = available.length < quartersToShow;

  const rows: ChartRow[] = obs.map((p) => ({ period: p.period, observed: p.value }));
  if (rows.length > 0 && fc.length > 0) {
    // Repeat the last observed value under the "forecast" key so the two
    // line segments visually connect at the boundary point.
    rows[rows.length - 1].forecast = rows[rows.length - 1].observed;
  }
  for (const p of fc) {
    rows.push({ period: p.period, forecast: p.value });
  }

  return (
    <div className="flex flex-col gap-1">
      <div style={{ width: "100%", height: 140 }}>
        <ResponsiveContainer>
          <LineChart data={rows} margin={{ top: 4, right: 8, bottom: 0, left: 0 }}>
            <CartesianGrid stroke="var(--color-viz-track)" vertical={false} />
            <XAxis
              dataKey="period"
              tickFormatter={formatQuarter}
              tick={{ fontSize: 11, fill: "var(--color-viz-muted)" }}
              axisLine={{ stroke: "var(--color-viz-track)" }}
              tickLine={false}
            />
            <YAxis
              width={48}
              tickFormatter={(v: number) => formatValue(v, unit)}
              tick={{ fontSize: 11, fill: "var(--color-viz-muted)" }}
              axisLine={false}
              tickLine={false}
            />
            <Tooltip
              labelFormatter={(label) => (typeof label === "string" ? formatQuarter(label) : label)}
              formatter={(value) => (typeof value === "number" ? formatValue(value, unit) : value)}
            />
            <Legend wrapperStyle={{ fontSize: 11 }} />
            <Line
              type="monotone"
              dataKey="observed"
              name="Observed"
              stroke="var(--color-viz-line)"
              strokeWidth={2}
              dot={{ r: 2 }}
              connectNulls
            />
            <Line
              type="monotone"
              dataKey="forecast"
              name="Forecast"
              stroke="var(--color-viz-line)"
              strokeWidth={2}
              strokeDasharray="4 3"
              dot={{ r: 2 }}
              connectNulls
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
      {shortBy && (
        <p className="text-xs text-muted">
          {available.length} of {quartersToShow} quarters available for this series.
        </p>
      )}
    </div>
  );
}
