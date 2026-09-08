import type { Metadata } from "next";
import { ComingSoon } from "@/components/ComingSoon";

export const metadata: Metadata = { title: "Setup — AgriWise" };

export default function SetupPage() {
  return (
    <ComingSoon
      title="Setup"
      description="Commodity and province setup is under active development."
    />
  );
}
