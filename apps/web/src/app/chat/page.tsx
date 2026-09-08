import type { Metadata } from "next";
import { ComingSoon } from "@/components/ComingSoon";

export const metadata: Metadata = { title: "Chat — AgriWise" };

export default function ChatPage() {
  return (
    <ComingSoon
      title="Chat"
      description="The AgriWise assistant chat is under active development."
    />
  );
}
