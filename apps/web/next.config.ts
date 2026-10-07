import type { NextConfig } from "next";

const config: NextConfig = {
  // Sito tutto statico (ADR 0036): nessun server, nessun modello a runtime.
  output: "export",
  // I pacchetti del monorepo sono TypeScript sorgente con import ".js" (stile ESM)
  transpilePackages: ["@op/schema", "@op/affinita"],
  webpack(cfg) {
    cfg.resolve.extensionAlias = { ".js": [".ts", ".tsx", ".js"] };
    return cfg;
  },
};

export default config;
