// Thin fetch wrapper used by every per-service API helper.
// Each helper calls fetchJson against a /api/<service>/<path> URL; Vite proxies
// the request to the right docker-compose container (see vite.config.ts).

export async function fetchJson<T = unknown>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(url, { cache: "no-store", ...init });
  if (!res.ok) {
    throw new Error(`${url} returned ${res.status}`);
  }
  return (await res.json()) as T;
}
