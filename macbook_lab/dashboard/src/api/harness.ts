import { fetchJson } from "./client";

export interface ScenarioList {
  scenarios: string[];
}

export interface TraceList {
  count: number;
  traces: Array<{
    scenario_id: string;
    name: string;
    size_bytes: number;
    example?: boolean;
  }>;
}

export interface TraceRecords {
  scenario_id: string;
  source: string;
  count: number;
  records: Record<string, unknown>[];
}

export interface HarnessRunEvent {
  eventId?: string;
  eventType?: string;
  event?: {
    correlatedEventId?: string;
    remediation?: Record<string, unknown>;
  };
}

export interface BenchSummary {
  results?: unknown[];
  summary?: {
    scenario_count?: number;
    scenarios_with_companion_intent?: number;
    total_duration_seconds?: number;
    per_scenario?: Array<{
      scenario_id: string;
      fault_id: string;
      action_type?: string;
      target_layer?: string;
      blast_cells?: number;
      companion_intent_attached?: boolean;
      duration_seconds?: number;
    }>;
  };
}

export const harnessApi = {
  scenarios: () => fetchJson<ScenarioList>("/api/harness/scenarios"),
  traces: () => fetchJson<TraceList>("/api/harness/traces"),
  trace: (scenarioId: string, limit = 200) =>
    fetchJson<TraceRecords>(`/api/harness/traces/${scenarioId}?limit=${limit}`),
  benchAll: () => fetchJson<BenchSummary>("/api/harness/bench/all"),
  runScenario: (scenarioId: string) =>
    fetchJson<HarnessRunEvent>(`/api/harness/run/${scenarioId}`),
  health: () =>
    fetchJson<{ service: string; scenarios_dir?: string }>(
      "/api/harness/health",
    ),
};
