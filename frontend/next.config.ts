import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactCompiler: true,
  async rewrites() {
    return [
      {
        source: "/data/images/:path*",
        destination: "http://localhost:8000/data/images/:path*",
      },
    ];
  },
};

export default nextConfig;
