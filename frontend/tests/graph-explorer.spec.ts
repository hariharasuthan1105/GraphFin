import { test, expect, type Page } from "@playwright/test";
import {
  graphCatalog,
  graphSession,
  graphNeighborhood,
  nodeRef,
} from "./graph-fixtures";
import { response, diagnostic } from "./fixtures";

test.beforeEach(async ({ page }) => {
  await page.route("**/api/v1/research/**", (r) =>
    r.fulfill({
      json: r.request().url().includes("/diagnostics/")
        ? {
            ...diagnostic,
            baseline_score: 0.9,
            intervened_score: 0.7,
            signed_fidelity: 0.2,
          }
        : response(new URL(r.request().url())),
    }),
  );
  await page.route("**/api/v1/graph-explorer/**", (r) => {
    const url = new URL(r.request().url());
    expect(r.request().method()).toBe("GET");
    return r.fulfill({
      json: url.pathname.endsWith("/catalog")
        ? graphCatalog
        : url.pathname.endsWith("/session")
          ? graphSession
          : graphNeighborhood(url),
    });
  });
});
async function open(page: Page) {
  await page.goto("#/graph");
  await page.getByRole("button", { name: "Open approved graph lens" }).click();
  await expect(page.locator(".graph-stage")).toBeVisible();
}

