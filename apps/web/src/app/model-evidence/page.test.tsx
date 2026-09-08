import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen, waitFor } from "@testing-library/react";

import ModelEvidencePage from "@/app/model-evidence/page";
import type { EvidenceComponent, EvidenceResponse } from "@/types/forecast";

vi.mock("@/lib/forecast", () => ({ getEvidence: vi.fn() }));
import { getEvidence } from "@/lib/forecast";

function component(
  commodity: EvidenceComponent["commodity"],
  comp: EvidenceComponent["component"],
  over: Partial<EvidenceComponent> = {},
): EvidenceComponent {
  return {
    commodity,
    component: comp,
    target: "BREAD",
    model: "GradientBoostingRegressor",
    verdict: "USABLE_PROXY",
    reason: "meets the bar",
    frequency: "quarterly",
    province_resolution: "province",
    source: "fies_cross_sectional_estimator",
    schema_version: "3.2",
    metrics: { R2: 0.54 },
    baseline: {},
    province_holdout: [],
    limitations: [],
    ...over,
  };
}

const RESPONSE: EvidenceResponse = {
  components: [
    component("Rice", "demand"),
    component("Rice", "supply", { model: "hist_gradient_boosting", verdict: "CAUTION" }),
    component("Rice", "price", { model: "hist_gradient_boosting", verdict: "PASS" }),
    component("Tomato", "demand", { model: "XGBRegressor", verdict: "INDICATIVE_PROXY" }),
    component("Tomato", "supply", { verdict: "CAUTION" }),
    component("Tomato", "price", { verdict: "CAUTION" }),
    component("Red Onion", "demand", { model: "XGBRegressor", verdict: "INDICATIVE_PROXY" }),
    component("Red Onion", "supply", {
      model: null,
      verdict: "INSUFFICIENT_DATA",
      metrics: {},
      reason: "forecast errors remain too high",
    }),
    component("Red Onion", "price", { model: null, verdict: "INSUFFICIENT_DATA", metrics: {} }),
    component("Banana", "demand", { verdict: "INDICATIVE_PROXY" }),
    component("Banana", "supply", { verdict: "CAUTION" }),
    component("Banana", "price", { verdict: "PASS" }),
  ],
};

afterEach(() => {
  cleanup();
  vi.resetAllMocks();
});

describe("ModelEvidencePage", () => {
  it("renders every commodity and marks missing models unavailable", async () => {
    vi.mocked(getEvidence).mockResolvedValue(RESPONSE as never);

    render(<ModelEvidencePage />);

    await waitFor(() => expect(screen.getByText("Rice")).toBeInTheDocument());
    for (const c of ["Rice", "Tomato", "Red Onion", "Banana"]) {
      expect(screen.getByText(c)).toBeInTheDocument();
    }
    // Red Onion supply/price have no model
    expect(screen.getAllByText(/no deployable model/i).length).toBe(2);
    // shared vegetable proxy note
    expect(screen.getByText(/same shared vegetable-expenditure proxy/i)).toBeInTheDocument();
  });

  it("shows an error state when evidence can't be fetched", async () => {
    vi.mocked(getEvidence).mockRejectedValue(new Error("down"));
    render(<ModelEvidencePage />);
    expect(
      await screen.findByText(/couldn.t reach the forecast service/i),
    ).toBeInTheDocument();
  });
});
