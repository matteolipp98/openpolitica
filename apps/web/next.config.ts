import type { NextConfig } from "next";

const config: NextConfig = {
  // I pacchetti del monorepo sono TypeScript sorgente con import ".js" (stile ESM)
  transpilePackages: ["@op/schema", "@op/affinita"],
  webpack(cfg) {
    cfg.resolve.extensionAlias = { ".js": [".ts", ".tsx", ".js"] };
    return cfg;
  },
  async headers() {
    return [
      {
        source: "/:path*",
        headers: [
          { key: "Referrer-Policy", value: "no-referrer" },
          { key: "X-Content-Type-Options", value: "nosniff" },
          { key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=()" },
        ],
      },
    ];
  },
};

export default config;
