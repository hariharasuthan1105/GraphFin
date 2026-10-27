import schemas from "./contract.schema.json";
type Schema = {
  const?: unknown;
  $ref?: string;
  anyOf?: Schema[];
  type?: string;
  enum?: unknown[];
  required?: string[];
  properties?: Record<string, Schema>;
  items?: Schema;
  prefixItems?: Schema[];
};
export function validate(
  value: unknown,
  schema: Schema,
  registry: Record<string, Schema> = schemas as Record<string, Schema>,
): boolean {
  if (!schema) return false;
  if ("const" in schema && value !== schema.const) return false;
  if (schema.$ref)
    return validate(value, registry[schema.$ref.split("/").pop()!], registry);
  if (schema.anyOf)
    return schema.anyOf.some((s) => validate(value, s, registry));
  if (schema.enum && !schema.enum.includes(value)) return false;
  if (schema.type === "null") return value === null;
  if (schema.type === "array")
    return (
      Array.isArray(value) &&
      value.length <= 1000 &&
      value.every((v, i) =>
        validate(v, schema.items ?? schema.prefixItems?.[i] ?? {}, registry),
      )
    );
  if (schema.type === "object")
    return (
      !!value &&
      typeof value === "object" &&
      !Array.isArray(value) &&
      (schema.required ?? []).every((k) => k in value) &&
      Object.entries(schema.properties ?? {}).every(
        ([k, s]) =>
          !(k in value) ||
          validate((value as Record<string, unknown>)[k], s, registry),
      )
    );
  if (schema.type === "number" || schema.type === "integer")
    return (
      typeof value === "number" &&
      Number.isFinite(value) &&
      (schema.type !== "integer" || Number.isInteger(value))
    );
  return !schema.type || typeof value === schema.type;
}
export class ResearchError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}
const base = (
  import.meta.env.VITE_RESEARCH_API_URL ??
  import.meta.env.VITE_API_URL ??
  (typeof window !== "undefined" && window.location.hostname.endsWith("github.io")
    ? "https://graphfin.onrender.com"
    : "")
)
  .replace(/\/$/, "")
  .replace(/\/api\/v1$/, "");

export function getAuthToken(): string | null {
  try {
    return sessionStorage.getItem("graphfin_examiner_token");
  } catch {
    return null;
  }
}

export function setAuthToken(token: string | null) {
  try {
    if (token) {
      sessionStorage.setItem("graphfin_examiner_token", token);
    } else {
      sessionStorage.removeItem("graphfin_examiner_token");
    }
  } catch {
    // Ignore storage errors in restricted contexts
  }
}

export function getAuthHeaders(): Record<string, string> {
  const token = getAuthToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

const cache = new Map<string, { value: unknown; expires: number }>();

export function backendApiUrl(path: string) {
  return base + "/api/v1" + path;
}

export async function checkBackendHealth(): Promise<{ online: boolean; waking: boolean; message: string }> {
  try {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 6000);
    const res = await fetch(backendApiUrl("/health"), {
      signal: controller.signal,
      headers: { Accept: "application/json" },
    }).finally(() => clearTimeout(timeout));
    if (res.ok) {
      return { online: true, waking: false, message: "Backend active (Render Free Tier)" };
    }
    return { online: false, waking: false, message: `HTTP ${res.status}` };
  } catch (err: any) {
    if (err?.name === "AbortError") {
      return { online: false, waking: true, message: "Backend is spinning up from sleep..." };
    }
    return { online: false, waking: false, message: "Backend offline (Local fallback active)" };
  }
}

export async function uploadTransactionsCsv(
  csvContent: string,
  filename = "transactions.csv",
  currency = "USD",
): Promise<{ dataset_id: string; summary: any; valid_transactions: number }> {
  const formData = new FormData();
  const fileBlob = new Blob([csvContent], { type: "text/csv" });
  formData.append("file", fileBlob, filename);

  const res = await fetch(
    backendApiUrl(`/transactions/upload?currency=${encodeURIComponent(currency)}`),
    {
      method: "POST",
      body: formData,
      headers: {
        Accept: "application/json",
        ...getAuthHeaders(),
      },
    },
  );
  if (!res.ok) {
    const errText = await res.text();
    throw new Error(`Upload failed (${res.status}): ${errText}`);
  }
  return await res.json();
}

export async function trainIsolationForest(
  datasetId: string,
  experimentLabel = "isolation_forest",
): Promise<any> {
  const res = await fetch(
    backendApiUrl(
      `/anomalies/${encodeURIComponent(datasetId)}/train?experiment_label=${encodeURIComponent(experimentLabel)}`,
    ),
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Accept: "application/json",
        ...getAuthHeaders(),
      },
      body: JSON.stringify({
        experiment_label: experimentLabel,
        n_estimators: 100,
        contamination: 0.05,
        random_state: 42,
        feature_groups: ["graph", "behavioral", "temporal"],
      }),
    },
  );
  if (!res.ok) {
    const errText = await res.text();
    throw new Error(`Model training failed (${res.status}): ${errText}`);
  }
  return await res.json();
}

