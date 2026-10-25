import { test, expect } from "@playwright/test";
import { writeFileSync } from "node:fs";
test("bounded production loading and route interaction measurements", async ({
  page,
}) => {
  const samples: unknown[] = [];
  await page.addInitScript(() => {
    (window as any).__lab = { lcp: 0, cls: 0 };
    new PerformanceObserver((list) => {
      for (const e of list.getEntries())
        (window as any).__lab.lcp = e.startTime;
    }).observe({ type: "largest-contentful-paint", buffered: true });
    new PerformanceObserver((list) => {
      for (const e of list.getEntries() as any)
        if (!e.hadRecentInput) (window as any).__lab.cls += e.value;
    }).observe({ type: "layout-shift", buffered: true });
  });
  for (let i = 0; i < 3; i++) {
    const start = Date.now();
    await page.goto("/GraphFin/?lab=" + i + "#/overview");
    await expect(page.getByText("84 method evaluations")).toBeVisible();
    const evidenceReadyMs = Date.now() - start;
    await page.evaluate(() => document.fonts.ready);
    await page.waitForTimeout(300);
    const sample = await page.evaluate(() => ({
      ...(window as any).__lab,
      heapBytes: (performance as any).memory?.usedJSHeapSize ?? null,
      navigation: performance.getEntriesByType("navigation")[0].toJSON(),
      api: performance
        .getEntriesByType("resource")
        .filter((r: any) => r.name.includes("/api/"))
        .map((r: any) => ({ name: r.name, duration: r.duration })),
      loadedJS: performance
        .getEntriesByType("resource")
        .filter((r: any) => r.name.endsWith(".js"))
        .map((r: any) => r.name),
    }));
    const click = Date.now();
    await page.getByRole("link", { name: /Research Limitations/ }).click();
    await expect(
      page.getByRole("heading", { name: "Research limitations", exact: true }),
    ).toBeVisible();
    samples.push({
      ...sample,
      evidenceReadyMs,
      routeHeadingReadyMs: Date.now() - click,
    });
  }
  writeFileSync(
    "../../../work/phase8/production-performance.json",
    JSON.stringify(
      {
        conditions:
          "Edge headless, local Vite production preview, localhost backend, 1440x1000, no CPU/network throttle; three navigations in one browser context, cache warm after first.",
        samples,
        inp: "Not measured as a field metric. routeHeadingReadyMs is a lab navigation check, not INP.",
        memory: "JS heap observations only; no long-duration leak claim.",
      },
      null,
      2,
    ),
  );
});
