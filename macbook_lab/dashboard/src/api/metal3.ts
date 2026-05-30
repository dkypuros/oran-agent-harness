import { fetchJson } from "./client";

export interface Metal3History {
  count: number;
  phases: Array<{
    component?: string;
    phase?: string;
    detail?: string;
    bytes?: number;
    scenario_id?: string;
  }>;
}

export const metal3Api = {
  history: (limit = 50) => fetchJson<Metal3History>(`/api/metal3/history?limit=${limit}`),
  state: () => fetchJson<{ scenarios_tracked: string[]; latest_per_scenario: Record<string, unknown> }>("/api/metal3/state"),
};