export async function fetchUserAnomalies(
  datasetId: string,
  experimentLabel = "isolation_forest",
  limit = 250,
): Promise<{ total_users: number; anomalies_detected: number; users: Array<any> }> {
  const res = await fetch(
    backendApiUrl(
      `/anomalies/${encodeURIComponent(datasetId)}/users?experiment_label=${encodeURIComponent(experimentLabel)}&limit=${limit}`,
    ),
    {
      headers: {
        Accept: "application/json",
        ...getAuthHeaders(),
      },
    },
  );
  if (!res.ok) {
    const errText = await res.text();
    throw new Error(`Failed to fetch user anomalies (${res.status}): ${errText}`);
  }
  return await res.json();
}

export async function downloadBackendCustomReport(
  datasetId: string,
  experimentLabel = "isolation_forest",
  format: "pdf" | "docx" | "csv" = "pdf",
): Promise<void> {
  const res = await fetch(backendApiUrl("/reports/generate"), {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...getAuthHeaders(),
    },
    body: JSON.stringify({
      source: "custom",
      format,
      dataset_id: datasetId,
      experiment_label: experimentLabel,
    }),
  });
  if (!res.ok) {
    throw new Error(`Backend report download failed (${res.status})`);
  }
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `GraphFin_${datasetId}_Report.${format}`;
  a.click();
  URL.revokeObjectURL(url);
}

export function authUrl(path: string) {
  return base + "/api/auth" + path;
}

export function researchUrl(path: string) {
  return base + "/api/v1/research" + path;
}
export function graphExplorerUrl(path: string) {
  return base + "/api/v1/graph-explorer" + path;
}
export function datasetReportUrl(datasetId: string) {
  return (
    base + "/api/v1/research-reports/datasets/" + datasetId + "/report.pdf"
  );
}
const pending = new Map<
  string,
  { promise: Promise<unknown>; controller: AbortController; users: number }
>();
export function clearResearchCache() {
  cache.clear();
}
export function query(
  path: string,
  params: Record<string, string | number | undefined>,
) {
  const q = new URLSearchParams();
  Object.entries(params)
    .sort()
    .forEach(([k, v]) => {
      if (v !== undefined) q.set(k, String(v));
    });
  return path + (q.size ? "?" + q : "");
}

function getStaticFallbackUrl(path: string): string | null {
  const cleanPath = path.split("?")[0];
  let prefix = "";
  if (typeof window !== "undefined" && window.location.pathname.includes("/GraphFin")) {
    prefix = "/GraphFin";
  }

  if (cleanPath === "/overview") {
    return `${prefix}/data/research/overview.json`;
  }
  if (cleanPath === "/datasets") {
    return `${prefix}/data/research/datasets.json`;
  }
  if (cleanPath.startsWith("/datasets/")) {
    const id = cleanPath.replace("/datasets/", "");
    return `${prefix}/data/research/datasets/${id}.json`;
  }
  if (cleanPath === "/experiments" || cleanPath.startsWith("/experiments?")) {
    return `${prefix}/data/research/experiments.json`;
  }
  if (cleanPath.includes("/rankings")) {
    const id = cleanPath.replace("/experiments/", "").replace("/rankings", "");
    return `${prefix}/data/research/rankings/${id}.json`;
  }
  if (cleanPath.startsWith("/experiments/")) {
    const id = cleanPath.replace("/experiments/", "").replace(/\/.*$/, "");
    return `${prefix}/data/research/experiments/${id}.json`;
  }
  if (cleanPath === "/model-seeds" || cleanPath.startsWith("/model-seeds?")) {
    return `${prefix}/data/research/model-seeds.json`;
  }
  if (cleanPath === "/reproducibility") {
    return `${prefix}/data/research/reproducibility.json`;
  }
  if (cleanPath === "/limitations") {
    return `${prefix}/data/research/limitations.json`;
  }
  if (cleanPath === "/diagnostics" || cleanPath.startsWith("/diagnostics?")) {
    return `${prefix}/data/research/diagnostics.json`;
  }
  if (cleanPath.startsWith("/diagnostics/")) {
    const id = cleanPath.replace("/diagnostics/", "");
    return `${prefix}/data/research/diagnostics/${id}.json`;
  }
  return null;
}

