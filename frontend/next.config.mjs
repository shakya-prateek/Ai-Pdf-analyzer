/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  images: {
    remotePatterns: [
      { protocol: "http", hostname: "localhost", port: "8000", pathname: "/api/**" },
      { protocol: "http", hostname: "127.0.0.1", port: "8000", pathname: "/api/**" }
    ]
  }
};

export default nextConfig;
