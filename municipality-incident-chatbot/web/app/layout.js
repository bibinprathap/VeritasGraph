export const metadata = {
  title: "Municipality Incident Reporting",
  description: "Report civic incidents — powered by VeritasGraph GraphRAG",
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
