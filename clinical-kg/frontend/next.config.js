/** @type {import('next').NextConfig} */
// Optional reverse-proxy subpath (e.g. "/clinical" when fronted by nginx/ngrok).
// Empty by default so local dev and root deployments are unaffected.
const basePath = (process.env.CLINICAL_BASE_PATH || "").replace(/\/$/, "");

const nextConfig = {
  reactStrictMode: true,
  ...(basePath
    ? { basePath, assetPrefix: basePath, env: { NEXT_PUBLIC_BASE_PATH: basePath } }
    : {}),
  async rewrites() {
    const api = process.env.NEXT_PUBLIC_API_BASE || "http://127.0.0.1:8700";
    return [{ source: "/api/:path*", destination: `${api}/:path*` }];
  },
};

module.exports = nextConfig;
