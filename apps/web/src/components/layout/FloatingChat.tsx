"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { usePathname } from "next/navigation";

import ChatClient from "@/app/chat/ChatClient";

export function FloatingChat() {
  const pathname = usePathname();
  const [open, setOpen] = useState(false);
  const [seenPath, setSeenPath] = useState(pathname);
  const panelRef = useRef<HTMLDivElement>(null);
  const bubbleRef = useRef<HTMLButtonElement>(null);

  const close = useCallback(() => setOpen(false), []);

  // Close the panel on any route change (including browser back/forward),
  // but keep ChatClient mounted so the conversation survives the close.
  if (pathname !== seenPath) {
    setSeenPath(pathname);
    setOpen(false);
  }

  useEffect(() => {
    if (!open) return;
    panelRef.current?.querySelector<HTMLElement>("input")?.focus();

    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") {
        setOpen(false);
        bubbleRef.current?.focus();
      }
    }
    function onPointer(e: PointerEvent) {
      const t = e.target as Node;
      if (!panelRef.current?.contains(t) && !bubbleRef.current?.contains(t)) {
        setOpen(false);
      }
    }
    document.addEventListener("keydown", onKey);
    document.addEventListener("pointerdown", onPointer);
    return () => {
      document.removeEventListener("keydown", onKey);
      document.removeEventListener("pointerdown", onPointer);
    };
  }, [open]);

  return (
    <>
      {open && <div className="fab-panel-scrim" aria-hidden="true" onPointerDown={close} />}

      <div
        ref={panelRef}
        className="fab-panel"
        hidden={!open}
        role="dialog"
        aria-label="Ask AgriWise"
        data-testid="chat-panel"
      >
        <div className="fab-panel-head">
          <div className="fab-panel-id">
            <span className="fab-panel-avatar" aria-hidden="true">
              {/* eslint-disable-next-line @next/next/no-img-element -- tiny static brand mark */}
              <img src="/brand/agriwise-mark-white.png" alt="" />
            </span>
            <span className="fab-panel-titles">
              <span className="fab-panel-title">AgriWise</span>
              <span className="fab-panel-subtitle">DA farm-business &amp; GAP manuals</span>
            </span>
          </div>
          <button type="button" className="btn btn-ghost btn-icon" aria-label="Close chat" onClick={close}>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" aria-hidden="true">
              <path d="M18 6 6 18M6 6l12 12" />
            </svg>
          </button>
        </div>
        <div className="fab-panel-body">
          <ChatClient variant="panel" />
        </div>
      </div>

      <button
        type="button"
        ref={bubbleRef}
        className="fab"
        aria-haspopup="dialog"
        aria-expanded={open}
        aria-label="Ask AgriWise"
        onClick={() => setOpen((v) => !v)}
      >
        {open ? (
          <svg className="fab-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2.5} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            <path d="m6 9 6 6 6-6" />
          </svg>
        ) : (
          <>
            <svg className="fab-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
              <path d="M21 11.5a8.5 8.5 0 0 1-12.8 7.3L3 20.5l1.7-5.2A8.5 8.5 0 1 1 21 11.5Z" />
              <circle cx="8.5" cy="12" r="1" fill="currentColor" stroke="none" />
              <circle cx="12" cy="12" r="1" fill="currentColor" stroke="none" />
              <circle cx="15.5" cy="12" r="1" fill="currentColor" stroke="none" />
            </svg>
            <span className="fab-label">Ask AgriWise</span>
          </>
        )}
      </button>
    </>
  );
}
