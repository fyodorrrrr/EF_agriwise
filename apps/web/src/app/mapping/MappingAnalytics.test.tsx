import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";

import { MappingAnalytics } from "@/app/mapping/MappingAnalytics";
import { AppPreferencesProvider } from "@/lib/preferences";
import type { OutlookResponse } from "@/types/forecast";

vi.mock("@/lib/forecast", () => ({ getOutlook: vi.fn() }));
vi.mock("@/lib/markets", () => ({ listMarkets: vi.fn() }));
vi.mock("@/components/map/MapPageClient", () => ({ MapPageClient: () => null }));
import { getOutlook } from "@/lib/forecast";
import { listMarkets } from "@/lib/markets";

function outlook(province: string, supplyOk: boolean): OutlookResponse {
  const insufficient = {
    verdict: "INSUFFICIENT_DATA" as const,
    observed: null,
    forecast: null,
    unit: null,
    frequency: null,
    confidence: null,
    source: null,
    data_as_of: null,
    label: null,
    limitations: [],
    metrics: {},
  };
  return {
    commodity: "Rice",
    province: province as OutlookResponse["province"],
    resolution_note: "province-resolution",
    demand: {
      ...insufficient,
      verdict: "USABLE_PROXY",
      forecast: [{ period: "2026-01-01", value: 100 + province.length }],
      unit: "index (base~100)",
    },
    supply: supplyOk
      ? { ...insufficient, verdict: "CAUTION", forecast: [{ period: "2026-07-01", value: 500 }], unit: "MT" }
      : insufficient,
    price: insufficient,
    opportunity: {
      verdict: "INSUFFICIENT_DATA",
      score: null,
      classification: null,
      shared_quarter: null,
      breakdown: {},
      weights_used: {},
    },
  };
}

afterEach(() => {
  cleanup();
  localStorage.clear();
  vi.resetAllMocks();
});

describe("MappingAnalytics", () => {
  it("lists a province-resolution value per province and marks unavailable layers", async () => {
    vi.mocked(listMarkets).mockResolvedValue({
      markets: [
        {
          market_id: "LAG-001",
          market_name: "Biñan Public Market",
          municipality: "Biñan",
          province: "Laguna",
          latitude: 14.33,
          longitude: 121.08,
          market_type: "Public Market",
          coordinate_confidence: "HIGH",
          source_url: null,
          notes: null,
        },
      ],
      diagnostics: [],
    });
    vi.mocked(getOutlook).mockImplementation((_c, p) =>
      Promise.resolve(outlook(p, p === "Laguna") as never),
    );

    render(
      <AppPreferencesProvider>
        <MappingAnalytics />
      </AppPreferencesProvider>,
    );

    // demand layer: every province has a value
    await waitFor(() => expect(screen.getByText("Batangas")).toBeInTheDocument());
    expect(await screen.findByText("1 mapped market")).toBeInTheDocument();
    expect(screen.queryByText("not available")).toBeNull();

    // switch to supply: only Laguna is available
    fireEvent.click(screen.getByRole("button", { name: "Supply" }));
    await waitFor(() =>
      expect(screen.getAllByText("not available").length).toBe(4),
    );

    expect(screen.getByText(/never a municipality forecast/i)).toBeInTheDocument();
  });
});
