import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "export",  // 静的エクスポート（Cloud Runで配信）
};

export default nextConfig;
