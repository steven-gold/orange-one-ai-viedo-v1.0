import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  poweredByHeader: false,
  allowedDevOrigins: ["*.monkeycode-ai.online", "**.monkeycode-ai.online"],
};

export default nextConfig;
