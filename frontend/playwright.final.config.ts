import { defineConfig } from "@playwright/test";
import original from "./playwright.graph.config";
export default defineConfig({ ...original,
  testDir: "./.phase10-tests",
  timeout: 60000,
  use: { ...original.use, baseURL: process.env.TEST_URL || "http://127.0.0.1:4190/GraphFin/" },
  outputDir: "../../../phase10/browser-artifacts",
  reporter: [["list"], ["json", { outputFile: process.env.TEST_REPORT || "../../../phase10/browser.json" }]],
});
