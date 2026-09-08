import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";

import SetupPage from "@/app/setup/page";
import { AppPreferencesProvider, PREFERENCES_STORAGE_KEY } from "@/lib/preferences";

vi.mock("@/lib/forecast", () => ({ getCatalog: vi.fn() }));
import { getCatalog } from "@/lib/forecast";

const CATALOG = {
  commodities: ["Rice", "Tomato", "Red Onion", "Banana"],
  provinces: ["Batangas", "Cavite", "Laguna", "Quezon", "Rizal"],
  pairs: [],
};

afterEach(() => {
  cleanup();
  localStorage.clear();
  vi.resetAllMocks();
});

function renderSetup() {
  return render(
    <AppPreferencesProvider>
      <SetupPage />
    </AppPreferencesProvider>,
  );
}

describe("SetupPage", () => {
  it("persists the chosen commodity and province and enables Continue", async () => {
    vi.mocked(getCatalog).mockResolvedValue(CATALOG as never);
    renderSetup();

    const commodity = await screen.findByLabelText("Commodity");
    fireEvent.change(commodity, { target: { value: "Banana" } });
    fireEvent.change(screen.getByLabelText("Province"), { target: { value: "Cavite" } });

    await waitFor(() =>
      expect(JSON.parse(localStorage.getItem(PREFERENCES_STORAGE_KEY)!)).toEqual({
        commodity: "Banana",
        province: "Cavite",
      }),
    );
    expect(screen.getByRole("link", { name: /continue to dashboard/i })).toHaveAttribute(
      "href",
      "/",
    );
  });

  it("does not offer a Continue link until both fields are set", async () => {
    vi.mocked(getCatalog).mockResolvedValue(CATALOG as never);
    renderSetup();

    await screen.findByLabelText("Commodity");
    fireEvent.change(screen.getByLabelText("Commodity"), { target: { value: "Rice" } });

    expect(screen.queryByRole("link", { name: /continue to dashboard/i })).toBeNull();
  });

  it("falls back to static options and shows a notice when the catalog request fails", async () => {
    vi.mocked(getCatalog).mockRejectedValue(new Error("boom"));
    renderSetup();

    expect(await screen.findByText(/couldn.t load the latest options/i)).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Province"), { target: { value: "Laguna" } });
    expect((screen.getByLabelText("Province") as HTMLSelectElement).value).toBe("Laguna");
  });
});
