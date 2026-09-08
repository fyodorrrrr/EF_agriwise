import type { Metadata } from "next";
import { ComingSoon } from "@/components/ComingSoon";

export const metadata: Metadata = { title: "Model Evidence — AgriWise" };

export default function ModelEvidencePage() {
  return (
    <ComingSoon
      title="Model Evidence"
      description="Model evidence and explainability views are under active development."
    />
  );
}
