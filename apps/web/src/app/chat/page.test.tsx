import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";

import ChatPage from "@/app/chat/page";
import { AppPreferencesProvider, PREFERENCES_STORAGE_KEY } from "@/lib/preferences";

vi.mock("@/lib/rag", () => ({ askAgriWise: vi.fn() }));
import { askAgriWise } from "@/lib/rag";

const renderChat = () =>
  render(
    <AppPreferencesProvider>
      <ChatPage />
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

describe("ChatPage", () => {
  it("renders the answer and its citations", async () => {
    vi.mocked(askAgriWise).mockResolvedValue({
      answer: "Keep a cash book.",
      citations: [
        { doc_id: "fbs", doc_title: "Farm Business School Manual", page_start: 88, page_end: 89 },
      ],
      analytics_context_used: false,
    });
    renderChat();
    ask("how do I track expenses?");

    expect(await screen.findByText("Keep a cash book.")).toBeInTheDocument();
    expect(screen.getByText(/Farm Business School Manual — p\.88-89/)).toBeInTheDocument();
    expect(vi.mocked(askAgriWise).mock.calls[0][0]).toBe("how do I track expenses?");
    expect(vi.mocked(askAgriWise).mock.calls[0][1]).toEqual([]);
  });

  it("shows an error with retry when the request fails", async () => {
    vi.mocked(askAgriWise).mockRejectedValueOnce(new Error("boom"));
    renderChat();
    ask("hello");

    expect(await screen.findByText(/something went wrong/i)).toBeInTheDocument();

    vi.mocked(askAgriWise).mockResolvedValueOnce({
      answer: "recovered",
      citations: [],
      analytics_context_used: false,
    });
    fireEvent.click(screen.getByRole("button", { name: /try again/i }));
    expect(await screen.findByText("recovered")).toBeInTheDocument();
  });

  it("passes the saved commodity/province selection and notes when it was used", async () => {
    localStorage.setItem(
      PREFERENCES_STORAGE_KEY,
      JSON.stringify({ commodity: "Rice", province: "Laguna" }),
    );
    vi.mocked(askAgriWise).mockResolvedValue({
      answer: "Rice demand is up.",
      citations: [],
      analytics_context_used: true,
    });
    renderChat();
    ask("how is rice demand?");

    await screen.findByText("Rice demand is up.");
    expect(vi.mocked(askAgriWise).mock.calls[0][2]).toEqual({
      commodity: "Rice",
      province: "Laguna",
    });
    expect(screen.getByText(/used your current rice \/ laguna analytics/i)).toBeInTheDocument();
  });

  it("disables input while pending", async () => {
    let resolve!: (v: unknown) => void;
    vi.mocked(askAgriWise).mockReturnValue(new Promise((r) => (resolve = r)) as never);
    renderChat();
    ask("slow one");

    await waitFor(() => expect(screen.getByRole("textbox")).toBeDisabled());
    resolve({ answer: "done", citations: [] });
    expect(await screen.findByText("done")).toBeInTheDocument();
  });
});
