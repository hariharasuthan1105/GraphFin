import { defineConfig } from "@playwright/test";
export default defineConfig({
  testDir: "./tests",
  timeout: 30000,
  workers: 1,
  fullyParallel: false,
  use: {
    baseURL: process.env.TEST_URL || "http://127.0.0.1:5173/GraphFin/",
    channel: "msedge",
    headless: true,
    viewport: { width: 1440, height: 1000 },
  },
  reporter: [
    ["list"],
    [
      "json",
      {
        outputFile:
          process.env.TEST_REPORT || "../../../work/phase8/browser-tests.json",
      },
    ],
  ],
  outputDir: "../../../work/phase8/browser-test-artifacts",
});
