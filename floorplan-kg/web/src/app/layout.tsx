import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Floorplan Knowledge Graph & Takeoff",
  description:
    "Turn architectural floorplan PDFs into a queryable knowledge graph, quantity takeoffs, and Excel/CSV schedule exports — fully offline.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
