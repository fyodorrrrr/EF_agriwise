export type BoundaryLevel = "region" | "province" | "municipality";

export interface BoundaryStyle {
  color: string;
  weight: number;
  fillColor?: string;
  fillOpacity: number;
}

const BOUNDARY_STYLES: Record<BoundaryLevel, BoundaryStyle> = {
  region: { color: "#df6b50", weight: 3, fillColor: "#df6b50", fillOpacity: 0.08 },
  province: { color: "#176b68", weight: 2, fillColor: "#176b68", fillOpacity: 0.05 },
  municipality: { color: "#c89b3c", weight: 1, fillOpacity: 0.03 },
};

export function boundaryStyle(level: BoundaryLevel): BoundaryStyle {
  return BOUNDARY_STYLES[level];
}

// Traces the exact clicked feature's shape in a bold black outline, rather
// than relying on the browser's default rectangular focus outline.
export function selectedBoundaryStyle(level: BoundaryLevel): BoundaryStyle {
  const base = BOUNDARY_STYLES[level];
  return { ...base, color: "#000000", weight: base.weight + 2, fillOpacity: 0.18 };
}

// "default": low->high, amber->red (Demand proxy -- no inherent good/bad direction).
// "goodHigh": low->high, red->green (Opportunity, Supply -- higher is better).
const HEAT_PALETTES = {
  default: ["#fde68a", "#fbbf24", "#f97316", "#dc2626"],
  goodHigh: ["#dc2626", "#f97316", "#facc15", "#16a34a"],
} as const;
export type HeatPalette = keyof typeof HEAT_PALETTES;

const NO_DATA_COLOR = "#d6d3d1";

/** Relative province color for the currently selected commodity and metric. */
export function heatColor(
  value: number | null,
  min: number,
  max: number,
  palette: HeatPalette = "default",
): string {
  if (value === null || !Number.isFinite(value)) return NO_DATA_COLOR;
  const ratio = max === min ? 0.5 : Math.max(0, Math.min(1, (value - min) / (max - min)));
  const index = ratio <= 0.25 ? 0 : ratio <= 0.5 ? 1 : ratio <= 0.75 ? 2 : 3;
  return HEAT_PALETTES[palette][index];
}

/** CSS gradient string for the legend bar, sharing the same palette as heatColor(). */
export function heatGradientCss(palette: HeatPalette = "default"): string {
  return `linear-gradient(90deg, ${HEAT_PALETTES[palette].join(", ")})`;
}
