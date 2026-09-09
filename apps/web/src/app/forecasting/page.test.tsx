import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";

import { ForecastingClient } from "@/app/forecasting/ForecastingClient";
import { AppPreferencesProvider, PREFERENCES_STORAGE_KEY } from "@/lib/preferences";
import type { OutlookResponse } from "@/types/forecast";

vi.mock("@/lib/forecast", () => ({ getOutlook: vi.fn(), getMethodology: vi.fn() }));
import { getMethodology, getOutlook } from "@/lib/forecast";

const METHODOLOGY = {
  schema_version: "3.2",
  demand: { temporal_proxy: "FIES baseline + LFS activity" },
  supply: { target: "PSA volume of production", frequency: "quarterly" },
  price: { target: "PSA farmgate price", frequency: "monthly" },
  opportunity: {},
  commodity_flow: {},
  disclaimers: ["Opportunity is a peer-relative decision-support score, not causal."],
};

const params = new URLSearchParams();
vi.mock("next/navigation", () => ({ useSearchParams: () => params }));

const OUTLOOK: OutlookResponse = {
  commodity: "Rice",
  province: "Laguna",
  resolution_note: "Analytics are province-resolution; this is not a municipality forecast.",
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
    limitations: ["FIES expenditure-category proxy, not physical commodity demand."],
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
    score: 55.4,
    classification: "BALANCED",
    shared_quarter: "2026-07-01",
    breakdown: {
      demand_pressure_index: { raw: 101, score: 75, weight: 0.389 },
      forecast_confidence_index: { raw: 73.3, score: 73.3, weight: 0.111 },
    },
    weights_used: { demand_pressure_index: 0.389 },
  },
};

afterEach(() => {
  cleanup();
  localStorage.clear();
  vi.resetAllMocks();
});

beforeEach(() => {
  vi.mocked(getMethodology).mockResolvedValue(METHODOLOGY as never);
});

function renderForecasting() {
  return render(
    <AppPreferencesProvider>
      <ForecastingClient />
    </AppPreferencesProvider>,
  );
}

describe("ForecastingClient", () => {
  it("asks for a selection when preferences are empty", () => {
    renderForecasting();
    expect(screen.getByText(/pick a commodity and province/i)).toBeInTheDocument();
  });

  it("renders demand/supply/price cards and the opportunity breakdown", async () => {
    localStorage.setItem(
      PREFERENCES_STORAGE_KEY,
      JSON.stringify({ commodity: "Rice", province: "Laguna" }),
    );
    vi.mocked(getOutlook).mockResolvedValue(OUTLOOK as never);

    const { container } = renderForecasting();

    await waitFor(() =>
      expect(screen.getByText("Estimated Demand Proxy")).toBeInTheDocument(),
    );
    expect(screen.getByText("learned_model:hist_gradient_boosting")).toBeInTheDocument();
    expect(screen.getByText(/not a municipality forecast/i)).toBeInTheDocument();
    // opportunity
    expect(screen.getByText("55 out of 100")).toBeInTheDocument();
    expect(screen.getByText("Forecast reliability")).toBeInTheDocument();
    // explainability — one "Why this result?" per component + opportunity
    expect(screen.getAllByText("Why this result?").length).toBe(4);
    expect(await screen.findByText("Methodology")).toBeInTheDocument();
    expect(screen.queryByText("What do these numbers mean?")).not.toBeInTheDocument();
    expect(container.querySelector(".info-tip")).toBeNull();
  });

  it("lets the user pick a forecast horizon of 2, 3, or 4 quarters", async () => {
    localStorage.setItem(
      PREFERENCES_STORAGE_KEY,
      JSON.stringify({ commodity: "Rice", province: "Laguna" }),
    );
    vi.mocked(getOutlook).mockResolvedValue({
      ...OUTLOOK,
      demand: {
        ...OUTLOOK.demand,
        forecast: [
          { period: "2026-01-01", value: 104 },
          { period: "2026-04-01", value: 106 },
          { period: "2026-07-01", value: 108 },
          { period: "2026-10-01", value: 110 },
        ],
      },
    } as never);

    renderForecasting();

    const fourQ = await screen.findByRole("button", { name: "Next 4 quarters" });
    const twoQ = screen.getByRole("button", { name: "Next 2 quarters" });
    expect(fourQ).toHaveAttribute("aria-pressed", "true");
    expect(twoQ).toHaveAttribute("aria-pressed", "false");
    expect(twoQ).not.toBeDisabled();

    fireEvent.click(twoQ);

    expect(twoQ).toHaveAttribute("aria-pressed", "true");
    expect(fourQ).toHaveAttribute("aria-pressed", "false");
  });

  it("disables horizon options beyond what the shortest available series supports", async () => {
    localStorage.setItem(
      PREFERENCES_STORAGE_KEY,
      JSON.stringify({ commodity: "Rice", province: "Laguna" }),
    );
    // OUTLOOK's demand/supply/price forecasts each carry a single quarter.
    vi.mocked(getOutlook).mockResolvedValue(OUTLOOK as never);

    renderForecasting();

    const threeQ = await screen.findByRole("button", { name: "Next 3 quarters" });
    expect(threeQ).toBeDisabled();
  });

  it("shows the insufficient-data opportunity message honestly", async () => {
    localStorage.setItem(
      PREFERENCES_STORAGE_KEY,
      JSON.stringify({ commodity: "Red Onion", province: "Batangas" }),
    );
    vi.mocked(getOutlook).mockResolvedValue({
      ...OUTLOOK,
      opportunity: {
        verdict: "INSUFFICIENT_DATA",
        score: null,
        classification: null,
        shared_quarter: null,
        breakdown: {},
        weights_used: {},
      },
    } as never);

    renderForecasting();

    expect(
      await screen.findByText(/needs demand, supply, and price for every/i),
    ).toBeInTheDocument();
  });
});
