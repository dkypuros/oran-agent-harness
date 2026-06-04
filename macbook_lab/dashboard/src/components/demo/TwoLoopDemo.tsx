import { useEffect, useState, type ReactNode } from "react";
import { chatApi, type ChatTurn } from "@/api/chat";
import { harnessApi, type HarnessRunEvent } from "@/api/harness";
import { Badge, type BadgeVariant } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { evidenceCards, standardsMap } from "./twoLoopDemoData";

const RIGHT_LOOP_SCENARIOS = [
  {
    id: "D_phc_drift_hw_only",
    label: "D: Driver / KMM",
    short: "host_driver → O2 IMS → KMM",
    routeKind: "DOWN only",
    intent: "Swap the affected ice driver after drain/isolate.",
    prompt:
      "/oran-discover:guardrail Check the right-loop KMM driver remediation boundary for D_phc_drift_hw_only. Use live harness state where available and explain taxonomy, guardrail, O2 IMS dispatch, sandbox verdict, and approval gate.",
  },
  {
    id: "E_nic_firmware_update",
    label: "E: Firmware + SMO",
    short: "node_firmware → O2 IMS + TMF921",
    routeKind: "DOWN + UP",
    intent:
      "Show the dual-route path: Metal3/Redfish down, SMO companion intent up.",
    prompt:
      "/oran-discover:plan Survey the dual-route right-loop remediation for E_nic_firmware_update. Explain Redfish, Metal3, SMO TMF921, taxonomy, guardrails, O2 IMS dispatch, and why production remains operator-controlled.",
  },
  {
    id: "E_with_smo_reject",
    label: "E reject: SMO reject",
    short: "node_firmware → SMO rejects window",
    routeKind: "DOWN + UP blocked",
    intent:
      "Show the same firmware path when the partner SMO rejects the service window.",
    prompt:
      "/oran-discover:smo Inspect the rejected companion intent for E_with_smo_reject, then explain how the right-loop harness keeps the O2 IMS remediation blocked behind the operator.",
  },
] as const;

type RightLoopScenarioId = (typeof RIGHT_LOOP_SCENARIOS)[number]["id"];

function getRightLoopScenario(id: RightLoopScenarioId) {
  return RIGHT_LOOP_SCENARIOS.find((scenario) => scenario.id === id)!;
}

function RightLoopProofStrip() {
  return (
    <div className="rounded border border-blue-200 bg-background p-3">
      <div className="text-xs uppercase text-muted-foreground">
        what the right loop proves
      </div>
      <div className="mt-2 grid gap-2 md:grid-cols-2">
        <div className="rounded border border-blue-200 bg-blue-50 p-3">
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-sm font-semibold">D path</span>
            <Badge variant="default">DOWN only</Badge>
          </div>
          <p className="mt-1 text-xs leading-5 text-blue-950">
            PTP/PHC finding becomes <strong>host_driver</strong>; router.py and
            taxonomy.yaml send it through <strong>O2 IMS</strong> into the
            O-Cloud <strong>KMM driver</strong> path.
          </p>
        </div>
        <div className="rounded border border-purple-200 bg-purple-50 p-3">
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-sm font-semibold">E path</span>
            <Badge variant="warning">DOWN + UP</Badge>
          </div>
          <p className="mt-1 text-xs leading-5 text-purple-950">
            Firmware remediation becomes <strong>node_firmware</strong>; the
            harness sends <strong>O2 IMS → Metal3/Redfish</strong> down while
            emitting a <strong>TMF921 SMO</strong> companion intent up.
          </p>
        </div>
      </div>
      <p className="mt-2 text-xs leading-5 text-muted-foreground">
        The endpoints are stubs; the harness run, routing decision, guardrail
        evaluation, sandbox verdict, and AuditEvent are the real demo contract.
      </p>
    </div>
  );
}

function getRightLoopCommands(scenarioId: RightLoopScenarioId) {
  const scenario = getRightLoopScenario(scenarioId);
  return [
    {
      label: "/commands",
      prompt: "/commands",
    },
    {
      label: "Guardrail check",
      prompt: `/oran-discover:guardrail Check the right-loop remediation boundary for ${scenario.id}. Use live harness state where available and explain taxonomy, guardrail policy, O2 IMS dispatch, endpoint target, sandbox verdict, and approval gate.`,
    },
    {
      label: "Pre-flight survey",
      prompt: `/oran-discover:plan Survey the current harness surfaces for ${scenario.id} before I authorize any right-loop remediation.`,
    },
    {
      label: scenario.label,
      prompt: scenario.prompt,
    },
  ] as const;
}

interface DemoChatMessage {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  meta?: ChatTurn;
  pending?: boolean;
}

const statusVariant: Record<string, BadgeVariant> = {
  hardware_anomaly: "danger",
  unhealthy: "danger",
  service_followup: "warning",
  node_actionable: "default",
  ruled_out_primary: "muted",
};

