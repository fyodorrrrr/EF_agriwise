"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";
import { NAV_ITEMS } from "./nav-items";

function isActive(pathname: string, href: string) {
  if (href === "/") return pathname === "/";
  return pathname === href || pathname.startsWith(`${href}/`);
}

export function Sidebar() {
  const pathname = usePathname();
  const [isOpen, setIsOpen] = useState(false);

  return (
    <>
      <div className="flex items-center justify-between border-b border-slate-200 p-4 md:hidden">
        <span className="font-semibold">AgriWise</span>
        <button
          type="button"
          onClick={() => setIsOpen((v) => !v)}
          aria-expanded={isOpen}
          aria-label="Toggle navigation"
          className="rounded border border-slate-300 px-3 py-1 text-sm"
        >
          Menu
        </button>
      </div>
      <aside
        className={`${isOpen ? "block" : "hidden"} border-b border-slate-200 p-4 md:block md:w-60 md:shrink-0 md:border-r md:border-b-0`}
      >
        <div className="mb-6 hidden text-lg font-semibold md:block">AgriWise</div>
        <nav className="flex flex-col gap-1">
          {NAV_ITEMS.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              onClick={() => setIsOpen(false)}
              className={`rounded px-3 py-2 text-sm ${
                isActive(pathname, item.href)
                  ? "bg-slate-100 font-semibold text-slate-900"
                  : "text-slate-600 hover:bg-slate-50"
              }`}
            >
              {item.label}
            </Link>
          ))}
        </nav>
      </aside>
    </>
  );
}
