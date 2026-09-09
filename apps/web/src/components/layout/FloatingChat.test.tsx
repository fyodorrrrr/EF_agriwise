import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";

import { FloatingChat } from "./FloatingChat";
import { AppPreferencesProvider } from "@/lib/preferences";

vi.mock("next/navigation", () => ({ usePathname: () => "/" }));

vi.mock("@/lib/rag", () => ({ askAgriWise: vi.fn() }));
import { askAgriWise } from "@/lib/rag";

const renderFab = () =>
  render(
    <AppPreferencesProvider>
      <FloatingChat />
    </AppPreferencesProvider>,
  );

afterEach(() => {
  cleanup();
  localStorage.clear();
  vi.resetAllMocks();
});

function ask(text: string) {
  fireEvent.change(screen.getByRole("textbox"), { target: { value: text } });
  fireEvent.submit(screen.getByTestId("chat-form"));
}

describe("FloatingChat", () => {
  it("renders the bubble collapsed by default", () => {
    renderFab();
    expect(screen.getByRole("button", { name: "Ask AgriWise" })).toHaveAttribute(
      "aria-expanded",
      "false",
    );
    expect(screen.getByTestId("chat-panel")).toHaveAttribute("hidden");
  });

  it("opens the panel and focuses the input when the bubble is clicked", async () => {
    renderFab();
    fireEvent.click(screen.getByRole("button", { name: "Ask AgriWise" }));

    expect(screen.getByTestId("chat-panel")).not.toHaveAttribute("hidden");
    await waitFor(() => expect(screen.getByRole("textbox")).toHaveFocus());
  });

  it("closes on Escape and returns focus to the bubble", async () => {
    renderFab();
    const bubble = screen.getByRole("button", { name: "Ask AgriWise" });
    fireEvent.click(bubble);
    await waitFor(() => expect(screen.getByRole("textbox")).toHaveFocus());

    fireEvent.keyDown(document, { key: "Escape" });

    await waitFor(() => expect(screen.getByTestId("chat-panel")).toHaveAttribute("hidden"));
    expect(bubble).toHaveFocus();
  });

  it("answers a question inside the panel and keeps it after closing and reopening", async () => {
    vi.mocked(askAgriWise).mockResolvedValue({
      answer: "Keep a cash book.",
      citations: [],
      analytics_context_used: false,
    });
    renderFab();
    fireEvent.click(screen.getByRole("button", { name: "Ask AgriWise" }));
    ask("how do I track expenses?");

    expect(await screen.findByText("Keep a cash book.")).toBeInTheDocument();

    fireEvent.keyDown(document, { key: "Escape" });
    fireEvent.click(screen.getByRole("button", { name: "Ask AgriWise" }));

    expect(screen.getByText("Keep a cash book.")).toBeInTheDocument();
  });
});
