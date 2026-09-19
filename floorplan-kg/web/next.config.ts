import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // The engine subprocess can take a few seconds on an 8-sheet construction set.
  experimental: { proxyTimeout: 120_000 },
  outputFileTracingRoot: process.cwd(),
};

export default nextConfig;
