import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",
  reactStrictMode: true,
  images: {
    remotePatterns: [
      { protocol: "https", hostname: "avatars.githubusercontent.com" },
      { protocol: "https", hostname: "**.gravatar.com" },
    ],
  },
  async rewrites() {
    // Proxy API calls in dev so the browser avoids CORS entirely.
    const api = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
    return [{ source: "/api/backend/:path*", destination: `${api}/api/v1/:path*` }];
  },
};

export default nextConfig;
