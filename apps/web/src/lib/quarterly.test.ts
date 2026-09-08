import { describe, expect, it } from "vitest";

import { quarterStart, toQuarterly } from "@/lib/quarterly";

describe("quarterStart", () => {
  it("maps a month to its quarter-start date", () => {
    expect(quarterStart("2026-02-15")).toBe("2026-01-01");
    expect(quarterStart("2026-04-01")).toBe("2026-04-01");
    expect(quarterStart("2026-12-31")).toBe("2026-10-01");
  });
});

describe("toQuarterly", () => {
  it("returns an empty array for null/empty input", () => {
    expect(toQuarterly(null)).toEqual([]);
    expect(toQuarterly([])).toEqual([]);
  });

  it("averages monthly points that fall in the same quarter, sorted ascending", () => {
    const result = toQuarterly([
      { period: "2026-03-01", value: 10 },
      { period: "2026-01-01", value: 20 },
      { period: "2026-02-01", value: 30 },
      { period: "2026-04-01", value: 40 },
    ]);
    expect(result).toEqual([
      { period: "2026-01-01", value: 20 },
      { period: "2026-04-01", value: 40 },
    ]);
  });

  it("passes already-quarterly points through unchanged", () => {
    const result = toQuarterly([
      { period: "2026-01-01", value: 1 },
      { period: "2026-04-01", value: 2 },
    ]);
    expect(result).toEqual([
      { period: "2026-01-01", value: 1 },
      { period: "2026-04-01", value: 2 },
    ]);
  });
});
