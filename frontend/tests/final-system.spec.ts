import { test, expect } from "@playwright/test";
import { mkdirSync, readFileSync, writeFileSync } from "node:fs";
const folder = "../../../phase10";

test("complete saved-evidence demonstration and preserved legacy entry", async ({ page }) => {
  test.setTimeout(180000);
  const errors: string[] = [], mutations: string[] = [];
  page.on("pageerror", e => errors.push(e.message));
  page.on("request", r => { if (r.url().includes("/api/") && r.method() !== "GET") mutations.push(r.method()+" "+new URL(r.url()).pathname); });
  await page.addInitScript(() => {
    (window as any).__lab = { lcp: 0, cls: 0 };
    new PerformanceObserver(list => { for (const e of list.getEntries()) (window as any).__lab.lcp = e.startTime; }).observe({ type: "largest-contentful-paint", buffered: true });
    new PerformanceObserver(list => { for (const e of list.getEntries() as any) if (!e.hadRecentInput) (window as any).__lab.cls += e.value; }).observe({ type: "layout-shift", buffered: true });
  });
  await page.goto("#/overview");
  await expect(page.getByText("84 method evaluations")).toBeVisible();
  const performance = await page.evaluate(() => ({ ...(window as any).__lab,
    navigation: window.performance.getEntriesByType("navigation")[0].toJSON(),
    heapBytes: (window.performance as any).memory?.usedJSHeapSize ?? null }));
  await page.getByRole("link", { name: /Datasets/ }).click();
  await page.getByRole("button", { name: "IBM AML 5k", exact: true }).click();
  await expect(page.getByRole("heading", { name: "IBM AML 5k", exact: true })).toBeVisible();
  await expect(page.getByText("partially verified", { exact: true }).first()).toBeVisible();
  await page.getByRole("link", { name: /Model Comparison/ }).click();
  await expect(page.getByRole("heading", { name: "Compatible model comparison" })).toBeVisible({ timeout: 30000 });
  for (const method of ["E0", "E1", "E2", "E3", "E4", "E5"]) await expect(page.getByRole("cell", { name: method, exact: true }).first()).toBeVisible();
  await page.getByRole("link", { name: /Seed Analysis/ }).click();
  await expect(page.getByRole("heading", { name: "Six-split analysis" })).toBeVisible();
  await page.getByRole("combobox", { name: "Evidence axis" }).selectOption("model");
  await expect(page.getByRole("heading", { name: "Ranking overlap" })).toBeVisible();
  await page.getByRole("link", { name: /Reproducibility/ }).click();
  await expect(page.getByRole("heading", { name: "Replay verification" })).toBeVisible();
  await page.getByRole("link", { name: /CREST Diagnostics/ }).click();
  await page.getByRole("button", { name: "crest-001", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Saved evidence sensitivity" })).toBeVisible();
  await page.getByRole("link", { name: /Experiments/ }).click();
  await page.getByRole("combobox", { name: "Method", exact: true }).selectOption("E4");
  await page.getByRole("button", { name: "baseline-5k-E4-s42-m42", exact: true }).click();
  await page.getByRole("button", { name: "metrics", exact: true }).click();
  await expect(page.getByRole("table").last()).toContainText("Confidence interval");
  await page.getByRole("button", { name: "provenance", exact: true }).click();
  await expect(page.getByText("test sha256")).toBeVisible();
  await page.getByRole("button", { name: "rankings", exact: true }).click();
  await page.getByRole("link", { name: "Open approved graph", exact: false }).first().click();
  await page.getByRole("button", { name: "Open approved graph lens" }).click();
  await expect(page.locator(".graph-stage")).toBeVisible();
  await page.locator(".graph-access-list").getByRole("button").first().click();
  await expect(page.getByRole("heading", { name: "Account detail" })).toBeVisible();
  await page.getByRole("button", { name: /Relationships \(/ }).click();
  await page.getByRole("button", { name: "Inspect relationship 1", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Relationship detail" })).toBeVisible();
  await page.getByRole("link", { name: "Dataset Explorer → Download Dataset Report (PDF)" }).click();
  await expect(page.getByRole("heading", { name: "IBM AML 5k", exact: true })).toBeVisible();
  const pending = page.waitForEvent("download");
  await page.getByRole("button", { name: "Download Dataset Report (PDF)" }).click();
  expect((await pending).suggestedFilename()).toContain("ibm-5k");
  await page.getByRole("link", { name: /Research Limitations/ }).click();
  await expect(page.getByRole("heading", { name: "Read the status precisely" })).toBeVisible();
  await page.getByRole("link", { name: /Existing analysis workspace/ }).click();
  await expect(page.locator("#root")).toContainText("GraphFin");
  expect(errors).toEqual([]); expect(mutations).toEqual([]);
  writeFileSync(folder+"/final-workflow.json", JSON.stringify({ errors, mutations, performance,
    conditions: "Headless Edge; localhost; normal-startup disposable API; production frontend. Lab vitals, not field INP." }, null, 2));
});

test("three genuine dataset PDF downloads for visual and numerical review", async ({ page }) => {
  const pdfs = folder+"/pdf"; mkdirSync(pdfs, { recursive: true });
  const results: unknown[] = [];
  await page.goto("#/datasets");
  for (const [id, name] of [["ibm-5k", "IBM AML 5k"], ["ibm-50k", "IBM AML 50k"], ["paysim", "PaySim"]]) {
    await page.getByRole("button", { name, exact: true }).click();
    await expect(page.getByRole("heading", { name, exact: true })).toBeVisible();
    const start = Date.now(), pending = page.waitForEvent("download");
    await page.getByRole("button", { name: "Download Dataset Report (PDF)" }).click();
    const download = await pending;
    expect(download.suggestedFilename()).toBe(`GraphFin_${id}_dataset_report.pdf`);
    const path = pdfs+"/"+download.suggestedFilename(); await download.saveAs(path);
    const bytes = readFileSync(path); expect(bytes.subarray(0,5).toString()).toBe("%PDF-");
    results.push({ dataset: id, bytes: bytes.length, downloadMs: Date.now()-start });
  }
  writeFileSync(folder+"/pdf-downloads.json", JSON.stringify(results, null, 2));
});