function filterStaticPage(path: string, raw: unknown): unknown {
  if (!path.includes("?") || !raw || typeof raw !== "object") return raw;
  const params = new URLSearchParams(path.split("?")[1]);
  const page = raw as {
    items?: Record<string, unknown>[];
    total?: number;
    page?: number;
    page_size?: number;
  };
  if (!Array.isArray(page.items)) return raw;

  let items = [...page.items];
  const datasetId = params.get("dataset_id");
  const tier = params.get("tier");
  const method = params.get("method");
  const version = params.get("version");
  const splitSeed = params.get("split_seed");
  const modelSeed = params.get("model_seed");

  if (datasetId) items = items.filter((x) => x.dataset_id === datasetId);
  if (tier) items = items.filter((x) => x.tier === tier);
  if (method) items = items.filter((x) => x.method === method);
  if (version) items = items.filter((x) => x.version === version);
  if (splitSeed != null)
    items = items.filter((x) => String(x.split_seed) === splitSeed);
  if (modelSeed != null)
    items = items.filter((x) => String(x.model_seed) === modelSeed);

  const pageNum = parseInt(params.get("page_number") || "1", 10);
  const pageSize = parseInt(params.get("page_size") || "25", 10);
  const total = items.length;
  const pagedItems = items.slice((pageNum - 1) * pageSize, pageNum * pageSize);

  return {
    ...page,
    items: pagedItems,
    total,
    page: pageNum,
    page_size: pageSize,
  };
}

export function getResearch<T>(
  path: string,
  schema: keyof typeof schemas,
  signal: AbortSignal,
): Promise<T> {
  if (!/^\/[a-z0-9/?=&_.%-]+$/i.test(path) || path.includes(".."))
    return Promise.reject(new ResearchError(422, "Invalid research query."));
  const key = `${schema}:${path}`;
  const hit = cache.get(key);
  if (hit && hit.expires > Date.now()) return Promise.resolve(hit.value as T);
  let entry = pending.get(key);
  if (!entry) {
    const controller = new AbortController();
    const promise = (async () => {
      const targetSchema = (schemas as Record<string, Schema>)[schema];
      const staticUrl = getStaticFallbackUrl(path);

      // Attempt live fetch first with a 5-second timeout (to handle sleeping Render service)
      try {
        const liveController = new AbortController();
        const timeoutId = setTimeout(() => liveController.abort(), 5000);

        const onParentAbort = () => liveController.abort();
        controller.signal.addEventListener("abort", onParentAbort);

        const r = await fetch(researchUrl(path), {
          method: "GET",
          signal: liveController.signal,
          credentials: "same-origin",
          headers: {
            Accept: "application/json",
            ...getAuthHeaders(),
          },
        }).finally(() => {
          clearTimeout(timeoutId);
          controller.signal.removeEventListener("abort", onParentAbort);
        });

        if (r.ok) {
          const value: unknown = await r.json();
          if (validate(value, targetSchema)) {
            const obj = value as { status?: string };
            if (obj.status !== "unavailable") {
              if (!path.includes("rankings") && !path.includes("diagnostics")) {
                cache.set(key, { value, expires: Date.now() + 60_000 });
                if (cache.size > 30) cache.delete(cache.keys().next().value!);
              }
              return value as T;
            }
          }
        }
      } catch (err) {
        if (controller.signal.aborted) {
          throw err;
        }
        // Live backend timed out or unreachable: fall through to static verified evidence
      }

      // Fallback: load verified aggregate research evidence
      if (staticUrl) {
        try {
          const res = await fetch(staticUrl, {
            signal: controller.signal,
            headers: { Accept: "application/json" },
          });
          if (res.ok) {
            const rawJson: unknown = await res.json();
            const processed = filterStaticPage(path, rawJson);
            if (validate(processed, targetSchema)) {
              if (!path.includes("rankings") && !path.includes("diagnostics")) {
                cache.set(key, { value: processed, expires: Date.now() + 60_000 });
                if (cache.size > 30) cache.delete(cache.keys().next().value!);
              }
              return processed as T;
            }
          }
        } catch (staticErr) {
          if (controller.signal.aborted) throw staticErr;
        }
      }

      throw new ResearchError(
        503,
        "Approved research evidence is unavailable.",
      );
    })().finally(() => {
      if (pending.get(key)?.controller === controller) pending.delete(key);
    });

    entry = { promise, controller, users: 0 };
    pending.set(key, entry);
  }
  entry.users++;
  const active = entry;
  return new Promise<T>((resolve, reject) => {
    let settled = false;
    const finish = () => {
      if (settled) return false;
      settled = true;
      signal.removeEventListener("abort", abort);
      active.users--;
      return true;
    };
    const abort = () => {
      if (finish()) {
        reject(new DOMException("Cancelled", "AbortError"));
        setTimeout(() => {
          if (active.users === 0 && pending.get(key) === active) {
            pending.delete(key);
            active.controller.abort();
          }
        }, 0);
      }
    };
    signal.addEventListener("abort", abort, { once: true });
    if (signal.aborted) {
      abort();
      return;
    }
    active.promise.then(
      (v) => {
        if (finish()) resolve(v as T);
      },
      (e) => {
        if (finish()) reject(e);
      },
    );
  });
}
