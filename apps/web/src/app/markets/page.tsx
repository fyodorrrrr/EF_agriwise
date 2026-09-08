import type { Metadata } from "next";
import { Suspense } from "react";

import { MarketsClient } from "./MarketsClient";

export const metadata: Metadata = { title: "Markets — AgriWise" };

export default function MarketsPage() {
  return (
    <Suspense fallback={null}>
      <MarketsClient />
    </Suspense>
  );
}
