import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  images: {
    remotePatterns: [
      { hostname: "books.google.com" },
      { hostname: "images.gr-assets.com" },
      { hostname: "covers.openlibrary.org" },
      { hostname: "s.gr-assets.com" },
    ],
  },
};

export default nextConfig;
