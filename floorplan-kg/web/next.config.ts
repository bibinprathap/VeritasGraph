import type { NextConfig } from "next";

// Optional reverse-proxy subpath (e.g. "/floorplan" when fronted by nginx).
// Empty by default so local dev and root deployments are unaffected.
const basePath = process.env.FLOORPLAN_BASE_PATH?.replace(/\/$/, "") || "";

const nextConfig: NextConfig = {
  // The engine subprocess can take a few seconds on an 8-sheet construction set.
  experimental: { proxyTimeout: 120_000 },
  outputFileTracingRoot: process.cwd(),
  ...(basePath
    ? { basePath, assetPrefix: basePath, env: { NEXT_PUBLIC_BASE_PATH: basePath } }
    : {}),
};

export default nextConfig;
