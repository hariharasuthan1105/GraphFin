import { test, expect } from "@playwright/test";
import { response } from "./fixtures";
test.beforeEach(async ({ page }) => {
  await page.route("**/api/v1/research/**", (r) =>
    r.fulfill({ json: response(new URL(r.request().url())) }),
  );
});
test("downloads the selected dataset as a PDF with GET", async ({ page }) => {
  const urls: string[] = [];
  await page.route("**/report.pdf", (r) => {
    urls.push(r.request().url());
    expect(r.request().method()).toBe("GET");
    return r.fulfill({
      contentType: "application/pdf",
      body: "%PDF-1.4\nsynthetic test-only download",
    });
  });
  await page.goto("#/datasets");
  await page.getByRole("button", { name: "PaySim", exact: true }).click();
  const pending = page.waitForEvent("download");
  await page
    .getByRole("button", { name: "Download Dataset Report (PDF)" })
    .click();
  const download = await pending;
  expect(download.suggestedFilename()).toBe(
    "GraphFin_paysim_dataset_report.pdf",
  );
  expect(urls).toHaveLength(1);
  expect(urls[0]).toContain("/datasets/paysim/report.pdf");
  await expect(page.locator(".report-download [role=status]")).toContainText(
    "Dataset report downloaded.",
  );
});
test("failed and invalid exports do not start downloads", async ({ page }) => {
  await page.route("**/report.pdf", (r) =>
    r.fulfill({
      status: 503,
      json: { message: "Pinned evidence unavailable." },
    }),
  );
  await page.goto("#/datasets");
  await page
    .getByRole("button", { name: "Download Dataset Report (PDF)" })
    .click();
  await expect(page.getByRole("alert")).toContainText(
    "Pinned evidence unavailable.",
  );
  await page.route("**/report.pdf", (r) =>
    r.fulfill({ contentType: "text/html", body: "not a report" }),
  );
  await page
    .getByRole("button", { name: "Download Dataset Report (PDF)" })
    .click();
  await expect(page.getByRole("alert")).toContainText("did not return a PDF");
});
test("loading prevents duplicate report requests", async ({ page }) => {
  let count = 0;
  await page.route("**/report.pdf", async (r) => {
    count++;
    await new Promise((x) => setTimeout(x, 700));
    await r.fulfill({
      contentType: "application/pdf",
      body: "%PDF-1.4\nfixture",
    });
  });
  await page.goto("#/datasets");
  await page
    .getByRole("button", { name: "Download Dataset Report (PDF)" })
    .click();
  await expect(
    page.getByRole("button", { name: "Preparing report…" }),
  ).toBeDisabled();
  await expect(page.locator(".report-download [role=status]")).toContainText("downloaded");
  expect(count).toBe(1);
});
