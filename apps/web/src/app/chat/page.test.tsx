import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";

import ChatPage from "@/app/chat/page";

vi.mock("@/lib/rag", () => ({ askAgriWise: vi.fn() }));
import { askAgriWise } from "@/lib/rag";

const renderChat = () => render(<ChatPage />);

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

  it("notes when the answer used the analytics, and sends no filter", async () => {
    vi.mocked(askAgriWise).mockResolvedValue({
      answer: "Rice demand is up.",
      citations: [],
      analytics_context_used: true,
      analytics_scope: "Rice · Laguna",
    });
    renderChat();
    ask("how is rice demand in Laguna?");

    await screen.findByText("Rice demand is up.");
    // The chat has no scope filter now — only question + history are sent.
    expect(vi.mocked(askAgriWise).mock.calls[0]).toHaveLength(2);
    expect(
      screen.getByText(/answer used agriwise analytics — rice · laguna/i),
    ).toBeInTheDocument();
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
