import { test, expect } from "@playwright/test";
import { response, page as envelope, experiment } from "./fixtures";
test.beforeEach(async ({ page }) => {
  await page.route("**/api/v1/research/**", (route) =>
    route.fulfill({ json: response(new URL(route.request().url())) }),
  );
});
const headings = {
  overview: "Financial Network Intelligence",
  datasets: "Dataset explorer",
  experiments: "Experiment registry",
  comparison: "Model comparison",
  seeds: "Seed analysis",
  reproducibility: "Reproducibility",
  diagnostics: "CREST diagnostics",
  limitations: "Research limitations",
};
for (const [route, title] of Object.entries(headings))
  test("renders " + route, async ({ page }) => {
    await page.goto("#/" + route);
    await expect(
      page.getByRole("heading", { name: title, exact: true }),
    ).toBeVisible();
    await expect(page.getByText("Reading research artifacts…")).toHaveCount(0);
    await expect(page.getByText("Evidence could not be loaded.")).toHaveCount(
      0,
    );
  });
test("overview uses returned evidence and preserves title", async ({
  page,
}) => {
  await page.goto("#/overview");
  await expect(page.getByText("84 method evaluations")).toBeVisible();
  await expect(
    page
      .getByText(
        "Machine Learning Enhanced Graph-Based Anomaly Detection for Financial Transactions",
        { exact: true },
      )
      .first(),
  ).toBeVisible();
});
test("PaySim identities and missing values", async ({ page }) => {
  await page.goto("#/datasets");
  await page.getByRole("button", { name: "PaySim", exact: true }).click();
  await expect(page.getByText("paysim-research-774")).toBeVisible();
  await expect(page.getByText("paysim-application-2606")).toBeVisible();
  await expect(
    page.getByText("Unresolved label conflict:", { exact: false }),
  ).toBeVisible();
  await expect(
    page.getByRole("cell", { name: "Unavailable", exact: true }).first(),
  ).toBeVisible();
});
test("comparison filters and table alternative", async ({ page }) => {
  await page.goto("#/comparison");
  await page
    .getByRole("combobox", { name: "Split seed", exact: true })
    .selectOption("7");
  await expect(
    page.getByRole("cell", { name: "baseline-5k-E4-s7-m42" }),
  ).toBeVisible();
  await expect(
    page.getByText("E6_BASE is calibration-only", { exact: false }),
  ).toBeVisible();
  await expect(page.getByRole("table")).toHaveCount(2);
});
test("split and model seeds stay distinct", async ({ page }) => {
  await page.goto("#/seeds");
  await expect(
    page.getByText("SD is not a confidence interval.", { exact: false }),
  ).toBeVisible();
  await page.getByLabel("Evidence axis").selectOption("model");
  await expect(
    page.getByRole("heading", { name: "Model-seed sensitivity" }),
  ).toBeVisible();
  await expect(
    page.getByRole("cell", { name: "101", exact: true }),
  ).toBeVisible();
  await expect(
    page.getByText("Three model seeds do not establish general robustness.", {
      exact: false,
    }),
  ).toBeVisible();
});
test("experiment details provenance and bounded rankings", async ({ page }) => {
  const urls: string[] = [];
  page.on("request", (r) => {
    if (r.url().includes("rankings")) urls.push(r.url());
  });
  await page.goto("#/experiments");
  await page
    .getByRole("button", { name: "baseline-5k-E4-s42-m42", exact: true })
    .click();
  await expect(page.getByText("in_degree")).toBeVisible();
  await page.getByRole("button", { name: "rankings", exact: true }).click();
  await expect(page.getByRole("cell", { name: "acct_fixture" })).toBeVisible();
  await page.getByRole("button", { name: "Next →" }).last().click();
  await expect
    .poll(() =>
      urls.some(
        (x) => x.includes("page_number=2") && x.includes("page_size=25"),
      ),
    )
    .toBeTruthy();
  await expect(
    page.getByText("Anomaly scores are not fraud probabilities.", {
      exact: false,
    }),
  ).toBeVisible();
});
test("diagnostic caveats and details", async ({ page }) => {
  await page.goto("#/diagnostics");
  await expect(
    page.getByText("Experimental model-sensitivity diagnostic", {
      exact: true,
    }),
  ).toBeVisible();
  await page.getByRole("button", { name: "crest-000" }).click();
  await expect(
    page.getByText("Stability and runtime are not exposed", { exact: false }),
  ).toBeVisible();
});
test("empty diagnostics are explicit", async ({ page }) => {
  await page.route("**/api/v1/research/diagnostics?*", (r) =>
    r.fulfill({ json: { ...envelope([]), status: "unavailable" } }),
  );
  await page.goto("#/diagnostics");
  await expect(
    page.getByText("No matching records.", { exact: false }),
  ).toBeVisible();
});
test("incomplete experiments never acquire invented metrics", async ({
  page,
}) => {
  await page.route(/\/api\/v1\/research\/experiments/, (r) =>
    r.fulfill({
      json: new URL(r.request().url()).pathname.endsWith("/experiments")
        ? envelope([{ ...experiment, status: "incomplete", metrics: null }])
        : { ...experiment, status: "incomplete", metrics: null },
    }),
  );
  await page.goto("#/experiments");
  await page.getByRole("button", { name: experiment.experiment_id }).click();
  await expect(
    page.getByText("Historical or incomplete record.", { exact: false }),
  ).toBeVisible();
  await expect(
    page.getByRole("cell", { name: "Unavailable", exact: true }),
  ).toBeVisible();
});
for (const status of [409, 422, 503])
  test("scientific/technical error " + status, async ({ page }) => {
    await page.route("**/api/v1/research/comparisons?*", (r) =>
      r.fulfill({
        status,
        json: { message: "Fixture request unavailable " + status },
      }),
    );
    await page.goto("#/comparison");
    await expect(page.getByRole("alert")).toContainText(
      "Fixture request unavailable " + status,
    );
    await expect(
      page.getByRole("button", { name: "Retry request ↗" }),
    ).toBeVisible();
  });
