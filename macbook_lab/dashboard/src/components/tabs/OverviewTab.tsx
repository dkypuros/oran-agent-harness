import { useCallback } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { harnessApi } from "@/api/harness";
import { usePolling } from "@/hooks/usePolling";

export function OverviewTab() {
  const bench = usePolling(useCallback(() => harnessApi.benchAll(), []), 5000);
  const traces = usePolling(useCallback(() => harnessApi.traces(), []), 5000);

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle>Overview</CardTitle>
            <CardDescription>
              Bench summary across all 4 scenarios, plus the trace files currently on disk.
            </CardDescription>
          </div>
          <Button onClick={() => { bench.refresh(); traces.refresh(); }}>Refresh</Button>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {bench.error && <div className="text-xs text-red-700">bench: {bench.error}</div>}
        {bench.loading && !bench.data && <div className="text-xs text-muted-foreground">loading bench...</div>}
        {bench.data?.summary && (
          <div>
            <div className="mb-2 flex flex-wrap gap-2 text-xs">
              <Badge variant="muted">scenarios: {bench.data.summary.scenario_count ?? 0}</Badge>
              <Badge variant="success">with companion_intent: {bench.data.summary.scenarios_with_companion_intent ?? 0}</Badge>
              <Badge variant="muted">duration: {bench.data.summary.total_duration_seconds ?? 0}s</Badge>
            </div>
            <table className="w-full text-xs border-collapse">
              <thead>
                <tr className="border-b text-left">
                  <th className="py-1 pr-2">Scenario</th>
                  <th className="py-1 pr-2">Action</th>
                  <th className="py-1 pr-2">Layer</th>
                  <th className="py-1 pr-2">Cells</th>
                  <th className="py-1 pr-2">SMO intent</th>
                  <th className="py-1">Duration</th>
                </tr>
              </thead>
              <tbody>
                {bench.data.summary.per_scenario?.map((s) => (
                  <tr key={s.scenario_id} className="border-b">
                    <td className="py-1 pr-2 font-mono">{s.scenario_id}</td>
                    <td className="py-1 pr-2">{s.action_type ?? "-"}</td>
                    <td className="py-1 pr-2">{s.target_layer ?? "-"}</td>
                    <td className="py-1 pr-2">{s.blast_cells ?? "-"}</td>
                    <td className="py-1 pr-2">
                      <Badge variant={s.companion_intent_attached ? "success" : "muted"}>
                        {s.companion_intent_attached ? "yes" : "no"}
                      </Badge>
                    </td>
                    <td className="py-1">{s.duration_seconds ?? "-"}s</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        <div>
          <h4 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-1">Trace files</h4>
          {traces.data?.traces?.length ? (
            <ul className="text-xs space-y-0.5">
              {traces.data.traces.map((t) => (
                <li key={t.name} className="font-mono">
                  {t.name} <span className="text-muted-foreground">({t.size_bytes} bytes)</span>
                  {t.example && <Badge variant="muted" className="ml-2">example</Badge>}
                </li>
              ))}
            </ul>
          ) : (
            <div className="text-xs text-muted-foreground italic">no trace files yet; run the bench (Overview refresh triggers one)</div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