test("loads bounded directed graph and explicit partial status", async ({
  page,
}) => {
  await open(page);
  await expect(
    page.getByText("Partial graph.", { exact: false }),
  ).toBeVisible();
  await expect(
    page.getByRole("img", { name: /Directed transaction neighborhood/ }),
  ).toBeVisible();
  expect(await page.locator("[data-graph-object=node]").count()).toBe(3);
  expect(
    await page.locator('path[marker-end="url(#graph-arrow)"]').count(),
  ).toBe(2);
  await expect(
    page.getByText("Node statistics and reciprocity", { exact: false }),
  ).toHaveCount(0);
});
test("node and edge selection are accessible and preserve layout", async ({
  page,
}) => {
  await open(page);
  const ms = await page.locator(".graph-stage").getAttribute("data-layout-ms");
  await page
    .getByRole("button", { name: "acct_fixture_2", exact: true })
    .click();
  await expect(
    page
      .getByRole("region", { name: "Selected graph evidence" })
      .or(page.locator(".graph-inspector")),
  ).toContainText("0.5 / 2");
  expect(
    await page.locator(".graph-stage").getAttribute("data-layout-ms"),
  ).toBe(ms);
  await page.getByRole("button", { name: "Relationships (2)" }).click();
  await page
    .getByRole("button", { name: "Inspect relationship 1", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "Relationship detail" }),
  ).toBeVisible();
  await expect(page.locator(".graph-inspector")).toContainText(
    "Sender → receiver",
  );
  await expect(page.locator(".graph-inspector")).toContainText(
    "12 dataset units",
  );
});
test("SVG pointer selection works", async ({ page }) => {
  await open(page);
  await page.locator(`[data-node-ref="${nodeRef(2)}"]`).click();
  await expect(page.locator(".graph-inspector")).toContainText(
    "acct_fixture_2",
  );
});
test("zoom fit reset and pan", async ({ page }) => {
  await open(page);
  const group = page.locator(".graph-stage svg>g");
  const before = await group.getAttribute("transform");
  await page.getByRole("button", { name: "Zoom in", exact: true }).click();
  expect(await group.getAttribute("transform")).not.toBe(before);
  await page.getByRole("button", { name: "Reset view", exact: true }).click();
  await expect(group).toHaveAttribute("transform", "translate(0 0) scale(1)");
  const box = await page.locator(".graph-stage svg").boundingBox();
  await page.mouse.move(box!.x + 20, box!.y + 20);
  await page.mouse.down();
  await page.mouse.move(box!.x + 60, box!.y + 50);
  await page.mouse.up();
  await expect(group).not.toHaveAttribute(
    "transform",
    "translate(0 0) scale(1)",
  );
  await page.getByRole("button", { name: "Fit", exact: true }).click();
  expect(await group.getAttribute("transform")).toBe(before);
});
test("all graph filters are real server requests", async ({ page }) => {
  const urls: string[] = [];
  page.on("request", (r) => {
    if (r.url().includes("/neighborhood")) {
      urls.push(r.url());
      expect(r.headers()["x-graph-session"]).toBe("S".repeat(32));
      expect(r.url()).not.toContain("S".repeat(32));
    }
  });
  await open(page);
  await page.getByLabel("Neighborhood depth").selectOption("2");
  await page
    .getByRole("combobox", { name: "Direction", exact: true })
    .selectOption("incoming");
  await page.getByLabel("Minimum transaction count").fill("2");
  await page.getByLabel("Minimum aggregate amount").fill("1");
  await page.getByRole("button", { name: "Apply server filters" }).click();
  await expect
    .poll(() =>
      urls.some(
        (x) =>
          x.includes("depth=2") &&
          x.includes("direction=incoming") &&
          x.includes("min_count=2") &&
          x.includes("min_amount=1"),
      ),
    )
    .toBe(true);
});
test("temporal subwindow suppresses frozen annotations", async ({ page }) => {
  await open(page);
  await page.getByLabel("Full source time window").uncheck();
  await page.getByLabel("From (synthetic UTC)").fill("2020-01-02T00:00");
  await page.getByRole("button", { name: "Apply server filters" }).click();
  await expect(
    page.getByText("Temporal subset:", { exact: false }),
  ).toBeVisible();
  await expect(page.locator(".graph-inspector")).toContainText(
    "Unavailable for temporal subwindows.",
  );
  await expect(page.getByLabel("Compatible saved diagnostic")).toHaveCount(0);
});
test("empty relationships and no fabricated ranking", async ({ page }) => {
  await open(page);
  await page
    .getByRole("button", { name: "acct_fixture_3", exact: true })
    .click();
  await expect(page.locator(".graph-inspector")).toContainText(
    "outside this experiment",
  );
  await page.getByLabel("Minimum aggregate amount").fill("99999");
  await page.getByRole("button", { name: "Apply server filters" }).click();
  await expect(
    page.getByText("No relationships match this bounded query.", {
      exact: false,
    }),
  ).toBeVisible();
});
test("compatible saved CREST evidence and caveats", async ({ page }) => {
  await open(page);
  await page
    .getByLabel("Compatible saved diagnostic")
    .selectOption("crest-000");
  await expect(
    page.getByRole("heading", {
      name: "Experimental model-sensitivity diagnostic",
    }),
  ).toBeVisible();
  await expect(page.locator(".graph-inspector")).toContainText(
    "not causal evidence",
  );
  await expect(page.locator(".graph-inspector")).toContainText("0.2");
});
test("open selected account neighborhood", async ({ page }) => {
  const refs: string[] = [];
  page.on("request", (r) => {
    if (r.url().includes("/neighborhood"))
      refs.push(new URL(r.url()).searchParams.get("focus_ref")!);
  });
  await open(page);
  await page
    .getByRole("button", { name: "acct_fixture_2", exact: true })
    .click();
  await page.getByRole("button", { name: "Explore this account →" }).click();
  await expect.poll(() => refs.at(-1)).toBe(nodeRef(2));
});
test("unavailable topology is honest and report link selects dataset", async ({
  page,
}) => {
  await page.goto("#/graph");
  await page.getByLabel("Dataset and tier").selectOption("paysim");
  await expect(
    page.getByText("Topology unavailable:", { exact: false }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Open approved graph lens" }),
  ).toHaveCount(0);
  await page
    .getByRole("link", {
      name: "Dataset Explorer → Download Dataset Report (PDF)",
    })
    .click();
  await expect(
    page.getByRole("heading", { name: "PaySim", exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Download Dataset Report (PDF)" }),
  ).toBeVisible();
});
test("expired session and invalid contract errors", async ({ page }) => {
  await open(page);
  await page.route("**/graph-explorer/neighborhood?*", (r) =>
    r.fulfill({
      status: 410,
      json: { message: "Graph session expired. Open a new lens." },
    }),
  );
  await page.getByRole("button", { name: "Apply server filters" }).click();
  await expect(page.getByRole("alert")).toContainText("Graph session expired");
  await page.route("**/graph-explorer/session?*", (r) =>
    r.fulfill({ json: { made_up: true } }),
  );
  await page.getByRole("button", { name: "Open approved graph lens" }).click();
  await expect(page.getByRole("alert")).toContainText("approved schema");
});
test("ranking deep link preserves context without reversing tokens", async ({
  page,
}) => {
  const opened: string[] = [];
  page.on("request", (r) => {
    if (r.url().includes("/session?")) opened.push(r.url());
  });
  await page.goto(
    "#/graph?dataset_id=ibm-5k&experiment_id=baseline-5k-E4-s42-m42&rank=2",
  );
  await page.getByRole("button", { name: "Open approved graph lens" }).click();
  await expect(page.locator(".graph-stage")).toBeVisible();
  expect(opened[0]).toContain("rank=2");
  expect(opened[0]).not.toContain("acct_");
});
for (const width of [360, 430, 768, 1280])
  test("responsive graph " + width, async ({ page }) => {
    await page.setViewportSize({ width, height: 1000 });
    await open(page);
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
    ).toBe(true);
    await page.getByRole("button", { name: "Relationships (2)" }).click();
    await page
      .getByRole("button", { name: "Inspect relationship 1", exact: true })
      .focus();
    await page.keyboard.press("Enter");
    await expect(
      page.getByRole("heading", { name: "Relationship detail" }),
    ).toBeVisible();
  });
test("reduced motion and process-local state", async ({ page }) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
  await open(page);
  expect(
    await page
      .locator(".graph-stage svg")
      .evaluate((e) => getComputedStyle(e).animationName),
  ).toBe("none");
  expect(
    await page.evaluate(() =>
      Object.keys(localStorage).filter((k) => /graph|session/.test(k)),
    ),
  ).toEqual([]);
});

test("session-dependent data expires in the browser", async ({ page }) => {
  await page.route("**/graph-explorer/session?*", (r) =>
    r.fulfill({ json: { ...graphSession, expires_in_seconds: 1 } }),
  );
  await open(page);
  await expect(page.getByRole("alert")).toContainText("Graph session expired", {
    timeout: 4000,
  });
  await expect(page.locator(".graph-stage")).toHaveCount(0);
});


test("worker messages, deterministic replay and lifecycle", async ({ page }) => {
  await page.addInitScript(() => {
    const Original = window.Worker;
    const state = { starts: 0, stops: 0, messages: [] as unknown[], urls: [] as string[] };
    (window as any).__workers = state;
    window.Worker = class extends Original {
      private stopped = false;
      constructor(url: string | URL, options?: WorkerOptions) { super(url, options); state.starts++; state.urls.push(String(url)); }
      postMessage(message: any) { state.messages.push(message); super.postMessage(message); }
      terminate() { if (!this.stopped) { state.stops++; this.stopped = true; } super.terminate(); }
    };
  });
  await open(page);
  const initial = await page.evaluate(() => (window as any).__workers);
  expect(initial.starts).toBe(initial.stops);
  for (const message of initial.messages) {
    expect(Object.keys(message).sort()).toEqual(["edges", "nodes"]);
    expect(message.nodes.length).toBeLessThanOrEqual(250);
    expect(message.edges.length).toBeLessThanOrEqual(500);
    expect(Object.keys(message.nodes[0]).sort()).toEqual(["in_degree", "node_ref", "out_degree"]);
  }
  await page.locator(".graph-access-list").getByRole("button").first().click();
  expect(await page.evaluate(() => (window as any).__workers.starts)).toBe(initial.starts);
  const result = await page.evaluate(async () => {
    const state = (window as any).__workers;
    const run = (input: unknown) => new Promise<any>((resolve, reject) => {
      const w = new Worker(state.urls.at(-1), { type: "module" });
      w.onmessage = e => { w.terminate(); resolve(e.data); };
      w.onerror = () => { w.terminate(); reject(new Error("Worker error")); };
      w.postMessage(input);
    });
    const input = state.messages[0];
    const a = await run(input), b = await run(input);
    const invalid = await run({ nodes: [{ node_ref: "raw-account" }], edges: [] });
    return { a: a.nodes, b: b.nodes, invalid };
  });
  expect(result.a).toEqual(result.b);
  expect(result.invalid.error).toContain("could not be displayed");
  await page.getByRole("link", { name: /Overview/ }).first().click();
  const final = await page.evaluate(() => (window as any).__workers);
  expect(final.starts).toBe(final.stops);
});

test("invalid worker output leaves accessible alternatives usable", async ({ page }) => {
  await page.addInitScript(() => {
    window.Worker = class {
      onmessage: ((event: unknown) => void) | null = null;
      onerror = null;
      postMessage() { setTimeout(() => this.onmessage?.({ data: { nodes: [], layoutMs: 0 } }), 10); }
      terminate() {}
    } as any;
  });
  await page.goto("#/graph");
  await page.getByRole("button", { name: "Open approved graph lens" }).click();
  await expect(page.getByRole("alert")).toContainText("Graph layout unavailable");
  await page.screenshot({ path: "../../../phase9/visual/layout-error.png", fullPage: true, animations: "disabled" });
  await page.locator(".graph-access-list").getByRole("button").first().click();
  await expect(page.getByRole("heading", { name: "Account detail" })).toBeVisible();
});


test("dataset changes ignore obsolete worker replies", async ({ page }) => {
  await page.addInitScript(() => {
    const state = { terminated: 0, delayedReplies: 0 };
    (window as any).__delayedWorker = state;
    window.Worker = class {
      onmessage: ((event: unknown) => void) | null = null;
      onerror = null;
      postMessage(input: any) {
        const handler = this.onmessage;
        setTimeout(() => { state.delayedReplies++; handler?.({ data: {
          nodes: input.nodes.map((n: any, i: number) => ({ id: n.node_ref, radius: 4, x: 100 + i * 40, y: 100 })), layoutMs: 1,
        } }); }, 1500);
      }
      terminate() { state.terminated++; }
    } as any;
  });
  await page.goto("#/graph");
  await page.getByRole("button", { name: "Open approved graph lens" }).click();
  await expect(page.getByText("Preparing the bounded network layout…")).toBeVisible();
  await page.screenshot({ path: "../../../phase9/visual/layout-loading.png", fullPage: true, animations: "disabled" });
  await page.getByLabel("Dataset and tier").selectOption("paysim");
  await expect.poll(() => page.evaluate(() => (window as any).__delayedWorker.delayedReplies)).toBeGreaterThan(0);
  expect(await page.evaluate(() => (window as any).__delayedWorker.terminated)).toBeGreaterThan(0);
  await expect(page.locator(".graph-stage")).toHaveCount(0);
  await expect(page.getByText("Topology unavailable:", { exact: false })).toBeVisible();
});