function HarnessPanel({
  title,
  description,
  children,
}: {
  title: string;
  description: string;
  children: ReactNode;
}) {
  return (
    <Card className="border-emerald-200 bg-emerald-50/50 shadow-none">
      <CardHeader>
        <div className="flex items-start justify-between gap-3">
          <div>
            <CardTitle>{title}</CardTitle>
            <CardDescription>{description}</CardDescription>
          </div>
          <Badge variant="success">harness</Badge>
        </div>
      </CardHeader>
      <CardContent>{children}</CardContent>
    </Card>
  );
}

function LoopStep({
  number,
  title,
  active = false,
}: {
  number: number;
  title: string;
  active?: boolean;
}) {
  return (
    <div
      className={
        active
          ? "rounded border border-primary bg-blue-50 p-2"
          : "rounded border bg-background p-2"
      }
    >
      <div className="text-[10px] uppercase tracking-wide text-muted-foreground">
        step {number}
      </div>
      <div className="text-xs font-semibold">{title}</div>
    </div>
  );
}

function asRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : {};
}

function textValue(value: unknown, fallback = "-"): string {
  if (value === undefined || value === null || value === "") return fallback;
  if (typeof value === "string") return value;
  if (typeof value === "number" || typeof value === "boolean")
    return String(value);
  return JSON.stringify(value);
}

function boolValue(value: unknown): boolean {
  return value === true || value === "true";
}

function shortText(value: unknown, fallback = "-", maxLength = 92): string {
  const text = textValue(value, fallback);
  return text.length > maxLength ? `${text.slice(0, maxLength - 1)}…` : text;
}

function scenarioHasSmoCompanion(scenarioId: RightLoopScenarioId): boolean {
  return scenarioId !== "D_phc_drift_hw_only";
}

function normalizeRightLoopPrompt(
  raw: string,
  selectedScenarioId: RightLoopScenarioId,
): string {
  const trimmed = raw.trim();
  if (!trimmed) return trimmed;

  const slashMatch = trimmed.match(/\/oran-discover:[a-z0-9_-]+/i);
  if (!slashMatch) return trimmed;

  const matchedCommand = slashMatch[0];
  if (
    matchedCommand === "/oran-discover:guardrail" &&
    trimmed === matchedCommand
  ) {
    return `/oran-discover:guardrail Check the right-loop remediation boundary for ${selectedScenarioId}. Use live harness state where available and explain taxonomy, guardrail policy, O2 IMS dispatch, endpoint target, sandbox verdict, and approval gate.`;
  }

  if (trimmed.startsWith("/")) return trimmed;
  return matchedCommand;
}

function EndpointNode({
  title,
  subtitle,
  detail,
  active,
  variant = "neutral",
}: {
  title: string;
  subtitle: string;
  detail: string;
  active: boolean;
  variant?: "neutral" | "good" | "warning" | "danger";
}) {
  const palette =
    variant === "good"
      ? "border-green-200 bg-green-50 text-green-950"
      : variant === "warning"
        ? "border-yellow-200 bg-yellow-50 text-yellow-950"
        : variant === "danger"
          ? "border-red-200 bg-red-50 text-red-950"
          : active
            ? "border-blue-200 bg-blue-50 text-blue-950"
            : "border-slate-200 bg-slate-50 text-slate-500";

  return (
    <div className={`rounded border p-3 ${palette}`}>
      <div className="flex items-start justify-between gap-2">
        <div>
          <div className="text-[10px] uppercase tracking-wide opacity-70">
            {subtitle}
          </div>
          <div className="text-sm font-semibold">{title}</div>
        </div>
        <Badge
          variant={
            active
              ? variant === "warning"
                ? "warning"
                : variant === "danger"
                  ? "danger"
                  : "success"
              : "muted"
          }
        >
          {active ? "active" : "quiet"}
        </Badge>
      </div>
      <p className="mt-2 text-xs leading-5 opacity-80">{detail}</p>
    </div>
  );
}

