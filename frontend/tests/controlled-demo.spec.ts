import { test, expect } from "@playwright/test";

test("actual controlled API excludes legacy access and unapproved browser origins", async ({ request }) => {
  const health = await request.get("/api/v1/health");
  expect(health.status()).toBe(200);
  expect((await health.json()).mode).toBe("controlled-research-demo");
  for (const path of ["/api/v1/graph/paysim/summary", "/api/v1/datasets", "/api/v1/anomalies/paysim", "/docs", "/api/v1/openapi.json"]) {
    const response = await request.get(path === "/docs" ? "http://127.0.0.1:8000/docs" : path);
    expect(response.status()).toBe(404);
    expect(response.headers()["cache-control"]).toBe("private, no-store");
  }
  const train = await request.post("/api/v1/anomalies/paysim/train", { data: {} });
  expect(train.status()).toBe(405);
  expect((await train.json()).error).toBe("DEMO_READ_ONLY");
  const otherOrigin = await request.get("/api/v1/research/overview", {
    headers: { Origin: "https://untrusted.invalid" },
  });
  expect(otherOrigin.status()).toBe(403);
  expect((await otherOrigin.json()).error).toBe("DEMO_ORIGIN_DENIED");
});
