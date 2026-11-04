/** @type {import('next').NextConfig} */

// The browser only ever talks to /api/*; Next.js proxies it to the FastAPI
// backend. That keeps the UI free of CORS concerns and of hard-coded hosts.
// NOTE: rewrites are evaluated at build time, so BACKEND_URL must be set
// when running `next build`.
const backendUrl = process.env.BACKEND_URL ?? "http://localhost:8000";

const nextConfig = {
  async rewrites() {
    return [{ source: "/api/:path*", destination: `${backendUrl}/:path*` }];
  },
};

export default nextConfig;
