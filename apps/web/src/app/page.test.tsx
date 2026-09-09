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
      verdict: "PASS",
      observed: [{ period: "2026-07-01", value: 18.5 }],
      forecast: [{ period: "2026-08-01", value: 19.3 }],
      unit: "PHP/kg",
      frequency: "monthly",
      confidence: "HIGH",
      source: "learned_model:hist_gradient_boosting",
      data_as_of: "2026-07-01",
      label: null,
      limitations: [],
      metrics: {},
    },
    opportunity: {
      verdict: "PASS",
      score: 28.98,
      classification: "OVERSUPPLY_LEANING",
      shared_quarter: "2026-07-01",
      breakdown: {
        demand_pressure_index: { raw: 104, score: 0, weight: 0.389 },
        supply_gap_or_scarcity_index: { raw: 4653, score: 75, weight: 0.278 },
        price_opportunity_index: { raw: 19.3, score: 0, weight: 0.222 },
        forecast_confidence_index: { raw: 73.3, score: 73.3, weight: 0.111 },
      },
      weights_used: {
        demand_pressure_index: 0.389,
        supply_gap_or_scarcity_index: 0.278,
        price_opportunity_index: 0.222,
        forecast_confidence_index: 0.111,
      },
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

    const { container } = renderDashboard();

    await waitFor(() => expect(screen.getAllByText("Rice").length).toBeGreaterThan(0));
    expect(screen.getAllByText("Tomato").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Banana").length).toBeGreaterThan(0);
    expect(screen.getAllByText(/more supply likely · 29/i)).toHaveLength(4);
    expect(screen.queryByRole("region", { name: /opportunity summary/i })).toBeNull();
    expect(screen.queryByText("Overall result")).toBeNull();
    expect(screen.queryByRole("table", { name: /opportunity breakdown/i })).toBeNull();
    expect(screen.getAllByText("104 demand index")).toHaveLength(4);
    expect(screen.getAllByText("4,653 metric tons")).toHaveLength(4);
    expect(screen.getAllByText("19.3 pesos per kilogram")).toHaveLength(4);
    expect(screen.getAllByText("Estimated demand")).toHaveLength(4);
    expect(screen.getAllByText("Available supply")).toHaveLength(4);
    expect(screen.getAllByText("Farmgate price")).toHaveLength(4);
    expect(screen.queryByText("Estimated Demand Proxy")).toBeNull();
    expect(screen.getAllByText("Data period: Quarter 3, 2026")).toHaveLength(4);
    // KPI tiles are gone — coverage is one plain sentence, and the two
    // "best opportunity" tiles are now a ranked bar strip.
    expect(screen.queryByText("Average opportunity score")).toBeNull();
    expect(screen.getByText(/tracking 4 commodities/i)).toBeVisible();
    expect(screen.getByText("Best opportunity right now")).toBeVisible();
    // A real chart per commodity per metric (demand/supply/price), not the
    // old 160×40 sparkline.
    expect(screen.queryByLabelText("Trend")).toBeNull();
    expect(container.querySelectorAll(".chart-frame").length).toBe(12);
    expect(
      screen.queryByText(/demand, supply, and price signals here are roughly in line/i),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByText(/the opportunity score above is the closest combined signal/i),
    ).not.toBeInTheDocument();
    expect(screen.queryByText("What do these numbers mean?")).not.toBeInTheDocument();
    expect(screen.queryByLabelText("What does this score mean?")).not.toBeInTheDocument();
    expect(screen.queryByLabelText("What is Estimated Demand Proxy?")).not.toBeInTheDocument();
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
