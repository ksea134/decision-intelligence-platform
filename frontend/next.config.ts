import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "export",  // 静的エクスポート（Cloud Runで配信）
  devIndicators: {
    position: "bottom-right",
  },
};

export default nextConfig;
