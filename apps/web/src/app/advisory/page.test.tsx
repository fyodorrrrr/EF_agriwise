import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";

import { AdvisoryClient } from "@/app/advisory/AdvisoryClient";

vi.mock("@/lib/advisory", () => ({ getAdvisories: vi.fn() }));
import { getAdvisories } from "@/lib/advisory";

afterEach(() => {
  cleanup();
  localStorage.clear();
  vi.resetAllMocks();
});

describe("AdvisoryClient", () => {
  it("uses the full page layout so market advisory content fills the workspace", () => {
    render(<AdvisoryClient />);

    expect(
      screen.getByRole("heading", { name: "Market Advisory" }).closest(".page-container-full"),
    ).toBeInTheDocument();
  });

  it("fills the loading state with placeholders for the market brief and signals", () => {
    vi.mocked(getAdvisories).mockReturnValue(new Promise(() => {}));

    const { container } = render(<AdvisoryClient />);
    fireEvent.change(screen.getByLabelText("Province"), { target: { value: "Laguna" } });

    expect(screen.getByRole("status")).toHaveTextContent("Preparing market brief");
    expect(container.querySelectorAll("[data-advisory-skeleton-card]")).toHaveLength(4);
  });
});
