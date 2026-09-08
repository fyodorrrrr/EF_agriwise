import type { Metadata } from "next";
import { ComingSoon } from "@/components/ComingSoon";

export const metadata: Metadata = { title: "Forecasting — AgriWise" };

export default function ForecastingPage() {
  return (
    <ComingSoon
      title="Forecasting"
      description="Demand, supply, price, and opportunity forecasting is under active development."
    />
  );
}
