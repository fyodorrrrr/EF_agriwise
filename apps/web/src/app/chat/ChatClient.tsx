"use client";

import { useEffect, useRef, useState } from "react";

import { CommoditySelect } from "@/components/filters/CommoditySelect";
import { ProvinceSelect } from "@/components/filters/ProvinceSelect";
import { usePreferences } from "@/lib/preferences";
import { askAgriWise } from "@/lib/rag";
import type { Citation, ContactInfo } from "@/types/rag";

type Turn = {
  role: "user" | "assistant";
  content: string;
  citations?: Citation[];
  contextUsed?: boolean;
  analyticsScope?: string | null;
  contact?: ContactInfo | null;
};

function ContactCard({ c }: { c: ContactInfo }) {
  const tel = c.phone.split(/[;,/]/)[0].replace(/[^\d+]/g, "");
  return (
    <div className="card mt-2 gap-1 !p-3 text-sm">
      <p className="text-xs font-semibold text-muted">Need a person to talk to?</p>
      <p className="font-medium">
        {c.name ? `${c.name} — ` : ""}
        {c.position}
      </p>
      <p className="text-xs text-muted">
        {c.office}, {c.organization} · {c.scope}
      </p>
      <p className="mt-1 flex flex-wrap gap-x-3 gap-y-0.5">
        {c.phone && (
          <a href={`tel:${tel}`} className="font-medium">
            ☎ {c.phone}
          </a>
        )}
        {c.email && (
          <a href={`mailto:${c.email}`} className="font-medium">
            ✉ {c.email}
          </a>
        )}
      </p>
      {c.how_to_reach && <p className="text-xs text-muted">{c.how_to_reach}</p>}
      {c.verified && <p className="text-xs text-neutral-500">{c.verified}</p>}
    </div>
  );
}

const EXAMPLES = [
  "How do I record farm expenses in a Farm Business School?",
  "What are the key requirements of the Code of GAP for vegetables?",
];

function pageLabel(c: Citation): string {
  return c.page_start === c.page_end
    ? `${c.doc_title} — p.${c.page_start}`
    : `${c.doc_title} — p.${c.page_start}-${c.page_end}`;
}

const BotAvatar = () => (
  <span className="chat-avatar" aria-hidden="true">
    {/* eslint-disable-next-line @next/next/no-img-element -- tiny static brand mark */}
    <img src="/brand/agriwise-mark-white.png" alt="" />
  </span>
);

