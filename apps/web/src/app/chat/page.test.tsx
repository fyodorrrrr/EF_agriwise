import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";

import ChatPage from "@/app/chat/page";

vi.mock("@/lib/rag", () => ({ askAgriWise: vi.fn() }));
import { askAgriWise } from "@/lib/rag";

afterEach(() => {
  cleanup();
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
    });
    render(<ChatPage />);
    ask("how do I track expenses?");

    expect(await screen.findByText("Keep a cash book.")).toBeInTheDocument();
    expect(screen.getByText(/Farm Business School Manual — p\.88-89/)).toBeInTheDocument();
    expect(vi.mocked(askAgriWise).mock.calls[0][0]).toBe("how do I track expenses?");
    expect(vi.mocked(askAgriWise).mock.calls[0][1]).toEqual([]);
  });

  it("shows an error with retry when the request fails", async () => {
    vi.mocked(askAgriWise).mockRejectedValueOnce(new Error("boom"));
    render(<ChatPage />);
    ask("hello");

    expect(await screen.findByText(/something went wrong/i)).toBeInTheDocument();

    vi.mocked(askAgriWise).mockResolvedValueOnce({ answer: "recovered", citations: [] });
    fireEvent.click(screen.getByRole("button", { name: /try again/i }));
    expect(await screen.findByText("recovered")).toBeInTheDocument();
  });

  it("disables input while pending", async () => {
    let resolve!: (v: unknown) => void;
    vi.mocked(askAgriWise).mockReturnValue(new Promise((r) => (resolve = r)) as never);
    render(<ChatPage />);
    ask("slow one");

    await waitFor(() => expect(screen.getByRole("textbox")).toBeDisabled());
    resolve({ answer: "done", citations: [] });
    expect(await screen.findByText("done")).toBeInTheDocument();
  });
});
