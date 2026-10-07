import { defineConfig } from "@playwright/test";

// Test nel browser sul sito già costruito (out/). In CI: pnpm build && pnpm test:e2e
export default defineConfig({
  testDir: "e2e",
  use: {
    baseURL: "http://localhost:4310",
    viewport: { width: 390, height: 844 },
    launchOptions: process.env.PLAYWRIGHT_CHROMIUM ? { executablePath: process.env.PLAYWRIGHT_CHROMIUM } : {},
  },
  webServer: { command: "node e2e/server.mjs", url: "http://localhost:4310/", reuseExistingServer: true },
});
