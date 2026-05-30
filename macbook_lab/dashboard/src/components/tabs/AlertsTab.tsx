import { useCallback } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge, type BadgeVariant } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { ptpApi } from "@/api/ptp";
import { usePolling } from "@/hooks/usePolling";

const VERDICT_VARIANT: Record<string, BadgeVariant> = {
  software_ok: "success",
  software_ok_persistent: "warning",
  hardware_anomaly: "danger",
  firmware_anomaly: "danger",
};

export function AlertsTab() {
  const { data, error, loading, refresh, lastUpdate } = usePolling(
    useCallback(() => ptpApi.history(50), []),
    3000,
  );
  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle>Alerts (PTP CloudEvents)</CardTitle>
            <CardDescription>
              PTP sync alarms emitted by the PTP operator stub in O-RAN.WG6 O-Cloud Notification API shape.
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
            no PTP alarms emitted yet. POST /api/ptp/publish to trigger an alarm sequence.
          </div>
        )}
        {data && data.count > 0 && (
          <ScrollArea className="h-[60vh]">
            <ul className="space-y-1.5">
              {data.events.map((ev, idx) => {
                const verdict = ev.data?.verdict ?? "";
                return (
                  <li key={idx} className="rounded border p-2 text-xs">
                    <div className="flex flex-wrap items-center gap-2 mb-1">
                      {verdict && <Badge variant={VERDICT_VARIANT[verdict] ?? "muted"}>{verdict}</Badge>}
                      <span className="text-muted-foreground">{ev.time?.slice(0, 19)}</span>
                    </div>
                    <div className="font-mono text-muted-foreground break-all">{ev.source ?? ""}</div>
                    <div className="font-mono">{ev.type ?? ""}</div>
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
