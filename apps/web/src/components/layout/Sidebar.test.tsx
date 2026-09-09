import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";

import { Sidebar, SIDEBAR_STORAGE_KEY } from "./Sidebar";

vi.mock("next/navigation", () => ({ usePathname: () => "/forecasting" }));

afterEach(() => {
  cleanup();
  localStorage.clear();
});

describe("Sidebar", () => {
  it("starts expanded and identifies the current page", () => {
    render(<Sidebar />);

    expect(screen.getByRole("navigation", { name: "Primary" })).toHaveAttribute(
      "data-collapsed",
      "false",
    );
    expect(screen.getByRole("button", { name: "Collapse navigation" })).toHaveAttribute(
      "aria-expanded",
      "true",
    );
    expect(screen.getByRole("link", { name: "Forecasting" })).toHaveAttribute(
      "aria-current",
      "page",
    );
  });

  it("collapses the desktop rail and remembers the preference", () => {
    const { unmount } = render(<Sidebar />);

    fireEvent.click(screen.getByRole("button", { name: "Collapse navigation" }));

    expect(screen.getByRole("navigation", { name: "Primary" })).toHaveAttribute(
      "data-collapsed",
      "true",
    );
    expect(screen.getByRole("button", { name: "Expand navigation" })).toHaveAttribute(
      "aria-expanded",
      "false",
    );
    expect(localStorage.getItem(SIDEBAR_STORAGE_KEY)).toBe("collapsed");

    unmount();
    render(<Sidebar />);

    expect(screen.getByRole("navigation", { name: "Primary" })).toHaveAttribute(
      "data-collapsed",
      "true",
    );
  });
});
