import { fetchJson } from "./client";

export interface RedfishHistory {
  count: number;
  tasks: Array<{
    task_uri?: string;
    task_state?: string;
    percent_complete?: number;
    message?: string;
  }>;
}

export const redfishApi = {
  history: (limit = 50) => fetchJson<RedfishHistory>(`/api/redfish/history?limit=${limit}`),
  state: () => fetchJson<{ scenarios_tracked: string[]; latest_per_scenario: Record<string, unknown> }>("/api/redfish/state"),
};
