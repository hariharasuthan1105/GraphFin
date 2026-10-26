import { defineConfig } from "@playwright/test";
import original from "./playwright.config";
export default defineConfig({
  ...original,
  timeout: 45000,
  outputDir: "../../../phase9/browser-artifacts",
  reporter: [
    ["list"],
    [
      "json",
      {
        outputFile:
          process.env.TEST_REPORT || "../../../phase9/browser-tests.json",
      },
    ],
  ],
  use: {
    ...original.use,
    baseURL: process.env.TEST_URL || "http://127.0.0.1:4190/GraphFin/",
  },
});