function HarnessPathVisual({
  scenarioId,
  audit,
}: {
  scenarioId: RightLoopScenarioId;
  audit: HarnessRunEvent | null;
}) {
  const remediation = asRecord(audit?.event?.remediation);
  const o2ims = asRecord(remediation.o2ims_dispatch);
  const companion = asRecord(remediation.companion_intent);
  const companionResult = asRecord(companion.dispatch_result);
  const guardrail = asRecord(remediation.guardrailResult);
  const sandbox = asRecord(remediation.sandbox_verdict);
  const hasAudit = Boolean(audit);
  const scenario = getRightLoopScenario(scenarioId);
  const isFirmware = scenarioId !== "D_phc_drift_hw_only";
  const smoAccepted =
    companionResult.accepted === undefined
      ? scenarioId === "E_nic_firmware_update"
      : boolValue(companionResult.accepted);
  const smoRejected =
    scenarioId === "E_with_smo_reject" ||
    (companionResult.accepted !== undefined && !smoAccepted);

  return (
    <div className="rounded border border-blue-200 bg-background p-3">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <div className="text-xs uppercase text-muted-foreground">
            live right-loop topology
          </div>
          <div className="mt-1 text-sm font-semibold">{scenario.short}</div>
        </div>
        <Badge variant={hasAudit ? "success" : "muted"}>
          {hasAudit ? "harness-walker attached" : "planned path"}
        </Badge>
      </div>
      <p className="mt-1 text-xs leading-5 text-muted-foreground">
        These boxes are stubbed lab endpoints, but the wiring is real: the
        right loop asks harness-walker for an AuditEvent, then surfaces router,
        taxonomy, guardrail, O2 IMS, O-Cloud, and SMO evidence from that run.
      </p>

      <div className="mt-3 grid gap-2 md:grid-cols-3">
        <EndpointNode
          title="harness-walker"
          subtitle="orchestrator"
          active={hasAudit}
          detail={
            hasAudit
              ? `${textValue(audit?.eventType)} ${textValue(audit?.event?.correlatedEventId)}`
              : `Ready to run /run/${scenarioId}.`
          }
        />
        <EndpointNode
          title="router.py + taxonomy.yaml"
          subtitle="classification"
          active={hasAudit}
          detail={`${textValue(remediation.taxonomyMatch, isFirmware ? "node_firmware" : "host_driver")} routes ${textValue(remediation.targetLayer, "infra")} remediation.`}
        />
        <EndpointNode
          title="guardrail.py + guardrails.yaml"
          subtitle="policy"
          active={hasAudit}
          variant={
            guardrail.outcome === "fail" ? "danger" : hasAudit ? "good" : "neutral"
          }
          detail={`Policy ${textValue(guardrail.outcome, "pending")} · sandbox apply_allowed=${textValue(sandbox.apply_allowed, "pending")} · human approval remains required.`}
        />
        <EndpointNode
          title="O2 IMS / O-Cloud Manager"
          subtitle="down route"
          active
          variant={hasAudit && boolValue(o2ims.accepted) ? "good" : "neutral"}
          detail={shortText(
            o2ims.ocm_response,
            isFirmware
              ? "Will dispatch firmware remediation down into the O-Cloud."
              : "Will dispatch driver remediation down into the O-Cloud.",
          )}
        />
        <EndpointNode
          title={isFirmware ? "Metal3 + Redfish" : "KMM driver path"}
          subtitle={isFirmware ? "firmware endpoint" : "driver endpoint"}
          active={hasAudit}
          variant={hasAudit ? "good" : "neutral"}
          detail={
            isFirmware
              ? `Stub shows HostFirmwareComponents + Redfish SimpleUpdate; payload ${textValue(remediation.actionPayloadRef, "intel-e810-firmware-update-4.50")}.`
              : `Stub shows Module reconciler driver swap; payload ${textValue(remediation.actionPayloadRef, "ice-driver-update-1.13.7")}.`
          }
        />
        <EndpointNode
          title="SMO / TMF921"
          subtitle="up route"
          active={hasAudit && Boolean(companion.dispatch_route)}
          variant={smoRejected ? "warning" : hasAudit && Boolean(companion.dispatch_route) ? "good" : "neutral"}
          detail={
            scenarioHasSmoCompanion(scenarioId)
              ? shortText(
                  companionResult.smo_response,
                  smoRejected
                    ? "Companion intent exists, but the partner SMO rejects this service window."
                    : "Companion intent notifies the partner SMO before firmware maintenance.",
                )
              : "No TMF921 companion for this driver-only remediation; /oran-discover:smo is still available as a quiet surface."
          }
        />
      </div>
    </div>
  );
}

