/** @type {import('next').NextConfig} */
const BACKEND = process.env.BACKEND_URL || "http://127.0.0.1:8899";

const nextConfig = {
  // Next 16 blocks /_next/* dev resources for hosts it treats as cross-origin
  // (e.g. 127.0.0.1). Playwright drives 127.0.0.1, so allow it or the client
  // bundle never hydrates and useEffect never runs.
  allowedDevOrigins: ["127.0.0.1", "localhost"],
  // Proxy /api/* to the FastAPI backend so the browser makes same-origin
  // requests (no CORS, and Playwright drives one origin).
  async rewrites() {
    return [{ source: "/api/:path*", destination: `${BACKEND}/api/:path*` }];
  },
};

export default nextConfig;
