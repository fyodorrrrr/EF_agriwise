import type { Metadata } from "next";

import { ModelEvidenceClient } from "./ModelEvidenceClient";

export const metadata: Metadata = { title: "Model Evidence — AgriWise" };

export default function ModelEvidencePage() {
  return <ModelEvidenceClient />;
}
