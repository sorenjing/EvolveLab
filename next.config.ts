import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // 输出独立产物，配合 Docker 多阶段构建生成更小镜像
  output: "standalone",
};

export default nextConfig;
