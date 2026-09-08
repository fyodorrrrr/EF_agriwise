import { describe, expect, it } from "vitest";

import * as styles from "@/lib/gis/styles";

type HeatColor = (value: number | null, min: number, max: number) => string;

describe("heatColor", () => {
  it("uses a yellow-to-red scale and a neutral color for unavailable data", () => {
    const heatColor = (styles as typeof styles & { heatColor?: HeatColor }).heatColor;

    expect(heatColor).toBeTypeOf("function");
    expect(heatColor?.(10, 10, 50)).toBe("#fde68a");
    expect(heatColor?.(30, 10, 50)).toBe("#fbbf24");
    expect(heatColor?.(50, 10, 50)).toBe("#dc2626");
    expect(heatColor?.(null, 10, 50)).toBe("#d6d3d1");
  });
});
