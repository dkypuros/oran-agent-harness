import { useCallback, useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { harnessApi } from "@/api/harness";
import { usePolling } from "@/hooks/usePolling";

const SCENARIOS = [
  "A_fw_lldp_agent",
  "A_prime_ice_driver",
  "D_phc_drift_hw_only",
  "E_nic_firmware_update",
];

export function PtpLogsTab() {
  const [scenario, setScenario] = useState("E_nic_firmware_update");
  const { data, error, loading, refresh, lastUpdate } = usePolling(
    useCallback(() => harnessApi.trace(scenario, 200), [scenario]),
    3000,
  );
  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between flex-wrap gap-2">
          <div>
            <CardTitle>PTP sync logs (shared trace JSONL)</CardTitle>
            <CardDescription>
              Per-stage records the harness writes to 5G_O-RAN_SIM/shared_trace/. Switch scenarios with the buttons.
            </CardDescription>
          </div>
          <div className="flex items-center gap-2">
            {lastUpdate && (
              <span className="text-xs text-muted-foreground">updated {lastUpdate.toLocaleTimeString()}</span>
            )}
            <Button onClick={refresh}>Refresh</Button>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <div className="mb-3 flex flex-wrap gap-2">
          {SCENARIOS.map((s) => (
            <Button
              key={s}
              onClick={() => setScenario(s)}
              className={s === scenario ? "bg-primary text-primary-foreground" : ""}
            >
              {s}
            </Button>
          ))}
        </div>
        {error && <div className="text-xs text-red-700">error: {error}</div>}
        {loading && !data && <div className="text-xs text-muted-foreground">loading...</div>}
        {data && data.count === 0 && (
          <div className="text-xs text-muted-foreground italic">
            no trace records yet for {scenario}. Run the bench or curl the harness walker.
          </div>
        )}
        {data && data.count > 0 && (
          <ScrollArea className="h-[60vh]">
            <ul className="space-y-1">
              {data.records.map((rec, idx) => {
                const r = rec as Record<string, unknown>;
                const ts = String(r.ts ?? "").replace("T", " ").slice(0, 19);
                const stage = String(r.stage ?? "?");
                const rest = Object.fromEntries(
                  Object.entries(r).filter(([k]) => !["ts", "scenario_id", "stage"].includes(k)),
                );
                return (
                  <li key={idx} className="rounded border p-2 text-[11px] font-mono flex items-start gap-2">
                    <span className="text-muted-foreground">{ts}</span>
                    <Badge variant="muted">{stage}</Badge>
                    <span className="flex-1 break-all">{JSON.stringify(rest)}</span>
                  </li>
                );
              })}
            </ul>
          </ScrollArea>
        )}
      </CardContent>
    </Card>
  );
}
