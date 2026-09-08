import type { Metadata, Viewport } from "next";
import { Plus_Jakarta_Sans, JetBrains_Mono } from "next/font/google";
import { AppShell } from "@/components/layout/AppShell";
import { AppPreferencesProvider } from "@/lib/preferences";
import "./globals.css";

const jakarta = Plus_Jakarta_Sans({
  variable: "--font-jakarta",
  subsets: ["latin"],
});

const jetbrainsMono = JetBrains_Mono({
  variable: "--font-jetbrains",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "AgriWise",
  description:
    "Province-resolution demand, supply, price, and opportunity analytics for CALABARZON agriculture.",
};

// viewport-fit=cover so the fixed bottom tab bar can honour env(safe-area-inset-*)
// on notched phones. Pinch-zoom stays enabled — no maximumScale / userScalable.
export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  viewportFit: "cover",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html
      lang="en"
      className={`${jakarta.variable} ${jetbrainsMono.variable} h-full antialiased`}
    >
      <body className="h-full">
        <AppPreferencesProvider>
          <AppShell>{children}</AppShell>
        </AppPreferencesProvider>
      </body>
    </html>
  );
}
