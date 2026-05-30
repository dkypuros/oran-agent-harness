import { useCallback, useEffect, useState } from "react";

export interface PollResult<T> {
  data: T | null;
  error: string | null;
  loading: boolean;
  refresh: () => void;
  lastUpdate: Date | null;
}

export function usePolling<T>(fetcher: () => Promise<T>, intervalMs = 3000): PollResult<T> {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [lastUpdate, setLastUpdate] = useState<Date | null>(null);
  const [nonce, setNonce] = useState(0);

  const refresh = useCallback(() => setNonce((n) => n + 1), []);

  useEffect(() => {
    let alive = true;
    let timer: ReturnType<typeof setTimeout> | null = null;
    const tick = async () => {
      try {
        const next = await fetcher();
        if (!alive) return;
        setData(next);
        setError(null);
        setLastUpdate(new Date());
      } catch (e) {
        if (!alive) return;
        setError(e instanceof Error ? e.message : String(e));
      } finally {
        if (alive) setLoading(false);
      }
      if (alive) timer = setTimeout(tick, intervalMs);
    };
    tick();
    return () => {
      alive = false;
      if (timer) clearTimeout(timer);
    };
  }, [fetcher, intervalMs, nonce]);

  return { data, error, loading, refresh, lastUpdate };
}