function HarnessRunSummary({ audit }: { audit: HarnessRunEvent }) {
  const remediation = asRecord(audit.event?.remediation);
  const guardrail = asRecord(remediation.guardrailResult);
  const sandbox = asRecord(remediation.sandbox_verdict);
  const blastRadius = asRecord(guardrail.blastRadius);
  const o2ims = asRecord(remediation.o2ims_dispatch);
  const companion = asRecord(remediation.companion_intent);
  const companionResult = asRecord(companion.dispatch_result);

  return (
    <div className="rounded border border-green-200 bg-green-50 p-3">
      <div className="text-xs uppercase text-green-800">
        live evidence sidecar
      </div>
      <div className="mt-1 font-semibold text-green-900">
        {textValue(audit.eventType)} ·{" "}
        {textValue(audit.event?.correlatedEventId)}
      </div>
      <div className="mt-3 grid gap-2 md:grid-cols-2">
        <div className="rounded border border-green-200 bg-background p-2 text-xs">
          <div className="uppercase text-muted-foreground">action</div>
          <div className="font-semibold">
            {textValue(remediation.actionType)}
          </div>
          <div className="text-muted-foreground">
            {textValue(remediation.actionTarget)}
          </div>
        </div>
        <div className="rounded border border-green-200 bg-background p-2 text-xs">
          <div className="uppercase text-muted-foreground">approval</div>
          <div className="font-semibold">
            requiresHumanApproval={textValue(remediation.requiresHumanApproval)}
          </div>
          <div className="text-muted-foreground">
            status: {textValue(remediation.humanApprovalStatus)}
          </div>
        </div>
        <div className="rounded border border-green-200 bg-background p-2 text-xs">
          <div className="uppercase text-muted-foreground">guardrail</div>
          <div className="font-semibold">
            outcome: {textValue(guardrail.outcome)}
          </div>
          <div className="text-muted-foreground">
            blast radius: {textValue(blastRadius.nodes)} node /{" "}
            {textValue(blastRadius.cells)} cells
          </div>
        </div>
        <div className="rounded border border-green-200 bg-background p-2 text-xs">
          <div className="uppercase text-muted-foreground">sandbox/eval</div>
          <div className="font-semibold">
            apply_allowed={textValue(sandbox.apply_allowed)}
          </div>
          <div className="text-muted-foreground">
            {textValue(sandbox.baseline_match)}
          </div>
        </div>
        <div className="rounded border border-green-200 bg-background p-2 text-xs">
          <div className="uppercase text-muted-foreground">O2 IMS down route</div>
          <div className="font-semibold">
            accepted={textValue(o2ims.accepted)}
          </div>
          <div className="text-muted-foreground">
            {textValue(o2ims.ocloud_internal_path)}
          </div>
        </div>
        <div className="rounded border border-green-200 bg-background p-2 text-xs">
          <div className="uppercase text-muted-foreground">SMO up route</div>
          <div className="font-semibold">
            {companion.dispatch_route
              ? textValue(companion.dispatch_route)
              : "no companion intent"}
          </div>
          <div className="text-muted-foreground">
            {companion.dispatch_route
              ? `accepted=${textValue(companionResult.accepted)}`
              : "driver-only remediation"}
          </div>
        </div>
      </div>
      <p className="mt-3 text-xs leading-5 text-green-900">
        {textValue(
          sandbox.rationale,
          "Harness returned an audit event; production action remains gated.",
        )}
      </p>
    </div>
  );
}

function EvidenceSynthesis() {
  const primaryEvidence = evidenceCards.slice(0, 3);
  const ruledOut = evidenceCards.find(
    (card) => card.status === "ruled_out_primary",
  );

  return (
    <div className="space-y-3">
      <div className="rounded border bg-background p-3">
        <div className="text-xs uppercase text-muted-foreground">
          evidence synthesis
        </div>
        <div className="mt-2 space-y-2">
          {primaryEvidence.map((card) => (
            <div
              key={card.title}
              className="flex items-start justify-between gap-3 text-xs"
            >
              <div>
                <span className="font-semibold">{card.title}</span>
                <span className="text-muted-foreground"> - {card.detail}</span>
                <div className="mt-1 text-[11px] text-muted-foreground">
                  source: {card.source}
                </div>
              </div>
              <Badge variant={statusVariant[card.status] ?? "muted"}>
                {card.status}
              </Badge>
            </div>
          ))}
        </div>
      </div>

      <div className="rounded border bg-background p-3">
        <div className="text-xs uppercase text-muted-foreground">
          recommendation with citations
        </div>
        <div className="mt-1 font-semibold">
          Likely NIC/PHC hardware timestamp issue
        </div>
        <p className="mt-1 text-xs leading-5 text-muted-foreground">
          PTP drift triggered the investigation; unhealthy NIC timestamp
          capability points toward hardware/PHC behavior; Redfish/BMC inventory
          keeps hardware follow-up traceable. {ruledOut?.title} (
          {ruledOut?.source}) is considered but ruled out as the primary cause,
          so this is not presented as generic config or operator drift.
        </p>
      </div>
    </div>
  );
}

