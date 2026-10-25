import schemas from "./contract.schema.json";
type Schema = {
  $ref?: string;
  anyOf?: Schema[];
  type?: string;
  enum?: unknown[];
  required?: string[];
  properties?: Record<string, Schema>;
  items?: Schema;
  prefixItems?: Schema[];
};
export function validate(value: unknown, schema: Schema): boolean {
  if (schema.$ref)
    return validate(
      value,
      (schemas as Record<string, Schema>)[schema.$ref.split("/").pop()!],
    );
  if (schema.anyOf) return schema.anyOf.some((s) => validate(value, s));
  if (schema.enum && !schema.enum.includes(value)) return false;
  if (schema.type === "null") return value === null;
  if (schema.type === "array")
    return (
      Array.isArray(value) &&
      value.length <= 1000 &&
      value.every((v, i) =>
        validate(v, schema.items ?? schema.prefixItems?.[i] ?? {}),
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
          !(k in value) || validate((value as Record<string, unknown>)[k], s),
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
  ""
)
  .replace(/\/$/, "")
  .replace(/\/api\/v1$/, "");
const cache = new Map<string, { value: unknown; expires: number }>();
export function researchUrl(path: string) {
  return base + "/api/v1/research" + path;
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
    const promise = fetch(researchUrl(path), {
      method: "GET",
      signal: controller.signal,
      headers: { Accept: "application/json" },
    })
      .then(async (r) => {
        if (!r.ok) {
          const error = await r.json().catch(() => null);
          throw new ResearchError(
            r.status,
            typeof error?.message === "string"
              ? error.message
              : `Research request unavailable (${r.status}).`,
          );
        }
        const value: unknown = await r.json();
        if (!validate(value, (schemas as Record<string, Schema>)[schema]))
          throw new ResearchError(
            503,
            "Research response does not match the verified API contract.",
          );
        // Account tokens are process-local: never retain ranking/diagnostic responses between visits.
        if (!path.includes("rankings") && !path.includes("diagnostics")) {
          cache.set(key, { value, expires: Date.now() + 60_000 });
          if (cache.size > 30) cache.delete(cache.keys().next().value!);
        }
        return value;
      })
      .finally(() => {
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
