"use client";

import dynamic from "next/dynamic";
import type { CalabarzonMapProps } from "./CalabarzonMap";

const CalabarzonMap = dynamic<CalabarzonMapProps>(() => import("./CalabarzonMap"), {
  ssr: false,
  loading: () => (
    <div className="flex h-[70vh] w-full items-center justify-center rounded-lg border border-slate-200 text-slate-500">
      Loading map…
    </div>
  ),
});

export function MapPageClient(props: CalabarzonMapProps) {
  return <CalabarzonMap {...props} />;
}
