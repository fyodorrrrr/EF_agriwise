import type { Metadata } from "next";
import { Suspense } from "react";

import { ForecastingClient } from "./ForecastingClient";

export const metadata: Metadata = { title: "Forecasting — AgriWise" };

export default function ForecastingPage() {
  return (
    <Suspense fallback={null}>
      <ForecastingClient />
    </Suspense>
  );
}
