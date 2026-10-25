import { useEffect, useState } from "react";
import { getResearch, clearResearchCache } from "./client";
import schemas from "./contract.schema.json";

export const TITLE =
  "Machine Learning Enhanced Graph-Based Anomaly Detection for Financial Transactions";
export const fmt = (value: number | null | undefined, digits = 4) =>
  value == null
    ? "Unavailable"
    : value.toLocaleString("en-US", { maximumFractionDigits: digits });

export function useResearch<T>(path: string, schema: keyof typeof schemas) {
  const [retryCount, setRetry] = useState(0);
  const key = `${schema}:${path}:${retryCount}`;
  const [state, setState] = useState<{ key: string; data?: T; error?: Error }>({
    key,
  });
  useEffect(() => {
    const controller = new AbortController();
    getResearch<T>(path, schema, controller.signal).then(
      (data) => setState({ key, data }),
      (error) => {
        if (!controller.signal.aborted) setState({ key, error });
      },
    );
    return () => controller.abort();
  }, [path, schema, key]);
  // Derive loading from request identity; never render a previous query's data
  // and avoid a redundant synchronous setState in the effect.
  return {
    data: state.key === key ? state.data : undefined,
    error: state.key === key ? state.error : undefined,
    retry: () => {
      clearResearchCache();
      setRetry((value) => value + 1);
    },
  };
}
