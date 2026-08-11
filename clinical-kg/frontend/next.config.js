/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  async rewrites() {
    const api = process.env.NEXT_PUBLIC_API_BASE || "http://127.0.0.1:8300";
    return [{ source: "/api/:path*", destination: `${api}/:path*` }];
  },
};

module.exports = nextConfig;
