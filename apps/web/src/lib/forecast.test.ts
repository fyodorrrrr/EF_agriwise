import { afterEach, describe, expect, it, vi } from "vitest";

import { getCatalog, getOutlook } from "@/lib/forecast";

afterEach(() => {
  vi.restoreAllMocks();
});

describe("getCatalog", () => {
  it("fetches /forecast/catalog", async () => {
    const payload = {
      commodities: ["Rice"],
      provinces: ["Laguna"],
      pairs: [{ commodity: "Rice", province: "Laguna" }],
    };
    const fetchMock = vi
      .fn()
      .mockResolvedValue(new Response(JSON.stringify(payload), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);

    await expect(getCatalog()).resolves.toEqual(payload);
    expect(fetchMock.mock.calls[0][0]).toContain("/forecast/catalog");
  });
});

describe("getOutlook", () => {
  it("passes commodity and province as query params", async () => {
    const payload = {
      commodity: "Red Onion",
      province: "Cavite",
      resolution_note: "Analytics are province-resolution.",
      demand: { verdict: "INSUFFICIENT_DATA", observed: null, forecast: null, limitations: [], metrics: {} },
      supply: { verdict: "INSUFFICIENT_DATA", observed: null, forecast: null, limitations: [], metrics: {} },
      price: { verdict: "INSUFFICIENT_DATA", observed: null, forecast: null, limitations: [], metrics: {} },
      opportunity: {
        verdict: "INSUFFICIENT_DATA",
        score: null,
        classification: null,
        shared_quarter: null,
        breakdown: {},
        weights_used: {},
      },
    };
    const fetchMock = vi
      .fn()
      .mockResolvedValue(new Response(JSON.stringify(payload), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);

    const result = await getOutlook("Red Onion", "Cavite");

    expect(result.opportunity.verdict).toBe("INSUFFICIENT_DATA");
    const url = fetchMock.mock.calls[0][0] as string;
    expect(url).toContain("/forecast/outlook?");
    expect(url).toContain("commodity=Red+Onion");
    expect(url).toContain("province=Cavite");
  });
});
