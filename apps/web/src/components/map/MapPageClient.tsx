"use client";

import dynamic from "next/dynamic";
import type { CalabarzonMapProps } from "./CalabarzonMap";

const CalabarzonMap = dynamic<CalabarzonMapProps>(() => import("./CalabarzonMap"), {
  ssr: false,
  loading: () => (
    <div className="state state-loading flex h-[60vh] min-h-[360px] w-full items-center justify-center rounded-lg border border-line sm:h-[70vh]">
      Loading map…
    </div>
  ),
});

export function MapPageClient(props: CalabarzonMapProps) {
  return <CalabarzonMap {...props} />;
}
