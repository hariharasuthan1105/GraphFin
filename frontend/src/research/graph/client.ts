import { useEffect, useState } from "react";
import { graphExplorerUrl, ResearchError, validate } from "../client";
import schemas from "./contract.schema.json";
import type { GraphCatalog } from "./contract";

export async function graphRequest<T>(
  path: string,
  schema: keyof typeof schemas,
  signal: AbortSignal,
  session?: string,
): Promise<T> {
  const response = await fetch(graphExplorerUrl(path), {
    method: "GET",
    cache: "no-store",
    signal,
    headers: {
      Accept: "application/json",
      ...(session ? { "X-Graph-Session": session } : {}),
    },
  });
  if (!response.ok) {
    const value = await response.json().catch(() => null);
    throw new ResearchError(
      response.status,
      typeof value?.message === "string"
        ? value.message
        : `Graph evidence unavailable (${response.status}).`,
    );
  }
  const value: unknown = await response.json();
  if (!validate(value, schemas[schema], schemas))
    throw new ResearchError(
      503,
      "Graph response did not match its approved schema.",
    );
  return value as T;
}

export function useGraphCatalog() {
  const [state, setState] = useState<{ data?: GraphCatalog; error?: Error }>(
    {},
  );
  useEffect(() => {
    const controller = new AbortController();
    graphRequest<GraphCatalog>(
      "/catalog",
      "GraphCatalog",
      controller.signal,
    ).then(
      (data) => setState({ data }),
      (error) => {
        if (!controller.signal.aborted) setState({ error });
      },
    );
    return () => controller.abort();
  }, []);
  return state;
}
