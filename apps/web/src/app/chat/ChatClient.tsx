"use client";

import { useState } from "react";

import { CommoditySelect } from "@/components/filters/CommoditySelect";
import { ProvinceSelect } from "@/components/filters/ProvinceSelect";
import { usePreferences } from "@/lib/preferences";
import { askAgriWise } from "@/lib/rag";
import type { Citation } from "@/types/rag";

type Turn = {
  role: "user" | "assistant";
  content: string;
  citations?: Citation[];
  contextUsed?: boolean;
};

const EXAMPLES = [
  "How do I record farm expenses in a Farm Business School?",
  "What are the key requirements of the Code of GAP for vegetables?",
];

function pageLabel(c: Citation): string {
  return c.page_start === c.page_end
    ? `${c.doc_title} — p.${c.page_start}`
    : `${c.doc_title} — p.${c.page_start}-${c.page_end}`;
}

export default function ChatClient() {
  const { preferences, isHydrated, setCommodity, setProvince } = usePreferences();
  const [messages, setMessages] = useState<Turn[]>([]);
  const [input, setInput] = useState("");
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function send(question: string, history: Turn[]) {
    setPending(true);
    setError(null);
    try {
      const res = await askAgriWise(
        question,
        history.map((m) => ({ role: m.role, content: m.content })),
        { commodity: preferences.commodity, province: preferences.province },
      );
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: res.answer,
          citations: res.citations,
          contextUsed: res.analytics_context_used,
        },
      ]);
    } catch {
      setError("Something went wrong. Please try again.");
    } finally {
      setPending(false);
    }
  }

  function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    const question = input.trim();
    if (!question || pending) return;
    const history = messages;
    setMessages((prev) => [...prev, { role: "user", content: question }]);
    setInput("");
    void send(question, history);
  }

  function retry() {
    const lastUser = [...messages].reverse().find((m) => m.role === "user");
    if (!lastUser || pending) return;
    const history = messages.slice(0, messages.indexOf(lastUser));
    void send(lastUser.content, history);
  }

  return (
    <div className="mx-auto flex min-h-full max-w-2xl flex-col gap-4 p-4 sm:p-8">
      <h1 className="text-2xl font-semibold">Ask AgriWise</h1>

      {isHydrated && (
        <div className="flex flex-col gap-2">
          <p className="text-xs text-muted">
            Optional — narrow answers to one commodity and province. Chat works fine without it.
          </p>
          <div className="flex flex-col gap-3 sm:flex-row sm:items-end">
            <CommoditySelect value={preferences.commodity} onChange={setCommodity} />
            <ProvinceSelect value={preferences.province} onChange={setProvince} />
            {(preferences.commodity || preferences.province) && (
              <button
                type="button"
                className="action"
                onClick={() => {
                  setCommodity(null);
                  setProvince(null);
                }}
              >
                Clear
              </button>
            )}
          </div>
        </div>
      )}

      {isHydrated && preferences.commodity && preferences.province && (
        <p className="text-xs text-muted">
          Answers can reference your current analytics selection:{" "}
          <span className="font-medium">
            {preferences.commodity} · {preferences.province}
          </span>
          .
        </p>
      )}

      {messages.length === 0 && (
        <div className="card flex flex-col gap-2">
          <p className="text-sm text-muted">
            Ask about the DA farm-business and good-agricultural-practice manuals.
          </p>
          <div className="chip-group">
            {EXAMPLES.map((ex) => (
              <button
                key={ex}
                type="button"
                className="chip text-left"
                onClick={() => setInput(ex)}
              >
                {ex}
              </button>
            ))}
          </div>
        </div>
      )}

      <ul className="flex flex-col gap-3">
        {messages.map((m, i) => (
          <li
            key={i}
            className={`flex max-w-[92%] flex-col sm:max-w-[80%] ${
              m.role === "user" ? "items-end self-end text-right" : "items-start self-start"
            }`}
          >
            <div
              className={`whitespace-pre-wrap rounded-lg px-3 py-2 text-sm [overflow-wrap:anywhere] ${
                m.role === "user" ? "bg-accent-500 text-on-accent" : "bg-sunken text-body"
              }`}
            >
              {m.content}
            </div>
            {m.citations && m.citations.length > 0 && (
              <ul className="mt-1 text-xs text-muted [overflow-wrap:anywhere]">
                {m.citations.map((c, j) => (
                  <li key={j}>{pageLabel(c)}</li>
                ))}
              </ul>
            )}
            {m.contextUsed && (
              <p className="mt-1 text-xs text-muted">
                Used your current {preferences.commodity} / {preferences.province} analytics.
              </p>
            )}
          </li>
        ))}
      </ul>

      {pending && <p className="state state-loading">Thinking…</p>}
      {error && (
        <p className="state state-error">
          {error}{" "}
          <button type="button" className="action" onClick={retry}>
            Try again
          </button>
        </p>
      )}

      <form
        data-testid="chat-form"
        aria-label="Ask AgriWise"
        onSubmit={onSubmit}
        className="input-shell mt-auto sticky bottom-2"
      >
        <input
          type="text"
          aria-label="Ask a question"
          value={input}
          disabled={pending}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask a question…"
          className="input-bare"
        />
        <button type="submit" disabled={pending} className="btn btn-accent btn-sm">
          Send
        </button>
      </form>
    </div>
  );
}
