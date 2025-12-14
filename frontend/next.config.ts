import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  async rewrites() {
    return [
      {
        source: "/auth/:path*",
        destination: "http://127.0.0.1:8000/auth/:path*",
      },
      {
        source: "/student/:path*",
        destination: "http://127.0.0.1:8000/student/:path*",
      },
      {
        source: "/teacher/:path*",
        destination: "http://127.0.0.1:8000/teacher/:path*",
      },
      {
        source: "/admin/:path*",
        destination: "http://127.0.0.1:8000/admin/:path*",
      },
    ];
  },
};

export default nextConfig;
