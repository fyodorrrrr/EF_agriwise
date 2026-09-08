"use client";

import { useState } from "react";

import { askAgriWise } from "@/lib/rag";
import type { Citation } from "@/types/rag";

type Turn = { role: "user" | "assistant"; content: string; citations?: Citation[] };

const EXAMPLES = [
  "How do I record farm expenses in a Farm Business School?",
  "What are the key requirements of the Code of GAP for vegetables?",
];

function pageLabel(c: Citation): string {
  return c.page_start === c.page_end
    ? `${c.doc_title} — p.${c.page_start}`
    : `${c.doc_title} — p.${c.page_start}-${c.page_end}`;
}

export default function ChatPage() {
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
      );
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: res.answer, citations: res.citations },
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
    <main className="mx-auto flex min-h-full max-w-2xl flex-col gap-4 p-4 sm:p-8">
      <h1 className="text-2xl font-semibold">Ask AgriWise</h1>

      {messages.length === 0 && (
        <div className="flex flex-col gap-2 text-slate-600 dark:text-slate-300">
          <p>Ask about the DA farm-business and good-agricultural-practice manuals.</p>
          {EXAMPLES.map((ex) => (
            <button
              key={ex}
              type="button"
              className="rounded border border-slate-300 px-3 py-2 text-left text-sm hover:bg-slate-100 dark:border-slate-700 dark:hover:bg-slate-800"
              onClick={() => setInput(ex)}
            >
              {ex}
            </button>
          ))}
        </div>
      )}

      <ul className="flex flex-col gap-3">
        {messages.map((m, i) => (
          <li key={i} className={m.role === "user" ? "self-end text-right" : "self-start"}>
            <div
              className={`whitespace-pre-wrap rounded-lg px-3 py-2 text-sm ${
                m.role === "user"
                  ? "bg-emerald-600 text-white"
                  : "bg-slate-100 dark:bg-slate-800"
              }`}
            >
              {m.content}
            </div>
            {m.citations && m.citations.length > 0 && (
              <ul className="mt-1 text-xs text-slate-500">
                {m.citations.map((c, j) => (
                  <li key={j}>{pageLabel(c)}</li>
                ))}
              </ul>
            )}
          </li>
        ))}
      </ul>

      {pending && <p className="text-sm text-slate-500">Thinking…</p>}
      {error && (
        <p className="text-sm text-red-600">
          {error}{" "}
          <button type="button" className="underline" onClick={retry}>
            Try again
          </button>
        </p>
      )}

      <form
        data-testid="chat-form"
        aria-label="Ask AgriWise"
        onSubmit={onSubmit}
        className="mt-auto flex gap-2"
      >
        <input
          type="text"
          aria-label="Ask a question"
          value={input}
          disabled={pending}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask a question…"
          className="flex-1 rounded border border-slate-300 px-3 py-2 text-sm disabled:opacity-50 dark:border-slate-700 dark:bg-slate-900"
        />
        <button
          type="submit"
          disabled={pending}
          className="rounded bg-emerald-600 px-4 py-2 text-sm text-white disabled:opacity-50"
        >
          Send
        </button>
      </form>
    </main>
  );
}
