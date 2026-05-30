import { useCallback } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge, type BadgeVariant } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { metal3Api } from "@/api/metal3";
import { usePolling } from "@/hooks/usePolling";

const PHASE_VARIANT: Record<string, BadgeVariant> = {
  Preparing: "muted",
  Pushing: "default",
  Rebooting: "warning",
  Verifying: "default",
  Updated: "success",
};

export function HardwareManagerTab() {
  const { data, error, loading, refresh, lastUpdate } = usePolling(
    useCallback(() => metal3Api.history(50), []),
    3000,
  );
  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle>Hardware Manager (Metal3 BMO)</CardTitle>
            <CardDescription>
              Firmware push phase progression for Scenario E (Intel E810 NIC firmware update).
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
        {error && <div className="text-xs text-red-700">error: {error}</div>}
        {loading && !data && <div className="text-xs text-muted-foreground">loading...</div>}
        {data && data.count === 0 && (
          <div className="text-xs text-muted-foreground italic">
            no firmware phases recorded yet. POST /api/metal3/apply or run the bench (Scenario E) to trigger.
          </div>
        )}
        {data && data.count > 0 && (
          <ScrollArea className="h-[60vh]">
            <ul className="space-y-1.5">
              {data.phases.map((phase, idx) => (
                <li key={idx} className="rounded border p-2 text-xs flex items-start gap-2">
                  <Badge variant={PHASE_VARIANT[phase.phase ?? ""] ?? "muted"}>{phase.phase ?? "?"}</Badge>
                  <div className="flex-1">
                    <div className="font-medium">{phase.component ?? ""}</div>
                    <div className="text-muted-foreground">{phase.detail ?? ""}</div>
                    {typeof phase.bytes === "number" && (
                      <div className="text-muted-foreground">{phase.bytes.toLocaleString()} bytes</div>
                    )}
                    {phase.scenario_id && (
                      <div className="font-mono text-muted-foreground">scenario: {phase.scenario_id}</div>
                    )}
                  </div>
                </li>
              ))}
            </ul>
          </ScrollArea>
        )}
      </CardContent>
    </Card>
  );
}
