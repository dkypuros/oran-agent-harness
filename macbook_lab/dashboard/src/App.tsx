import { useEffect, useState } from "react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { OverviewTab } from "@/components/tabs/OverviewTab";
import { SmoTab } from "@/components/tabs/SmoTab";
import { HardwareManagerTab } from "@/components/tabs/HardwareManagerTab";
import { OCloudTab } from "@/components/tabs/OCloudTab";
import { AlertsTab } from "@/components/tabs/AlertsTab";
import { PtpLogsTab } from "@/components/tabs/PtpLogsTab";
import { ChatTab } from "@/components/tabs/ChatTab";
import { TwoLoopDemo } from "@/components/demo/TwoLoopDemo";
import { Button } from "@/components/ui/button";

const TAB_IDS = ["overview", "chat", "smo", "hardware", "ocloud", "alerts", "ptp"] as const;
type TabId = (typeof TAB_IDS)[number];
type DashboardMode = "simple" | "advanced";

function currentHash(): string {
  return (window.location.hash || "#demo").replace("#", "");
}

function isTabId(hash: string): hash is TabId {
  return (TAB_IDS as readonly string[]).includes(hash);
}

function initialTab(): TabId {
  const hash = currentHash();
  return isTabId(hash) ? hash : "overview";
}

function initialMode(): DashboardMode {
  return isTabId(currentHash()) ? "advanced" : "simple";
}

export default function App() {
  const [mode, setMode] = useState<DashboardMode>(initialMode());
  const [tab, setTab] = useState<TabId>(initialTab());

  useEffect(() => {
    const onHashChange = () => {
      const hash = currentHash();
      if (isTabId(hash)) {
        setTab(hash);
        setMode("advanced");
      } else {
        setMode("simple");
      }
    };

    window.addEventListener("hashchange", onHashChange);
    return () => window.removeEventListener("hashchange", onHashChange);
  }, []);

  useEffect(() => {
    const nextHash = mode === "simple" ? "demo" : tab;
    if (currentHash() !== nextHash) {
      window.location.hash = nextHash;
    }
  }, [mode, tab]);

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
          <div className="flex items-center gap-3">
            <div className="rounded-md bg-muted p-1">
              <Button
                onClick={() => setMode("simple")}
                className={mode === "simple" ? "bg-background shadow" : "border-transparent bg-transparent"}
              >
                Simple demo
              </Button>
              <Button
                onClick={() => setMode("advanced")}
                className={mode === "advanced" ? "bg-background shadow" : "border-transparent bg-transparent"}
              >
                Advanced
              </Button>
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
        </div>
      </header>
      <main className="max-w-7xl mx-auto px-6 py-5">
        {mode === "simple" ? (
          <TwoLoopDemo />
        ) : (
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
        )}
      </main>
    </div>
  );
}
