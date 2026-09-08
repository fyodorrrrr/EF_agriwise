import type { Metadata } from "next";
import { ComingSoon } from "@/components/ComingSoon";

export const metadata: Metadata = { title: "Markets — AgriWise" };

export default function MarketsPage() {
  return (
    <ComingSoon
      title="Markets"
      description="The curated markets directory is under active development."
    />
  );
}
