import { test, expect } from "@playwright/test";
import { mkdirSync, writeFileSync } from "node:fs";
test("verified real graph explorer, sparse/dense cases and saved evidence", async ({
  page,
}) => {
  test.setTimeout(90000);
  const folder = "../../../phase9/visual";
  mkdirSync(folder, { recursive: true });
  const errors: string[] = [];
  const calls: { path: string; status: number }[] = [];
  const queries: any[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  page.on("response", async (r) => {
    if (r.url().includes("/api/v1/graph-explorer")) {
      calls.push({ path: new URL(r.url()).pathname, status: r.status() });
      if (r.url().includes("/neighborhood")) queries.push(await r.json());
    }
  });
  await page.goto("#/overview");
  await expect(page.getByText("84 method evaluations")).toBeVisible();
  const initialJS = await page.evaluate(() =>
    performance
      .getEntriesByType("resource")
      .filter((x: any) => x.name.endsWith(".js"))
      .map((x) => x.name),
  );
  expect(
    initialJS.some((x) => /GraphExplorer|layout\.worker|manyBody/.test(x)),
  ).toBe(false);
  await page.getByRole("link", { name: /Graph Explorer/ }).click();
  await expect(
    page.getByRole("heading", { name: "Graph Explorer", exact: true }),
  ).toBeVisible();
  const observations: unknown[] = [];
  async function applyCase(dataset: string, role: string) {
    const option = await page
      .getByRole("combobox", { name: "Focus account" })
      .locator("option")
      .evaluateAll(
        (list, role) =>
          list
            .find((n) => n.textContent?.includes(role as string))
            ?.getAttribute("value"),
        role,
      );
    expect(option).toBeTruthy();
    await page
      .getByRole("combobox", { name: "Focus account" })
      .selectOption(option!);
    await page.getByLabel("Neighborhood depth").selectOption("2");
    await page.getByLabel("Visible node limit").selectOption("250");
    const start = Date.now();
    await page.getByRole("button", { name: "Apply server filters" }).click();
    await expect(page.getByRole("button", { name: "Apply server filters" })).toBeEnabled();
    await expect(page.locator(".graph-stage")).toBeVisible();
    await expect(page.locator(".graph-stage")).toBeVisible();
    const elapsed = Date.now() - start;
    const q = queries.at(-1);
    expect(q.dataset_id).toBe(dataset);
    expect(q.nodes.length).toBeLessThanOrEqual(250);
    expect(q.edges.length).toBeLessThanOrEqual(500);
    const layoutMs = Number(
      await page.locator(".graph-stage").getAttribute("data-layout-ms"),
    );
    const workerReadyMs = Number(await page.locator(".graph-stage").getAttribute("data-worker-ready-ms"));
    const before = Date.now();
    await page.getByRole("button", { name: "Zoom in", exact: true }).click();
    const zoomButtonReadyMs = Date.now() - before;
    const nodeButton = page
      .locator(".graph-access-list")
      .getByRole("button")
      .first();
    const selectionStart = Date.now();
    await nodeButton.click();
    await expect(
      page.getByRole("heading", { name: "Account detail" }),
    ).toBeVisible();
    const nodeSelectionMs = Date.now() - selectionStart;
    const heap = await page.evaluate(
      () => (performance as any).memory?.usedJSHeapSize ?? null,
    );
    observations.push({
      dataset,
      role,
      nodes: q.nodes.length,
      edges: q.edges.length,
      payloadBytes: new TextEncoder().encode(JSON.stringify(q)).byteLength,
      serverSeconds: q.query_seconds,
      graphReadyMs: elapsed,
      layoutMs,
      workerReadyMs,
      nodeSelectionMs,
      zoomButtonReadyMs,
      heapBytes: heap,
      truncation: q.truncation_reasons,
    });
    await page.getByRole("button", { name: "Fit", exact: true }).click();
    await page.screenshot({
      path: `${folder}/${dataset}-${role}.png`,
      fullPage: true,
      animations: "disabled",
    });
  }
  for (const dataset of ["ibm-5k", "ibm-50k"]) {
    await page.getByLabel("Dataset and tier").selectOption(dataset);
    const start = Date.now();
    await page
      .getByRole("button", { name: "Open approved graph lens" })
      .click();
    await expect(page.locator(".graph-stage")).toBeVisible();
    observations.push({
      dataset,
      sessionAndInitialReadyMs: Date.now() - start,
    });
    if (dataset === "ibm-5k") {
      const rank = await page.request.get(
        "/api/v1/research/experiments/baseline-5k-E4-s42-m42/rankings?page_size=1",
      );
      const first = (await rank.json()).items[0];
      await expect(page.locator(".graph-inspector")).toContainText(
        first.account_token,
      );
    }
    await applyCase(dataset, "high-degree");
    await applyCase(dataset, "low-degree");
    if (dataset === "ibm-5k") {
      const option = await page
        .getByRole("combobox", { name: "Focus account" })
        .locator("option")
        .evaluateAll((list) =>
          list
            .find((n) => n.textContent?.includes("compatible saved diagnostic"))
            ?.getAttribute("value"),
        );
      expect(option).toBeTruthy();
      await page
        .getByRole("combobox", { name: "Focus account" })
        .selectOption(option!);
      await page.getByRole("button", { name: "Apply server filters" }).click();
    await expect(page.getByRole("button", { name: "Apply server filters" })).toBeEnabled();
    await expect(page.locator(".graph-stage")).toBeVisible();
      await expect(
        page.getByRole("combobox", { name: "Compatible saved diagnostic", exact: true }),
      ).toBeVisible();
      const id = await page
        .getByRole("combobox", { name: "Compatible saved diagnostic", exact: true })
        .locator("option")
        .nth(1)
        .getAttribute("value");
      const label = await page
        .getByRole("combobox", { name: "Compatible saved diagnostic", exact: true })
        .locator("option")
        .nth(1)
        .textContent();
      await page
        .getByRole("combobox", { name: "Compatible saved diagnostic", exact: true })
        .selectOption(id || label!);
      await expect(
        page.getByRole("heading", {
          name: "Experimental model-sensitivity diagnostic",
        }),
      ).toBeVisible();
      await page.screenshot({
        path: folder + "/crest-unavailable.png",
        fullPage: true,
        animations: "disabled",
      });
      const candidates = await page.getByRole("combobox", { name: "Compatible saved diagnostic", exact: true }).locator("option").allTextContents();
      let availableId: string | undefined;
      for (const candidate of candidates.slice(1)) {
        const response = await page.request.get("/api/v1/research/diagnostics/" + candidate);
        if ((await response.json()).available) { availableId = candidate; break; }
      }
      expect(availableId).toBeTruthy();
      await page.getByRole("combobox", { name: "Compatible saved diagnostic", exact: true }).selectOption(availableId!);
      await expect(page.locator(".graph-inspector dd").filter({ hasText: availableId! })).toBeVisible();
      await page.screenshot({ path: folder + "/crest-compatible.png", fullPage: true, animations: "disabled" });

    }
  }
  await page.getByLabel("Minimum aggregate amount").fill("1000000000000000");
  await page.getByRole("button", { name: "Apply server filters" }).click();
    await expect(page.getByRole("button", { name: "Apply server filters" })).toBeEnabled();
    await expect(
    page.getByText("No relationships match this bounded query.", {
      exact: false,
    }),
  ).toBeVisible();
  await page.screenshot({
    path: folder + "/empty-neighborhood.png",
    fullPage: true,
    animations: "disabled",
  });
  await page.getByLabel("Minimum aggregate amount").fill("0");
  await page.getByRole("button", { name: "Apply server filters" }).click();
    await expect(page.getByRole("button", { name: "Apply server filters" })).toBeEnabled();
    await expect(page.locator(".graph-stage")).toBeVisible();
  await expect(page.locator(".graph-stage")).toBeVisible();
  await page.getByRole("button", { name: /Relationships \(/ }).click();
  await page
    .getByRole("button", { name: "Inspect relationship 1", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "Relationship detail" }),
  ).toBeVisible();
  await page.screenshot({
    path: folder + "/selected-edge.png",
    fullPage: true,
    animations: "disabled",
  });
  for (const width of [360, 430, 768, 1280]) {
    await page.setViewportSize({ width, height: 1000 });
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
    ).toBe(true);
    await page.screenshot({
      path: `${folder}/responsive-${width}.png`,
      fullPage: true,
      animations: "disabled",
    });
  }
  await page.getByLabel("Dataset and tier").selectOption("paysim");
  await expect(
    page.getByText("Topology unavailable:", { exact: false }),
  ).toBeVisible();
  await page.screenshot({
    path: folder + "/topology-unavailable.png",
    fullPage: true,
    animations: "disabled",
  });
  await page
    .getByRole("link", {
      name: "Dataset Explorer → Download Dataset Report (PDF)",
    })
    .click();
  await expect(
    page.getByRole("heading", { name: "PaySim", exact: true }),
  ).toBeVisible();
  const download = page.waitForEvent("download");
  await page
    .getByRole("button", { name: "Download Dataset Report (PDF)" })
    .click();
  expect((await download).suggestedFilename()).toContain("paysim");
  expect(errors).toEqual([]);
  expect(calls.every((x) => x.status === 200)).toBe(true);
  writeFileSync(
    "../../../phase9/browser-real-performance.json",
    JSON.stringify(
      {
        conditions:
          "Headless Edge; local production preview and indexed API; no CPU/network throttling; live graph responses, no fixture topology.",
        initialJS,
        observations,
        calls,
        errors,
        limitations: [
          "Interaction times include test polling and are not field INP.",
          "Heap samples are not long-duration leak measurements.",
          "Screenshots stabilized finite CSS entrances.",
        ],
      },
      null,
      2,
    ),
  );
});
