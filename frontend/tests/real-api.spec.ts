import { test, expect } from "@playwright/test";
import { mkdirSync, writeFileSync } from "node:fs";
import { resolve } from "node:path";
const output = resolve(process.env.VISUAL_DIR || "../../../work/phase8/visual");
mkdirSync(output, { recursive: true });
test("actual saved API evidence and rendered research workflow", async ({
  page,
}) => {
  const calls: { url: string; status: number; method: string }[] = [];
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  page.on("response", (r) => {
    if (r.url().includes("/api/v1/research"))
      calls.push({
        url: r.url(),
        status: r.status(),
        method: r.request().method(),
      });
  });
  await page.addInitScript(() => {
    (window as any).__vitals = { lcp: 0, cls: 0 };
    new PerformanceObserver((l) => {
      for (const e of l.getEntries())
        (window as any).__vitals.lcp = e.startTime;
    }).observe({ type: "largest-contentful-paint", buffered: true });
    new PerformanceObserver((l) => {
      for (const e of l.getEntries() as any)
        if (!e.hadRecentInput) (window as any).__vitals.cls += e.value;
    }).observe({ type: "layout-shift", buffered: true });
  });
  await page.goto("#/overview");
  await expect(page.getByText("84 method evaluations")).toBeVisible();
  await page.evaluate(() => document.fonts.ready);
  await page.screenshot({
    path: resolve(output, "overview-desktop.png"),
    fullPage: true,
    animations: "disabled",
  });
  const performance = await page.evaluate(() => ({
    ...(window as any).__vitals,
    navigation: performance.getEntriesByType("navigation")[0].toJSON(),
    memory: (performance as any).memory
      ? {
          usedJSHeapSize: (performance as any).memory.usedJSHeapSize,
          totalJSHeapSize: (performance as any).memory.totalJSHeapSize,
        }
      : null,
    resources: performance
      .getEntriesByType("resource")
      .map((r: any) => ({
        name: r.name,
        duration: r.duration,
        transferSize: r.transferSize,
      })),
  }));
  await page.getByRole("link", { name: /Datasets/ }).click();
  await page.getByRole("button", { name: "PaySim", exact: true }).click();
  await expect(page.getByText("paysim-research-774")).toBeVisible();
  await expect(page.getByText("paysim-application-2606")).toBeVisible();
  await page.getByRole("link", { name: /Model Comparison/ }).click();
  await expect(
    page.getByRole("heading", { name: "Compatible model comparison" }),
  ).toBeVisible();
  await page.screenshot({
    path: resolve(output, "comparison-desktop.png"),
    fullPage: true,
    animations: "disabled",
  });
  await page.getByRole("link", { name: /Seed Analysis/ }).click();
  await expect(
    page.getByText("SD is not a confidence interval.", { exact: false }),
  ).toBeVisible();
  await page.getByLabel("Evidence axis").selectOption("model");
  await expect(
    page.getByRole("heading", { name: "Ranking overlap" }),
  ).toBeVisible();
  await page.getByRole("link", { name: /Reproducibility/ }).click();
  await expect(
    page.getByRole("heading", { name: "Replay verification" }),
  ).toBeVisible();
  await page.getByRole("link", { name: /CREST Diagnostics/ }).click();
  await page.getByRole("button", { name: "crest-000" }).click();
  await expect(
    page.getByRole("heading", { name: "Saved evidence sensitivity" }),
  ).toBeVisible();
  await page.getByRole("link", { name: /Experiments/ }).click();
  await page
    .getByRole("combobox", { name: "Method", exact: true })
    .selectOption("E4");
  await page
    .getByRole("button", { name: "baseline-5k-E4-s42-m42", exact: true })
    .click();
  await page.getByRole("button", { name: "metrics", exact: true }).click();
  await expect(page.getByRole("table").last()).toContainText(
    "Confidence interval",
  );
  await page.getByRole("button", { name: "provenance", exact: true }).click();
  await expect(page.getByText("test sha256")).toBeVisible();
  await page.getByRole("button", { name: "rankings", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Held-out account rankings" }),
  ).toBeVisible();
  await expect(page.getByRole("cell", { name: /acct_/ }).first()).toBeVisible();
  await page.getByRole("button", { name: "Next →" }).last().click();
  await expect(page.getByText("1,500 records", { exact: false })).toHaveCount(
    0,
  );
  await expect(
    page.getByText("1500 records / page 2", { exact: false }),
  ).toBeVisible();
  await page.getByRole("link", { name: /Research Limitations/ }).click();
  await expect(
    page.getByRole("heading", { name: "Read the status precisely" }),
  ).toBeVisible();
  for (const width of [390, 768, 1280, 1920]) {
    await page.setViewportSize({ width, height: 1000 });
    await page.goto("#/overview");
    await expect(page.getByText("84 method evaluations")).toBeVisible();
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
    ).toBe(true);
    await page.screenshot({
      path: resolve(output, `overview-${width}.png`),
      fullPage: true,
      animations: "disabled",
    });
  }
  expect(errors).toEqual([]);
  expect(calls.every((x) => x.status === 200 && x.method === "GET")).toBe(true);
  writeFileSync(
    resolve(output, "real-api.json"),
    JSON.stringify(
      {
        calls,
        errors,
        performance,
        conditions:
          "Local development build, warm local backend, Edge headless, desktop initial navigation; lab vitals, not field INP.",
      },
      null,
      2,
    ),
  );
});
