// Covers both network headers and response-body download. Never retry a training POST automatically.
export async function boundedJsonFetch(url: string, init: RequestInit = {}, timeoutMs = 30000): Promise<any> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const response = await fetch(url, {...init, signal: controller.signal});
    if (!response.ok) throw new Error(`Backend request failed (${response.status}). Client-side graph analysis remains available.`);
    return await response.json();
  } finally { clearTimeout(timer); }
}
