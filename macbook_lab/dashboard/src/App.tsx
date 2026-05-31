import { useEffect, useState } from "react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { OverviewTab } from "@/components/tabs/OverviewTab";
import { SmoTab } from "@/components/tabs/SmoTab";
import { HardwareManagerTab } from "@/components/tabs/HardwareManagerTab";
import { OCloudTab } from "@/components/tabs/OCloudTab";
import { AlertsTab } from "@/components/tabs/AlertsTab";
import { PtpLogsTab } from "@/components/tabs/PtpLogsTab";
import { ChatTab } from "@/components/tabs/ChatTab";

const TAB_IDS = ["overview", "chat", "smo", "hardware", "ocloud", "alerts", "ptp"] as const;
type TabId = (typeof TAB_IDS)[number];

function initialTab(): TabId {
  const hash = (window.location.hash || "#overview").replace("#", "");
  return (TAB_IDS as readonly string[]).includes(hash) ? (hash as TabId) : "overview";
}

export default function App() {
  const [tab, setTab] = useState<TabId>(initialTab());

  useEffect(() => {
    window.location.hash = tab;
  }, [tab]);

  return (
    <div className="min-h-screen bg-background">
      <header className="border-b">
        <div className="max-w-7xl mx-auto px-6 py-3 flex items-center justify-between">
          <div>
            <h1 className="text-lg font-semibold">O-RAN Agent Harness Lab</h1>
            <p className="text-xs text-muted-foreground">
              Local view of the harness platform: PTP alarms, hardware manager, O-Cloud, SMO intents, traces.
            </p>
          </div>
          <a
            className="text-xs text-muted-foreground hover:underline"
            href="https://github.com/dkypuros/oran-agent-harness"
            target="_blank"
            rel="noreferrer"
          >
            github.com/dkypuros/oran-agent-harness
          </a>
        </div>
      </header>
      <main className="max-w-7xl mx-auto px-6 py-5">
        <Tabs value={tab} onValueChange={(v) => setTab(v as TabId)}>
          <TabsList>
            <TabsTrigger value="overview">Overview</TabsTrigger>
            <TabsTrigger value="chat">oh-my-tiny-oran</TabsTrigger>
            <TabsTrigger value="smo">SMO</TabsTrigger>
            <TabsTrigger value="hardware">Hardware Manager</TabsTrigger>
            <TabsTrigger value="ocloud">O-Cloud</TabsTrigger>
            <TabsTrigger value="alerts">Alerts</TabsTrigger>
            <TabsTrigger value="ptp">PTP sync logs</TabsTrigger>
          </TabsList>
          <TabsContent value="overview"><OverviewTab /></TabsContent>
          <TabsContent value="chat"><ChatTab /></TabsContent>
          <TabsContent value="smo"><SmoTab /></TabsContent>
          <TabsContent value="hardware"><HardwareManagerTab /></TabsContent>
          <TabsContent value="ocloud"><OCloudTab /></TabsContent>
          <TabsContent value="alerts"><AlertsTab /></TabsContent>
          <TabsContent value="ptp"><PtpLogsTab /></TabsContent>
        </Tabs>
      </main>
    </div>
  );
}
