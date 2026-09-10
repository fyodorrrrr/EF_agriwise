import { afterEach, describe, expect, it, vi } from "vitest";

import { askAgriWise } from "@/lib/rag";

afterEach(() => vi.restoreAllMocks());

describe("askAgriWise", () => {
  it("posts only question and history to /rag/query", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValue(new Response(JSON.stringify({ answer: "hi", citations: [] }), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);

    const result = await askAgriWise("how to compost", [{ role: "user", content: "hello" }]);

    expect(result.answer).toBe("hi");
    const [url, init] = fetchMock.mock.calls[0];
    expect(String(url)).toMatch(/\/rag\/query$/);
    expect(init.method).toBe("POST");
    expect(JSON.parse(init.body)).toEqual({
      question: "how to compost",
      history: [{ role: "user", content: "hello" }],
    });
  });

  it("propagates ApiError on failure", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response("no", { status: 503 })));
    await expect(askAgriWise("q", [])).rejects.toMatchObject({ status: 503 });
  });
});
