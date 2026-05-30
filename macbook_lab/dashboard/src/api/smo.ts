import { fetchJson } from "./client";

export interface SmoHistory {
  count: number;
  intents: Array<{
    intent_id?: string;
    intent_type?: string;
    affected_resources?: string[];
    window_start?: string;
    window_end?: string;
    service_impact_hint?: string;
    expected_handover_count?: number;
  }>;
}

export const smoApi = {
  history: (limit = 50) => fetchJson<SmoHistory>(`/api/smo/history?limit=${limit}`),
  state: () => fetchJson<{ emitted_count: number; latest: unknown }>("/api/smo/state"),
};
