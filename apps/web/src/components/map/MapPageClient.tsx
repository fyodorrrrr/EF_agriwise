"use client";

import dynamic from "next/dynamic";
import type { CalabarzonMapProps } from "./CalabarzonMap";

const CalabarzonMap = dynamic<CalabarzonMapProps>(() => import("./CalabarzonMap"), {
  ssr: false,
  loading: () => (
    <div className="brand-loader h-[60vh] min-h-[360px] w-full rounded-lg border border-line sm:h-[70vh]">
      <img src="/brand/agriwise-mark.png" alt="" aria-hidden="true" />
      <span>Loading map…</span>
    </div>
  ),
});

export function MapPageClient(props: CalabarzonMapProps) {
  return <CalabarzonMap {...props} />;
}
