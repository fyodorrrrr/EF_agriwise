import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen, waitFor } from "@testing-library/react";

import Home from "@/app/page";
import { AppPreferencesProvider, PREFERENCES_STORAGE_KEY } from "@/lib/preferences";
import type { OutlookResponse } from "@/types/forecast";

vi.mock("@/lib/forecast", () => ({ getOutlook: vi.fn() }));
import { getOutlook } from "@/lib/forecast";

function outlook(commodity: string): OutlookResponse {
  return {
    commodity: commodity as OutlookResponse["commodity"],
    province: "Laguna",
    resolution_note: "Analytics are province-resolution.",
    demand: {
      verdict: "USABLE_PROXY",
      observed: [{ period: "2025-10-01", value: 101 }],
      forecast: [{ period: "2026-01-01", value: 104 }],
      unit: "index (base~100)",
      frequency: "quarterly",
      confidence: "MODERATE",
      source: "demand_pressure_index",
      data_as_of: "2025-10-01",
      label: "Cereal Household Demand Proxy",
      limitations: [],
      metrics: {},
    },
    supply: {
      verdict: "CAUTION",
      observed: [{ period: "2026-04-01", value: 43598 }],
      forecast: [{ period: "2026-07-01", value: 4653 }],
      unit: "MT",
      frequency: "quarterly",
      confidence: "MODERATE",
      source: "seasonal_naive",
      data_as_of: "2026-04-01",
      label: null,
      limitations: [],
      metrics: {},
    },
    price: {
      verdict: "INSUFFICIENT_DATA",
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
    },
    opportunity: {
      verdict: "PASS",
      score: 55.4,
      classification: "BALANCED",
      shared_quarter: "2026-07-01",
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

function renderDashboard() {
  return render(
    <AppPreferencesProvider>
      <Home />
    </AppPreferencesProvider>,
  );
}

describe("Dashboard", () => {
  it("prompts for a province when none is selected", () => {
    renderDashboard();
    expect(screen.getByText(/choose a province/i)).toBeInTheDocument();
  });

  it("renders an outlook card per commodity for the saved province", async () => {
    localStorage.setItem(
      PREFERENCES_STORAGE_KEY,
      JSON.stringify({ commodity: "Rice", province: "Laguna" }),
    );
    vi.mocked(getOutlook).mockImplementation((c) => Promise.resolve(outlook(c) as never));

    renderDashboard();

    await waitFor(() => expect(screen.getByText("Rice")).toBeInTheDocument());
    expect(screen.getByText("Tomato")).toBeInTheDocument();
    expect(screen.getAllByText("Banana").length).toBeGreaterThan(0);
    // opportunity classification surfaces on the card
    expect(screen.getAllByText(/balanced · 55.4/i).length).toBe(4);
  });

  it("shows an error state and no stale rows when the service fails", async () => {
    localStorage.setItem(
      PREFERENCES_STORAGE_KEY,
      JSON.stringify({ commodity: "Rice", province: "Laguna" }),
    );
    vi.mocked(getOutlook).mockRejectedValue(new Error("boom"));

    renderDashboard();

    expect(await screen.findByText(/couldn.t reach the forecast service/i)).toBeInTheDocument();
    expect(screen.queryByText("Tomato")).toBeNull();
  });
});
