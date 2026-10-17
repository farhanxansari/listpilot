import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "ListPilot",
  description: "AI agent that turns used-car photos into a verified, priced listing",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-ground font-sans text-ink antialiased">{children}</body>
    </html>
  );
}