"use client";

import dynamic from "next/dynamic";

const CalabarzonMap = dynamic(() => import("./CalabarzonMap"), {
  ssr: false,
  loading: () => (
    <div className="flex h-[70vh] w-full items-center justify-center rounded-lg border border-slate-200 text-slate-500">
      Loading map…
    </div>
  ),
});

export function MapPageClient() {
  return <CalabarzonMap />;
}
