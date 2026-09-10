import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";

import { MarketsClient } from "@/app/markets/MarketsClient";
import type { MarketRankingResponse } from "@/types/markets";

vi.mock("@/lib/markets", () => ({ rankMarkets: vi.fn() }));
import { rankMarkets } from "@/lib/markets";

const RANKING: MarketRankingResponse = {
  commodity: "Rice",
  province: "Laguna",
  supported_analytics: 3,
  ranked: [
    {
      market: {
        market_id: "LAG-001",
        market_name: "Biñan Public Market",
        municipality: "Biñan",
        province: "Laguna",
        latitude: 14.35,
        longitude: 121.08,
        market_type: "Public Market",
        operator: null,
        coordinate_confidence: "HIGH",
        source_url: null,
        notes: null,
      },
      score: 71.2,
      distance_km: 12.4,
      breakdown: {
        proximity: { score: 0.8, weight: 0.4 },
        data_reliability: { score: 1.0, weight: 0.2 },
      },
      why: "~12 km from the province centre (straight line, not travel time); high-confidence location",
    },
  ],
  policy: ["Straight-line distance is not travel time."],
};

afterEach(() => {
  cleanup();
  localStorage.clear();
  vi.resetAllMocks();
});

function renderMarkets() {
  return render(<MarketsClient />);
}

function pick(commodity: string, province: string) {
  fireEvent.change(screen.getByLabelText("Commodity"), { target: { value: commodity } });
  fireEvent.change(screen.getByLabelText("Province"), { target: { value: province } });
}

describe("MarketsClient", () => {
  it("prompts for a selection first", () => {
    renderMarkets();
    expect(screen.getByText(/pick a commodity and province/i)).toBeInTheDocument();
  });

  it("renders ranked markets with the why-recommended breakdown and policy caveats", async () => {
    vi.mocked(rankMarkets).mockResolvedValue(RANKING as never);

    renderMarkets();
    pick("Rice", "Laguna");

    await waitFor(() =>
      expect(screen.getByText("Biñan Public Market")).toBeInTheDocument(),
    );
    expect(screen.getByText("71.2 out of 100")).toBeInTheDocument();
    expect(screen.getByText(/3\/3 analytics components available/i)).toBeInTheDocument();
    expect(screen.getByText("Why recommended?")).toBeInTheDocument();
    // caveat appears in the intro copy and again as a policy bullet
    expect(
      screen.getAllByText(/straight-line distance is not travel time/i).length,
    ).toBeGreaterThanOrEqual(1);
    expect(screen.getByRole("link", { name: /view on map/i })).toHaveAttribute(
      "href",
      "/mapping?market=LAG-001",
    );
  });

  it("shows an empty state when a province has no mapped markets", async () => {
    vi.mocked(rankMarkets).mockResolvedValue({
      ...RANKING,
      province: "Rizal",
      ranked: [],
    } as never);

    renderMarkets();
    pick("Rice", "Rizal");

    expect(await screen.findByText(/no curated market with verified coordinates/i)).toBeInTheDocument();
  });
});
