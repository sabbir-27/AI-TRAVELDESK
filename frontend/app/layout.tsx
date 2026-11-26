import type { Metadata } from "next";
import React from "react";

import { Providers } from "@/components/providers";
import "./globals.css";

export const metadata: Metadata = {
  title: "AI TravelDesk | Enterprise B2B Travel Agency Operating Platform",
  description:
    "Multi-tenant AI flight booking automation and white-label travel operations SaaS.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className="min-h-screen bg-[var(--background)] text-[var(--foreground)]">
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
