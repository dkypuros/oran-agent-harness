import { useCallback } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge, type BadgeVariant } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { redfishApi } from "@/api/redfish";
import { usePolling } from "@/hooks/usePolling";

const STATE_VARIANT: Record<string, BadgeVariant> = {
  Running: "warning",
  Completed: "success",
  Failed: "danger",
};

export function OCloudTab() {
  const { data, error, loading, refresh, lastUpdate } = usePolling(
    useCallback(() => redfishApi.history(50), []),
    3000,
  );
  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle>O-Cloud (Redfish BMC tasks)</CardTitle>
            <CardDescription>
              DMTF Redfish DSP0266 SimpleUpdate task lifecycle. The BMC layer underneath Metal3.
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
            no Redfish tasks recorded yet. POST /api/redfish/update or run Scenario E.
          </div>
        )}
        {data && data.count > 0 && (
          <ScrollArea className="h-[60vh]">
            <ul className="space-y-1.5">
              {data.tasks.map((t, idx) => (
                <li key={idx} className="rounded border p-2 text-xs flex items-start gap-2">
                  <Badge variant={STATE_VARIANT[t.task_state ?? ""] ?? "muted"}>{t.task_state ?? "?"}</Badge>
                  <div className="flex-1">
                    <div className="font-mono text-muted-foreground">{t.task_uri ?? ""}</div>
                    <div>{t.message ?? ""}</div>
                    {typeof t.percent_complete === "number" && (
                      <div className="mt-1 h-1 bg-muted rounded overflow-hidden">
                        <div className="h-full bg-primary" style={{ width: `${t.percent_complete}%` }} />
                      </div>
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
