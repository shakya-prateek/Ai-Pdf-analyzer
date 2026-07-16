import { dirname } from "node:path";
import { fileURLToPath } from "node:url";

const projectRoot = dirname(fileURLToPath(import.meta.url));

/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  outputFileTracingRoot: projectRoot,
  images: {
    remotePatterns: [
      { protocol: "http", hostname: "localhost", port: "8000", pathname: "/api/**" },
      { protocol: "http", hostname: "127.0.0.1", port: "8000", pathname: "/api/**" }
    ]
  }
};

export default nextConfig;