test("invalid API shape is rejected", async ({ page }) => {
  await page.route("**/api/v1/research/overview", (r) =>
    r.fulfill({ json: { made_up_metric: 999 } }),
  );
  await page.goto("#/overview");
  await expect(page.getByRole("alert")).toContainText("does not match");
});
test("network failure and retry", async ({ page }) => {
  await page.route("**/api/v1/research/overview", (r) => r.abort());
  await page.goto("#/overview");
  await expect(page.getByRole("alert")).toBeVisible();
  await page.screenshot({
    path: "../../../work/phase8/visual-production/error-mocked.png",
    animations: "disabled",
  });
  await page.unroute("**/api/v1/research/overview");
  await page.getByRole("button", { name: "Retry request ↗" }).click();
  await expect(page.getByText("84 method evaluations")).toBeVisible();
});
test("genuine slow loading", async ({ page }) => {
  await page.route("**/api/v1/research/overview", async (r) => {
    await new Promise((x) => setTimeout(x, 4000));
    await r.fulfill({ json: response(new URL(r.request().url())) });
  });
  await page.goto("#/overview");
  await expect(page.getByRole("status")).toContainText("Still waiting", {
    timeout: 6000,
  });
  await page.screenshot({
    path: "../../../work/phase8/visual-production/loading-mocked.png",
    animations: "disabled",
  });
  await expect(page.getByText("84 method evaluations")).toBeVisible();
});
test("only GET and immutable cache reuse", async ({ page }) => {
  const requests: string[] = [];
  page.on("request", (r) => {
    if (r.url().includes("/api/")) {
      expect(r.method()).toBe("GET");
      requests.push(r.url());
    }
  });
  await page.goto("#/overview");
  await expect(page.getByText("84 method evaluations")).toBeVisible();
  const before = requests.length;
  await page.getByRole("link", { name: /Research Limitations/ }).click();
  await expect(page.getByText("Synthetic limitation")).toBeVisible();
  await page.getByRole("link", { name: /01$/ }).click();
  await expect(page.getByText("84 method evaluations")).toBeVisible();
  expect(requests.length).toBe(before + 1);
});
for (const width of [390, 768, 1280, 1920])
  test("responsive layout " + width, async ({ page }) => {
    await page.setViewportSize({ width, height: 1000 });
    await page.goto("#/overview");
    await expect(page.getByText("84 method evaluations")).toBeVisible();
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
    ).toBe(true);
    if (width < 768) {
      await page.getByRole("button", { name: "Toggle navigation" }).click();
      await page.getByRole("link", { name: /Datasets/ }).click();
      await expect(
        page.getByRole("heading", { name: "Dataset explorer" }),
      ).toBeVisible();
    }
  });
