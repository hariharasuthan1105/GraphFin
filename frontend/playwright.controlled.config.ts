import { defineConfig } from "@playwright/test";
import original from "./playwright.final.config";

export default defineConfig({
  ...original,
  testDir: "./.phase10r-tests",
  use: {
    ...original.use,
    baseURL: process.env.TEST_URL || "http://127.0.0.1:4290/GraphFin/",
  },
  outputDir: "../../../phase10r/browser-artifacts",
  reporter: [
    ["list"],
    ["json", { outputFile: process.env.TEST_REPORT || "../../../phase10r/browser.json" }],
  ],
});
