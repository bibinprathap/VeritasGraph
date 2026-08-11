import "./globals.css";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Clinical Knowledge Graph — VeritasGraph",
  description:
    "HIPAA-safe clinical knowledge graph: on-device de-identification, entity extraction, contradiction detection, and multi-hop cohort queries with citations.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