function LeftLoop() {
  const [investigated, setInvestigated] = useState(false);

  return (
    <Card className="border-red-200 bg-red-50/40">
      <CardHeader>
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div>
            <CardTitle>Left loop: alert + harness</CardTitle>
            <CardDescription>
              One loop: alert appears, operator asks the harness to investigate,
              evidence is synthesized, and the harness recommends.
            </CardDescription>
          </div>
          <Badge variant="danger">PTP drift → NIC/PHC fault</Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid gap-2 md:grid-cols-4">
          <LoopStep number={1} title="Alert" active />
          <LoopStep
            number={2}
            title="Investigate in harness"
            active={investigated}
          />
          <LoopStep
            number={3}
            title="Evidence synthesis"
            active={investigated}
          />
          <LoopStep number={4} title="Recommendation" active={investigated} />
        </div>

        <div className="grid gap-4 lg:grid-cols-[0.8fr_1.2fr]">
          <Card className="bg-background shadow-none">
            <CardHeader>
              <div className="flex items-start justify-between gap-3">
                <div>
                  <CardTitle>Alert</CardTitle>
                  <CardDescription>
                    PTP sync drift on a timing-sensitive worker.
                  </CardDescription>
                </div>
                <Badge variant="danger">active</Badge>
              </div>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="rounded border bg-red-50/60 p-3 text-sm">
                <div className="font-semibold">worker-timing-03</div>
                <p className="mt-1 text-xs leading-5 text-muted-foreground">
                  PTP sync drift alarm. Timing-sensitive workloads are at risk
                  because hardware timestamp trust is degraded.
                </p>
              </div>
              <div className="rounded border border-blue-200 bg-blue-50 p-3">
                <div className="text-xs font-semibold uppercase tracking-wide text-blue-900">
                  Next operator action
                </div>
                <p className="mt-1 text-xs leading-5 text-blue-900">
                  Start the harness investigation before any recommendation
                  appears.
                </p>
                <Button
                  onClick={() => setInvestigated(true)}
                  className={
                    investigated
                      ? "mt-3 h-10 bg-green-600 px-4 text-white shadow-sm hover:bg-green-700"
                      : "mt-3 h-10 bg-blue-600 px-4 text-white shadow-sm hover:bg-blue-700"
                  }
                >
                  {investigated
                    ? "Harness investigation complete"
                    : "Start harness investigation"}
                </Button>
              </div>
            </CardContent>
          </Card>

          <HarnessPanel
            title="Harness discovery"
            description="The harness ties alert, evidence, and recommendation together."
          >
            {investigated ? (
              <EvidenceSynthesis />
            ) : (
              <div className="rounded border bg-background p-4 text-sm text-muted-foreground">
                Waiting for the operator to start harness investigation. No
                recommendation is shown before the harness correlates the alert
                with evidence.
              </div>
            )}
          </HarnessPanel>
        </div>
      </CardContent>
    </Card>
  );
}

