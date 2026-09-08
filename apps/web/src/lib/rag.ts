import { apiFetch } from "@/lib/api";
import type { ChatMessage, RagQueryResponse } from "@/types/rag";

export function askAgriWise(
  question: string,
  history: ChatMessage[],
  selection?: { commodity?: string | null; province?: string | null },
): Promise<RagQueryResponse> {
  return apiFetch<RagQueryResponse>("/rag/query", {
    method: "POST",
    body: JSON.stringify({
      question,
      history,
      commodity: selection?.commodity ?? null,
      province: selection?.province ?? null,
    }),
  });
}
