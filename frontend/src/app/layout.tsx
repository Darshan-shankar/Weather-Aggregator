import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Weather Aggregator",
  description: "Fetch and browse stored weather readings",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
