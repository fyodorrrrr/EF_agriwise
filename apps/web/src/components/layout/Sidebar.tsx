"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { MORE_ICON, NAV_ITEMS } from "./nav-items";

function isActive(pathname: string, href: string) {
  if (href === "/") return pathname === "/";
  return pathname === href || pathname.startsWith(`${href}/`);
}

const MORE_ITEMS = NAV_ITEMS.filter((i) => i.group === "more");

export function Sidebar() {
  const pathname = usePathname();
  const [moreOpen, setMoreOpen] = useState(false);
  const [seenPath, setSeenPath] = useState(pathname);
  const moreRef = useRef<HTMLDivElement>(null);
  const moreButtonRef = useRef<HTMLButtonElement>(null);

  const closeMore = useCallback(() => setMoreOpen(false), []);

  // Close the sheet on any route change (including browser back/forward).
  if (pathname !== seenPath) {
    setSeenPath(pathname);
    setMoreOpen(false);
  }

  // While open: dismiss on Escape or an outside tap, and move focus into the sheet.
  useEffect(() => {
    if (!moreOpen) return;
    moreRef.current?.querySelector<HTMLElement>("a")?.focus();

    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") {
        setMoreOpen(false);
        moreButtonRef.current?.focus();
      }
    }
    function onPointer(e: PointerEvent) {
      const t = e.target as Node;
      if (!moreRef.current?.contains(t) && !moreButtonRef.current?.contains(t)) {
        setMoreOpen(false);
      }
    }
    document.addEventListener("keydown", onKey);
    document.addEventListener("pointerdown", onPointer);
    return () => {
      document.removeEventListener("keydown", onKey);
      document.removeEventListener("pointerdown", onPointer);
    };
  }, [moreOpen]);

  const moreActive = MORE_ITEMS.some((i) => isActive(pathname, i.href));

  return (
    <>
      <div className="sidebar">
        <Link href="/" className="sidebar-brand">
          AgriWise
        </Link>

        <nav className="sidenav" aria-label="Primary">
          {NAV_ITEMS.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              data-group={item.group}
              aria-current={isActive(pathname, item.href) ? "page" : undefined}
              className="sidenav-item"
            >
              {item.icon}
              <span className="sidenav-full">{item.label}</span>
              <span className="sidenav-short">{item.short}</span>
            </Link>
          ))}

          {/* Mobile-only: the overflow tab and its sheet. Hidden on the desktop rail. */}
          <div className="sidenav-more" ref={moreRef}>
            {moreOpen && (
              <div className="sidenav-sheet" role="menu" aria-label="More pages">
                {MORE_ITEMS.map((item) => (
                  <Link
                    key={item.href}
                    href={item.href}
                    role="menuitem"
                    aria-current={isActive(pathname, item.href) ? "page" : undefined}
                    className="sidenav-sheet-item"
                    onClick={closeMore}
                  >
                    {item.icon}
                    <span>{item.label}</span>
                  </Link>
                ))}
              </div>
            )}
            <button
              type="button"
              ref={moreButtonRef}
              className="sidenav-item sidenav-more-btn"
              aria-haspopup="menu"
              aria-expanded={moreOpen}
              aria-current={moreActive && !moreOpen ? "page" : undefined}
              onClick={() => setMoreOpen((v) => !v)}
            >
              {MORE_ICON}
              <span className="sidenav-short">More</span>
            </button>
          </div>
        </nav>
      </div>

      {moreOpen && (
        <div className="sidenav-scrim" aria-hidden="true" onPointerDown={closeMore} />
      )}
    </>
  );
}
