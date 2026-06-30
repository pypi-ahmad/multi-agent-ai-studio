import type { Metadata } from "next";
import "./globals.css";

import { AppShell } from "@/components/layout/app-shell";

export const metadata: Metadata = {
  title: "Multi-Agent AI Studio",
  description: "Production-grade local agentic AI platform powered by Ollama",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <body>
        <AppShell>{children}</AppShell>
      </body>
    </html>
  );
}
