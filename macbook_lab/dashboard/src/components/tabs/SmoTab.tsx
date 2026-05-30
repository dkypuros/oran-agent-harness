import { useCallback } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { smoApi } from "@/api/smo";
import { usePolling } from "@/hooks/usePolling";

export function SmoTab() {
  const { data, error, loading, refresh, lastUpdate } = usePolling(
    useCallback(() => smoApi.history(50), []),
    3000,
  );
  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle>SMO (TMF921 intents)</CardTitle>
            <CardDescription>
              Companion intents emitted UP to the partner SMO when blast radius forces dual-route remediation.
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
            no intents emitted yet. POST /api/smo/emit or run the bench to trigger one (Scenario E fires this).
          </div>
        )}
        {data && data.count > 0 && (
          <ScrollArea className="h-[60vh]">
            <ul className="space-y-2">
              {data.intents.map((intent, idx) => (
                <li key={idx} className="rounded border p-3 text-xs">
                  <div className="flex flex-wrap items-center gap-2 mb-1">
                    <Badge variant="default">{intent.intent_type ?? "intent"}</Badge>
                    <span className="font-mono text-muted-foreground">{intent.intent_id}</span>
                  </div>
                  <div>Affected: <span className="font-mono">{intent.affected_resources?.join(", ")}</span></div>
                  <div>Window: {intent.window_start} -- {intent.window_end}</div>
                  <div>Impact: {intent.service_impact_hint} (expected handovers: {intent.expected_handover_count})</div>
                </li>
              ))}
            </ul>
          </ScrollArea>
        )}
      </CardContent>
    </Card>
  );
}
