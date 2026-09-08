import type { SeriesPoint } from "@/types/forecast";

/**
 * A minimal observed→forecast sparkline. The forecast segment is dashed and
 * the boundary point is marked. Renders nothing when there are fewer than two
 * points total.
 */
export function Sparkline({
  observed,
  forecast,
  width = 160,
  height = 40,
}: {
  observed: SeriesPoint[] | null;
  forecast: SeriesPoint[] | null;
  width?: number;
  height?: number;
}) {
  const obs = observed ?? [];
  const fc = forecast ?? [];
  const all = [...obs, ...fc];
  if (all.length < 2) return null;

  const values = all.map((p) => p.value);
  const min = Math.min(...values);
  const max = Math.max(...values);
  const span = max - min || 1;
  const pad = 3;

  const x = (i: number) => pad + (i / (all.length - 1)) * (width - 2 * pad);
  const y = (v: number) => height - pad - ((v - min) / span) * (height - 2 * pad);

  const line = (pts: SeriesPoint[], offset: number) =>
    pts.map((p, i) => `${i === 0 ? "M" : "L"} ${x(i + offset)} ${y(p.value)}`).join(" ");

  const obsPath = obs.length >= 1 ? line(obs, 0) : "";
  // start the forecast path at the last observed point so the segments join
  const fcPath =
    fc.length >= 1 && obs.length >= 1
      ? line([obs[obs.length - 1], ...fc], obs.length - 1)
      : fc.length >= 1
        ? line(fc, obs.length)
        : "";

  return (
    <svg
      width={width}
      height={height}
      viewBox={`0 0 ${width} ${height}`}
      role="img"
      aria-label="Trend"
      className="text-[var(--color-accent-500)]"
    >
      {obsPath && (
        <path d={obsPath} fill="none" stroke="currentColor" strokeWidth={1.5} />
      )}
      {fcPath && (
        <path
          d={fcPath}
          fill="none"
          stroke="currentColor"
          strokeWidth={1.5}
          strokeDasharray="3 2"
          opacity={0.7}
        />
      )}
      {obs.length >= 1 && (
        <circle cx={x(obs.length - 1)} cy={y(obs[obs.length - 1].value)} r={2} fill="currentColor" />
      )}
    </svg>
  );
}