function RightLoop() {
  const [approved, setApproved] = useState(false);
  const [selectedScenarioId, setSelectedScenarioId] =
    useState<RightLoopScenarioId>("D_phc_drift_hw_only");
  const [chatSessionId, setChatSessionId] = useState<string | null>(null);
  const [chatInput, setChatInput] = useState("");
  const [chatMessages, setChatMessages] = useState<DemoChatMessage[]>([]);
  const [chatSending, setChatSending] = useState(false);
  const [chatError, setChatError] = useState<string | null>(null);
  const [chatHealth, setChatHealth] = useState<{
    anthropic_key_set: boolean;
    model: string;
  } | null>(null);
  const [harnessAudit, setHarnessAudit] = useState<HarnessRunEvent | null>(
    null,
  );
  const [evidenceLoading, setEvidenceLoading] = useState(false);
  const [evidenceError, setEvidenceError] = useState<string | null>(null);
  const hasAssistantResponse = chatMessages.some(
    (message) => message.role === "assistant" && !message.pending,
  );
  const selectedScenario = getRightLoopScenario(selectedScenarioId);
  const rightLoopCommands = getRightLoopCommands(selectedScenarioId);

  useEffect(() => {
    chatApi
      .health()
      .then((health) =>
        setChatHealth({
          anthropic_key_set: health.anthropic_key_set,
          model: health.model,
        }),
      )
      .catch(() => setChatHealth(null));
  }, []);

  function showCommands() {
    const now = Date.now();
    setChatMessages((prev) => [
      ...prev,
      { id: `right-user-${now}`, role: "user", content: "/commands" },
      {
        id: `right-assistant-${now}`,
        role: "assistant",
        content: [
          "Available right-loop harness commands:",
          "• /oran-discover:guardrail - inspect deterministic policy, approval gates, sandbox, and AuditEvent shape.",
          "• /oran-discover:plan - pre-flight survey across PTP, right-loop infra/service, taxonomy, and guardrails.",
          "• /oran-discover:ptp - inspect the PTP/PHC alarm side before remediation.",
          "• /oran-discover:metal3, /oran-discover:redfish, /oran-discover:smo - inspect right-loop infrastructure and service-side surfaces.",
          "• harness-walker /run/<scenario> - attaches the live AuditEvent sidecar that drives the endpoint topology.",
          "Committed right-loop scenarios: D_phc_drift_hw_only, E_nic_firmware_update, E_with_smo_reject.",
          "Pick a preset below or edit the prompt, then press Enter.",
        ].join("\n"),
      },
    ]);
  }

  async function attachEvidenceSidecar(scenarioId = selectedScenarioId) {
    setEvidenceLoading(true);
    setEvidenceError(null);
    try {
      const audit = await harnessApi.runScenario(scenarioId);
      setHarnessAudit(audit);
    } catch (error) {
      setEvidenceError(error instanceof Error ? error.message : String(error));
    } finally {
      setEvidenceLoading(false);
    }
  }

  async function sendToRightLoopHarness(raw: string) {
    const text = normalizeRightLoopPrompt(raw, selectedScenarioId);
    if (!text || chatSending) return;

    if (text === "/commands") {
      showCommands();
      setChatInput("");
      return;
    }

    if (!approved) {
      setChatMessages((prev) => [
        ...prev,
        {
          id: `right-system-${Date.now()}`,
          role: "system",
          content:
            "Approve the right-loop proposal first. The chat harness stays behind the human gate.",
        },
      ]);
      return;
    }

    const now = Date.now();
    const pendingId = `right-assistant-pending-${now}`;
    setChatMessages((prev) => [
      ...prev,
      { id: `right-user-${now}`, role: "user", content: text },
      {
        id: pendingId,
        role: "assistant",
        content: "oh-my-tiny-oran is inspecting live harness output...",
        pending: true,
      },
    ]);
    setChatInput("");
    setChatSending(true);
    setChatError(null);

    if (chatHealth?.anthropic_key_set === false) {
      setChatMessages((prev) =>
        prev.map((message) =>
          message.id === pendingId
            ? {
                ...message,
                pending: false,
                role: "system",
                content:
                  "oh-my-tiny-oran is wired into the right loop, but ANTHROPIC_API_KEY is not set in the running harness-chat container. Add macbook_lab/anthropic.env and restart harness-chat to enable the assistant response.",
              }
            : message,
        ),
      );
      setChatSending(false);
      return;
    }

    try {
      const response = await chatApi.send(text, chatSessionId);
      if (!chatSessionId) setChatSessionId(response.session_id);
      setChatMessages((prev) =>
        prev.map((message) =>
          message.id === pendingId
            ? {
                id: `right-assistant-${Date.now()}`,
                role: "assistant",
                content: response.turn.content,
                meta: response.turn,
          }
            : message,
        ),
      );
      const inspectedScenario = RIGHT_LOOP_SCENARIOS.find((scenario) => {
        const needle = `/run/${scenario.id}`;
        const toolInspected = response.turn.tool_uses.some((toolUse) =>
          JSON.stringify(toolUse.input).includes(needle),
        );
        return toolInspected || text.includes(scenario.id);
      });
      if (inspectedScenario) {
        setSelectedScenarioId(inspectedScenario.id);
        await attachEvidenceSidecar(inspectedScenario.id);
      }
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      setChatError(message);
      setChatMessages((prev) =>
        prev.map((chatMessage) =>
          chatMessage.id === pendingId
            ? {
                ...chatMessage,
                pending: false,
                role: "system",
                content: `oh-my-tiny-oran chat failed (${message}).`,
              }
            : chatMessage,
        ),
      );
    } finally {
      setChatSending(false);
    }
  }

  return (
    <Card className="border-blue-200 bg-blue-50/40">
      <CardHeader>
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div>
            <CardTitle>Right loop: remediation + chat harness</CardTitle>
            <CardDescription>
              One loop: the operator opens slash-command chat, oh-my-tiny-oran
              inspects the real harness, and the harness-walker AuditEvent
              remains the load-bearing evidence.
            </CardDescription>
          </div>
          <Badge
            variant={
              hasAssistantResponse
                ? "success"
                : approved
                  ? "default"
                  : "warning"
            }
          >
            {hasAssistantResponse
              ? "assistant response received"
              : approved
                ? "approval recorded"
                : "approval required before chat"}
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <RightLoopProofStrip />

        <div className="grid gap-2 md:grid-cols-4">
          <LoopStep number={1} title="Proposal" active />
          <LoopStep number={2} title="Human approval" active={approved} />
          <LoopStep
            number={3}
            title="chat command"
            active={chatMessages.length > 0 || chatInput.length > 0}
          />
          <LoopStep
            number={4}
            title="Production still blocked"
            active={hasAssistantResponse || Boolean(harnessAudit)}
          />
        </div>

        <div className="grid gap-4 lg:grid-cols-[0.8fr_1.2fr]">
          <Card className="bg-background shadow-none">
            <CardHeader>
              <CardTitle>Remediation proposal</CardTitle>
              <CardDescription>
                Standards-backed action prepared from the left-loop
                recommendation.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="rounded border bg-background p-3">
                <div className="text-xs uppercase text-muted-foreground">
                  remediation slice
                </div>
                <div className="mt-2 grid gap-2">
                  {RIGHT_LOOP_SCENARIOS.map((scenario) => (
                    <button
                      key={scenario.id}
                      type="button"
                      onClick={() => {
                        setSelectedScenarioId(scenario.id);
                        setHarnessAudit(null);
                        setEvidenceError(null);
                        setChatInput(scenario.prompt);
                      }}
                      className={
                        "rounded border p-2 text-left text-xs transition " +
                        (selectedScenarioId === scenario.id
                          ? "border-blue-400 bg-blue-50 text-blue-950"
                          : "bg-background hover:bg-muted")
                      }
                    >
                      <div className="flex flex-wrap items-center justify-between gap-2">
                        <span className="font-semibold">{scenario.label}</span>
                        <Badge
                          variant={
                            scenario.routeKind === "DOWN only"
                              ? "default"
                              : scenario.routeKind === "DOWN + UP"
                                ? "warning"
                                : "muted"
                          }
                        >
                          {scenario.routeKind}
                        </Badge>
                      </div>
                      <div className="mt-1 font-mono text-[10px] text-muted-foreground">
                        {scenario.id}
                      </div>
                      <div className="mt-0.5 text-muted-foreground">
                        {scenario.short}
                      </div>
                    </button>
                  ))}
                </div>
              </div>
              <div className="rounded border bg-background p-3">
                <div className="text-xs uppercase text-muted-foreground">
                  operator intent
                </div>
                <div className="mt-1 text-sm font-semibold">
                  {selectedScenario.intent}
                </div>
                <p className="mt-1 text-xs leading-5 text-muted-foreground">
                  Remove timing-sensitive workloads from the suspect node before
                  any production-impacting NIC/PHC follow-up. The right-loop
                  harness can inspect the committed AuditEvent, but production
                  action remains blocked behind operator control.
                </p>
              </div>
              <div className="rounded border bg-background p-3">
                <div className="text-xs uppercase text-muted-foreground">
                  actual harness target
                </div>
                <div className="mt-1 text-sm font-semibold">
                  {selectedScenarioId}
                </div>
                <p className="mt-1 text-xs leading-5 text-muted-foreground">
                  The assistant is prompted through `/oran-discover:*` slash
                  commands. When it inspects this scenario, the evidence drawer
                  can show the same live harness-walker AuditEvent as a sidecar.
                </p>
              </div>
              <div className="rounded border bg-background p-3">
                <div className="text-xs uppercase text-muted-foreground">
                  standards-backed path
                </div>
                <p className="mt-1 text-xs leading-5 text-muted-foreground">
                  {standardsMap.join(" · ")}
                </p>
              </div>
            </CardContent>
          </Card>

          <HarnessPanel
            title="oh-my-tiny-oran chat harness"
            description="Use slash commands, edit the prompt, press Enter, and inspect live harness evidence from the assistant turn."
          >
            <div className="space-y-4">
              <div className="rounded border bg-background p-3">
                <div className="flex flex-wrap items-start justify-between gap-2">
                  <div>
                    <div className="text-xs uppercase text-muted-foreground">
                      hard boundary
                    </div>
                    <div className="mt-1 font-semibold">
                      Human approval required before right-loop chat
                    </div>
                  </div>
                  {chatHealth && (
                    <Badge
                      variant={
                        chatHealth.anthropic_key_set ? "success" : "warning"
                      }
                    >
                      {chatHealth.anthropic_key_set
                        ? "oh-my-tiny-oran key set"
                        : "chat key not set"}
                    </Badge>
                  )}
                </div>
                <p className="mt-1 text-xs leading-5 text-muted-foreground">
                  The LLM can inspect and explain harness output. The
                  load-bearing evidence remains the harness-walker tool result,
                  and production action remains blocked behind operator control.
                </p>
              </div>

              <HarnessPathVisual
                scenarioId={selectedScenarioId}
                audit={harnessAudit}
              />

              <div className="flex flex-wrap gap-2">
                <Button
                  onClick={() => setApproved(true)}
                  className={
                    approved
                      ? "bg-green-600 text-white hover:bg-green-700"
                      : "bg-blue-600 text-white hover:bg-blue-700"
                  }
                >
                  {approved
                    ? "Human approval recorded"
                    : "Approve chat harness"}
                </Button>
                <Button
                  disabled={!approved || evidenceLoading}
                  onClick={() => attachEvidenceSidecar()}
                  className="bg-emerald-600 text-xs text-white hover:bg-emerald-700"
                >
                  {evidenceLoading
                    ? "Running harness..."
                    : "Run harness-walker sidecar"}
                </Button>
                {rightLoopCommands.map((command) => (
                  <Button
                    key={command.label}
                    disabled={!approved && command.prompt !== "/commands"}
                    onClick={() => setChatInput(command.prompt)}
                    className="text-xs"
                  >
                    {command.label}
                  </Button>
                ))}
              </div>

              {!approved && (
                <div className="rounded border bg-yellow-50 p-3 text-xs text-yellow-900">
                  Approve the proposal to enable the chat harness. You can still
                  inspect `/commands` to see available slash commands.
                </div>
              )}

              <div className="rounded border bg-background p-3">
                <div className="text-xs uppercase text-muted-foreground">
                  chat prompt
                </div>
                <form
                  className="mt-2 space-y-2"
                  onSubmit={(event) => {
                    event.preventDefault();
                    sendToRightLoopHarness(chatInput);
                  }}
                >
                  <textarea
                    value={chatInput}
                    onChange={(event) => setChatInput(event.target.value)}
                    onKeyDown={(event) => {
                      if (event.key === "Enter" && !event.shiftKey) {
                        event.preventDefault();
                        sendToRightLoopHarness(chatInput);
                      }
                    }}
                    placeholder="Type /commands or choose a preset, then press Enter..."
                    className="min-h-20 w-full rounded border bg-background p-2 text-xs font-mono"
                    disabled={chatSending}
                  />
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-[10px] text-muted-foreground">
                      Enter sends · Shift+Enter adds a line
                    </span>
                    <Button
                      type="submit"
                      disabled={chatSending || !chatInput.trim()}
                      className="bg-blue-600 text-white hover:bg-blue-700"
                    >
                      {chatSending
                        ? "oh-my-tiny-oran is inspecting..."
                        : "Send"}
                    </Button>
                  </div>
                </form>
              </div>

              {chatMessages.length > 0 && (
                <div className="max-h-96 space-y-2 overflow-y-auto rounded border bg-muted p-3">
                  {chatMessages.map((message) => (
                    <div
                      key={message.id}
                      className={
                        message.role === "user" ? "text-right" : "text-left"
                      }
                    >
                      <div
                        className={
                          "inline-block max-w-full whitespace-pre-wrap rounded px-3 py-2 text-xs font-mono " +
                          (message.role === "user"
                            ? "bg-blue-600 text-white"
                            : message.role === "system"
                              ? "border border-yellow-200 bg-yellow-50 text-yellow-900"
                              : message.pending
                                ? "border border-blue-200 bg-blue-50 text-blue-900"
                                : "border bg-background")
                        }
                      >
                        {message.content || "(no content)"}
                      </div>
                      {message.meta && (
                        <div className="mt-1 flex flex-wrap gap-1 text-[10px] text-muted-foreground">
                          <Badge variant="muted">
                            {message.meta.latency_s}s
                          </Badge>
                          <Badge variant="muted">
                            in {message.meta.input_tokens}
                          </Badge>
                          <Badge variant="muted">
                            out {message.meta.output_tokens}
                          </Badge>
                          {message.meta.skill_invoked && (
                            <Badge variant="default">
                              {message.meta.skill_invoked}
                            </Badge>
                          )}
                          {message.meta.tool_uses.length > 0 && (
                            <Badge variant="warning">
                              {message.meta.tool_uses.length} tool calls
                            </Badge>
                          )}
                        </div>
                      )}
                      {message.meta && message.meta.tool_uses.length > 0 && (
                        <ul className="mt-1 space-y-0.5 text-left font-mono text-[10px] text-muted-foreground">
                          {message.meta.tool_uses.map((toolUse, index) => (
                            <li key={index}>
                              <span className="text-primary">
                                {toolUse.name}
                              </span>
                              ({JSON.stringify(toolUse.input)})
                            </li>
                          ))}
                        </ul>
                      )}
                    </div>
                  ))}
                </div>
              )}

              {chatError && (
                <div className="rounded border border-yellow-200 bg-yellow-50 p-3 text-xs text-yellow-900">
                  {chatError}
                </div>
              )}
              {evidenceLoading && (
                <div className="rounded border border-blue-200 bg-blue-50 p-3 text-xs text-blue-900">
                  Attaching live evidence sidecar from harness-walker...
                </div>
              )}
              {evidenceError && (
                <div className="rounded border border-yellow-200 bg-yellow-50 p-3 text-xs text-yellow-900">
                  {evidenceError}
                </div>
              )}
              {harnessAudit && <HarnessRunSummary audit={harnessAudit} />}
            </div>
          </HarnessPanel>
        </div>
      </CardContent>
    </Card>
  );
}

