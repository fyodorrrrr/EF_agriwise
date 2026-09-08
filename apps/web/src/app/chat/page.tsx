import type { Metadata } from "next";
import ChatClient from "./ChatClient";

export const metadata: Metadata = { title: "Chat — AgriWise" };

export default function ChatPage() {
  return <ChatClient />;
}