test("keyboard skip and finite pixel animation", async ({ page }) => {
  await page.goto("#/overview");
  await page.keyboard.press("Tab");
  await expect(page.getByText("Skip to research content")).toBeFocused();
  await page.keyboard.press("Enter");
  await expect(page.locator("main")).toBeFocused();
  await page.waitForTimeout(2200);
  expect(
    await page
      .locator(".brand")
      .evaluate(
        (e) =>
          e
            .getAnimations({ subtree: true })
            .filter((a) => a.playState === "running").length,
      ),
  ).toBe(0);
});
test("reduced motion and fonts", async ({ page }) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.goto("#/overview");
  await page.evaluate(() => document.fonts.ready);
  expect(
    await page
      .locator(".brand span")
      .evaluate((e) => getComputedStyle(e).animationName),
  ).toBe("none");
  expect(
    await page.evaluate(() => document.fonts.check('700 30px "Pixelify Sans"')),
  ).toBe(true);
});
test("font failure preserves visible content", async ({ page }) => {
  await page.route("**/*.woff2", (r) => r.abort());
  await page.goto("#/overview");
  await expect(
    page.getByRole("heading", { name: "Financial Network Intelligence" }),
  ).toBeVisible();
  expect(
    await page
      .locator(".brand")
      .evaluate((e) => e.getBoundingClientRect().width),
  ).toBeGreaterThan(100);
});
test("null metrics and empty rankings remain unavailable", async ({ page }) => {
  await page.route(/\/api\/v1\/research\/experiments/, (r) => {
    const u = new URL(r.request().url());
    return r.fulfill({
      json: u.pathname.endsWith("/rankings")
        ? envelope([])
        : u.pathname.endsWith("/experiments")
          ? envelope([
              {
                ...experiment,
                metrics: { ...experiment.metrics, average_precision: null },
              },
            ])
          : experiment,
    });
  });
  await page.goto("#/experiments");
  await expect(
    page.getByRole("cell", { name: "Unavailable", exact: true }),
  ).toBeVisible();
  await page.getByRole("button", { name: experiment.experiment_id }).click();
  await page.getByRole("button", { name: "rankings", exact: true }).click();
  await expect(
    page.getByText("No matching records.", { exact: false }),
  ).toBeVisible();
});
test("sample standard deviation is numerically correct", async ({ page }) => {
  await page.route("**/api/v1/research/experiments?*", (r) =>
    r.fulfill({
      json: envelope(
        [0.1, 0.2, 0.3, 0.4, 0.5, 0.6].map((v, i) => ({
          ...experiment,
          split_seed: i,
          metrics: { ...experiment.metrics, average_precision: v },
        })),
      ),
    }),
  );
  await page.goto("#/seeds");
  await expect(
    page.getByText("mean 0.35 · sample SD 0.18708287", { exact: false }),
  ).toBeVisible();
});
test("missing saved diagnostic returns an honest error", async ({ page }) => {
  await page.route("**/api/v1/research/diagnostics/crest-000", (r) =>
    r.fulfill({
      status: 404,
      json: { message: "Saved diagnostic unavailable." },
    }),
  );
  await page.goto("#/diagnostics");
  await page.getByRole("button", { name: "crest-000" }).click();
  await expect(page.getByRole("alert")).toContainText(
    "Saved diagnostic unavailable.",
  );
});
test("mobile pages and scientific tables contain overflow", async ({
  page,
}) => {
  await page.setViewportSize({ width: 360, height: 900 });
  for (const route of Object.keys(headings)) {
    await page.goto("#/" + route);
    await expect(
      page.getByRole("heading", {
        name: headings[route as keyof typeof headings],
        exact: true,
      }),
    ).toBeVisible();
    await expect(page.getByText("Reading research artifacts…")).toHaveCount(0);
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
    ).toBe(true);
  }
});
test("legacy workspace navigation remains available", async ({ page }) => {
  await page.route("**/api/v1/**", (r) =>
    r.fulfill({
      status: 503,
      json: { message: "Synthetic offline legacy API" },
    }),
  );
  await page.goto("#/workspace");
  await expect(
    page.getByRole("button", { name: "Tax Analytics", exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Graph", exact: true }),
  ).toBeVisible();
  await page
    .getByRole("link", { name: "← Read-only research terminal" })
    .click();
  await expect(
    page.getByRole("heading", { name: "Financial Network Intelligence" }),
  ).toBeVisible();
});
