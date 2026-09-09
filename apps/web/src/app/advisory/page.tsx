import type { Metadata } from "next";

import { AdvisoryClient } from "./AdvisoryClient";

export const metadata: Metadata = { title: "Market Advisory — AgriWise" };

export default function AdvisoryPage() {
  return <AdvisoryClient />;
}