export default function ChatClient({ variant = "page" }: { variant?: "page" | "panel" }) {
  const isPanel = variant === "panel";
  const { preferences, isHydrated, setCommodity, setProvince } = usePreferences();
  const [messages, setMessages] = useState<Turn[]>([]);
  const [input, setInput] = useState("");
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!isPanel) return;
    try {
      bottomRef.current?.scrollIntoView?.({ block: "end" });
    } catch {
      /* scrollIntoView is unavailable in some test/SSR environments */
    }
  }, [messages, pending, isPanel]);

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
          analyticsScope: res.analytics_scope,
          contact: res.contact,
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

  const scopeControls = (
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
  );

  const examplePrompts = isPanel ? (
    <div className="chat-suggests">
      {EXAMPLES.map((ex) => (
        <button key={ex} type="button" className="chat-suggest" onClick={() => setInput(ex)}>
          {ex}
        </button>
      ))}
    </div>
  ) : (
    <div className="chip-group">
      {EXAMPLES.map((ex) => (
        <button key={ex} type="button" className="chip text-left" onClick={() => setInput(ex)}>
          {ex}
        </button>
      ))}
    </div>
  );

  return (
    <div
      className={
        isPanel
          ? "flex h-full flex-col gap-3 p-3"
          : "mx-auto flex min-h-full max-w-2xl flex-col gap-4 p-4 sm:p-8"
      }
    >
      {!isPanel && <h1 className="text-2xl font-semibold">Ask AgriWise</h1>}

      <div
        className={
          isPanel
            ? "flex min-h-0 min-w-0 flex-1 flex-col gap-4 overflow-y-auto overflow-x-clip"
            : "flex flex-col gap-4"
        }
      >
        {isHydrated &&
          (isPanel ? (
            <details className="disclosure">
              <summary>Scope answers to a commodity / province</summary>
              <div className="disclosure-body">{scopeControls}</div>
            </details>
          ) : (
            <div className="flex flex-col gap-2">
              <p className="text-xs text-muted">
                Optional — narrow answers to one commodity and province. Chat works fine without it.
              </p>
              {scopeControls}
            </div>
          ))}

        {isHydrated && preferences.commodity && preferences.province && (
          <p className="text-xs text-muted">
            Answers can reference your current analytics selection:{" "}
            <span className="font-medium">
              {preferences.commodity} · {preferences.province}
            </span>
            .
          </p>
        )}

        {messages.length === 0 &&
          (isPanel ? (
            <div className="flex items-start gap-2 self-start">
              <BotAvatar />
              <div className="flex min-w-0 flex-col gap-2">
                <div className="rounded-lg bg-sunken px-3 py-2 text-sm text-body">
                  Kumusta! I&apos;m AgriWise, your farm advisor. Tell me your crop and
                  what&apos;s happening on your farm — or ask about prices, markets, or
                  the DA manuals.
                </div>
                {examplePrompts}
              </div>
            </div>
          ) : (
            <div className="card flex flex-col gap-2">
              <p className="text-sm text-muted">
                Ask about the DA farm-business and good-agricultural-practice manuals.
              </p>
              {examplePrompts}
            </div>
          ))}

        <ul className="flex min-w-0 flex-col gap-3">
          {messages.map((m, i) => {
            const isUser = m.role === "user";
            const meta = (
              <>
                {m.citations && m.citations.length > 0 && (
                  <ul className="mt-1 text-xs text-muted [overflow-wrap:anywhere]">
                    {m.citations.map((c, j) => (
                      <li key={j}>{pageLabel(c)}</li>
                    ))}
                  </ul>
                )}
                {m.contextUsed && (
                  <p className="mt-1 text-xs text-muted">
                    {m.analyticsScope
                      ? `Answer used AgriWise analytics — ${m.analyticsScope}.`
                      : "Answer used AgriWise analytics."}
                  </p>
                )}
                {m.contact && <ContactCard c={m.contact} />}
              </>
            );
            const bubble = (
              <div
                className={`whitespace-pre-wrap rounded-lg px-3 py-2 text-sm [overflow-wrap:anywhere] ${
                  isUser ? "bg-accent-500 text-on-accent" : "bg-sunken text-body"
                }`}
              >
                {m.content}
              </div>
            );

            if (isPanel && !isUser) {
              return (
                <li key={i} className="flex max-w-[92%] items-start gap-2 self-start">
                  <BotAvatar />
                  <div className="flex min-w-0 flex-col items-start">
                    {bubble}
                    {meta}
                  </div>
                </li>
              );
            }

            return (
              <li
                key={i}
                className={`flex max-w-[92%] flex-col sm:max-w-[80%] ${
                  isUser ? "items-end self-end text-right" : "items-start self-start"
                }`}
              >
                {bubble}
                {meta}
              </li>
            );
          })}
        </ul>

        {pending &&
          (isPanel ? (
            <div className="flex items-start gap-2 self-start" aria-label="Thinking" role="status">
              <BotAvatar />
              <div className="typing-dots rounded-lg bg-sunken px-3 py-3">
                <span />
                <span />
                <span />
              </div>
            </div>
          ) : (
            <p className="state state-loading">Thinking…</p>
          ))}
        {error && (
          <p className="state state-error">
            {error}{" "}
            <button type="button" className="action" onClick={retry}>
              Try again
            </button>
          </p>
        )}
        <div ref={bottomRef} />
      </div>

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
        <button
          type="submit"
          disabled={pending || (isPanel && !input.trim())}
          aria-label="Send"
          className={isPanel ? "btn btn-accent btn-icon" : "btn btn-accent btn-sm"}
        >
          {isPanel ? (
            <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth={2.5} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
              <path d="M12 19V5M5 12l7-7 7 7" />
            </svg>
          ) : (
            "Send"
          )}
        </button>
      </form>
    </div>
  );
}
