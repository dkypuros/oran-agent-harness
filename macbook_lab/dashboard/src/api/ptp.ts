import { fetchJson } from "./client";

export interface PtpHistory {
  count: number;
  events: Array<{
    source?: string;
    type?: string;
    time?: string;
    data?: { values?: unknown[]; verdict?: string };
  }>;
}

export const ptpApi = {
  history: (limit = 50) => fetchJson<PtpHistory>(`/api/ptp/history?limit=${limit}`),
  state: () => fetchJson<{ published_count: number; latest: unknown }>("/api/ptp/state"),
};
