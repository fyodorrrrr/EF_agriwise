import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";

import { AdvisoryClient } from "@/app/advisory/AdvisoryClient";
import { AppPreferencesProvider, PREFERENCES_STORAGE_KEY } from "@/lib/preferences";

vi.mock("@/lib/advisory", () => ({ getAdvisories: vi.fn() }));
import { getAdvisories } from "@/lib/advisory";

afterEach(() => {
  cleanup();
  localStorage.clear();
  vi.resetAllMocks();
});

describe("AdvisoryClient", () => {
  it("uses the full page layout so market advisory content fills the workspace", () => {
    render(
      <AppPreferencesProvider>
        <AdvisoryClient />
      </AppPreferencesProvider>,
    );

    expect(
      screen.getByRole("heading", { name: "Market Advisory" }).closest(".page-container-full"),
    ).toBeInTheDocument();
  });

  it("fills the loading state with placeholders for the market brief and signals", () => {
    localStorage.setItem(
      PREFERENCES_STORAGE_KEY,
      JSON.stringify({ commodity: "Rice", province: "Laguna" }),
    );
    vi.mocked(getAdvisories).mockReturnValue(new Promise(() => {}));

    const { container } = render(
      <AppPreferencesProvider>
        <AdvisoryClient />
      </AppPreferencesProvider>,
    );

    expect(screen.getByRole("status")).toHaveTextContent("Preparing market brief");
    expect(container.querySelectorAll("[data-advisory-skeleton-card]")).toHaveLength(4);
  });
});