export function TwoLoopDemo() {
  const [loop, setLoop] = useState("left");

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <CardTitle>Simple two-loop harness demo</CardTitle>
              <CardDescription>
                Left loop is alert + harness. Right loop is remediation +
                harness connected to stubbed O-RAN endpoints. The harness is
                visible and load-bearing in both.
              </CardDescription>
            </div>
            <div className="flex flex-wrap gap-2">
              <Badge variant="default">harness in both loops</Badge>
              <Badge variant="warning">human approval gate</Badge>
              <Badge variant="muted">LLM not load-bearing</Badge>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <p className="text-sm leading-6 text-muted-foreground">
            The left loop shows the PTP drift alert and the harness
            investigation that turns evidence into a NIC/PHC recommendation. The
            right loop shows how that recommendation becomes a governed
            remediation: D routes down through O2 IMS to KMM, while E shows the
            firmware dual-route through O2 IMS to Metal3/Redfish and up to SMO
            through TMF921. The endpoints are stubs; router, taxonomy,
            guardrails, sandbox, and AuditEvent wiring are the real harness.
          </p>
        </CardContent>
      </Card>

      <Tabs value={loop} onValueChange={setLoop}>
        <TabsList>
          <TabsTrigger value="left">Left loop - alert + harness</TabsTrigger>
          <TabsTrigger value="right">
            Right loop - remediation + harness
          </TabsTrigger>
        </TabsList>
        <TabsContent value="left">
          <LeftLoop />
        </TabsContent>
        <TabsContent value="right">
          <RightLoop />
        </TabsContent>
      </Tabs>
    </div>
  );
}
