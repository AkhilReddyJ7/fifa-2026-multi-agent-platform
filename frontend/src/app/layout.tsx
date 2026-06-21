import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "FIFA 2026 Platform",
  description: "AI-powered FIFA 2026 analysis platform",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="bg-gray-950 text-gray-100 min-h-screen">{children}</body>
    </html>
  );
}
