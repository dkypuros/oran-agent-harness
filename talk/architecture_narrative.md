---
title: "Architecture Narrative: Observation Loop, Cognitive Middle, Routing, Sandbox"
author: David Kypuros
venue: O-RAN nGRG Workshop, Seattle
date: 4th [THU] JUN 2026
license: Apache-2.0
status: plain-prose companion to talk/abstract.md and talk/architecture.mmd
---

# Architecture Narrative: Observation Loop, Cognitive Middle, Routing, Sandbox

This document is the plain-prose walkthrough of the harness pattern described in `talk/abstract.md` and
diagrammed in `talk/architecture.mmd` (v3). The dense Mermaid diagram shows every component and edge;
this document tells you how to read it. Four pieces in order: an observation loop on the left, a
cognitive middle in the harness, a routing decision that splits into a high side and a low side, and a
sandbox that runs before any live action.

## What is novel here, in one paragraph

The right-side execution path is the contribution. It grounds infrastructure remediation in two
standardized contracts simultaneously. Above, the O-RAN O2 IMS interface
([O-RAN.WG6 O2 General Aspects and Principles, ref 2](../docs/references.md#ref-2);
[O-RAN.WG6 O2 IMS Interface Specification, ref 3](../docs/references.md#ref-3)) gives the
SMO-to-O-Cloud API a specification surface. Below, the actual delivery happens through CRD-shaped
contracts that already run in production O-Cloud deployments:
[Metal3 BareMetalHost / HostFirmwareComponents (ref 8)](../docs/references.md#ref-8) for node
firmware, and the [Machine Config Operator (ref 9)](../docs/references.md#ref-9) for host
configuration. Most published agentic-RAN work either stops at the SMO boundary without a delivery
story, or proposes a custom controller plane that side-steps O-RAN's own resource layering. The
2+3+8+9 conjunction is what lets a single RemediationProposal travel from the cognitive layer
through a standardized O-RAN interface into a concrete Kubernetes-native contract. Layered on top
of that conjunction, the Remediation Router classifies first by deterministic taxonomy lookup
against the O-RAN WG6 O-Cloud resource model and invokes LLM reasoning only on the residual
`ambiguous` class. The rest of this document walks the four pieces (left loop, cognitive middle,
routing decision, sandbox plus operator seam) in that order.

## 1. The observation loop (the left side of the diagram)

The PTP sync alarm format is a standards stack. The Red Hat PTP Operator
([ref 28](../docs/references.md#ref-28)) runs the linuxptp daemon
([ref 27](../docs/references.md#ref-27)) on each node and the cloud-event-proxy sidecar
([ref 29](../docs/references.md#ref-29)) publishes CloudEvents
([ref 30](../docs/references.md#ref-30)) carrying the
O-RAN.WG6 O-Cloud Notification API payload
([ref 31](../docs/references.md#ref-31)). The PTP state machine itself
([IEEE 1588-2019, ref 26](../docs/references.md#ref-26)) defines the
SYNCHRONIZED / HOLDOVER / FREE_RUNNING / UNCALIBRATED transitions; the
G.8275.1 telecom profile ([ref 44](../docs/references.md#ref-44)) is the
full-timing-support shape Cloud RAN deployments use. Scenario D
(`scenarios/D_phc_drift_hw_only/`) shows the divergence pattern: ptp4l
reports SYNCHRONIZED (software view OK) while phc2sys reports monotonic PPB
drift AND the NIC reports rising tx_hwtstamp_timeouts (hardware view NOT
OK). Each stage of the harness pipeline appends one JSON record to the
shared trace layer at `5G_O-RAN_SIM/shared_trace/{scenario_id}.jsonl` for
post-run replay analysis.

PTP synchronization on a Cloud RAN site flows downward from a GNSS source disciplining a PTP
Grandmaster (T-GM, profile [G.8275.1](../docs/references.md#ref-44)), optionally through a Boundary Clock, and into the worker node's
NIC, where the PTP Hardware Clock (PHC) handles hardware timestamping. On the host, the [linuxptp](../docs/references.md#ref-27)
daemon (`ptp4l` plus `phc2sys`) runs as an Ordinary or Boundary Clock and disciplines the system clock
to the network's time source. The vDU consumes that timing via `clock_gettime(CLOCK_TAI)`.

When PTP starts to drift, the [cloud-event-proxy](../docs/references.md#ref-29) sidecar observes the linuxptp state transitions
(LOCKED, UNCALIBRATED, FREE_RUNNING, master offset spikes, PHC frequency drift in parts per billion)
and publishes O-RAN CloudEvents conforming to [O-RAN.WG6 Cloud Notifications](../docs/references.md#ref-31) on top of
[CNCF CloudEvents 1.0](../docs/references.md#ref-30). Those events are the empirical evidence that something is wrong. They are the inbound
contract the harness reads. The schema each event populates is `harness/schemas/FaultPayload.json`.

## 2. The cognitive middle (the harness itself)

The Agentic Gateway terminates the CloudEvents stream and exposes vendor-private tooling under
controlled MCP interfaces (mTLS, OAuth2, IP allowlist). Three [FastMCP](../docs/references.md#ref-15) servers run behind the gateway:
mcp-platform (linuxptp, host services, driver versions, NIC stats), mcp-ran (cell sync, PM counters,
RAN parameters), and mcp-hardware (NIC PHC introspection, [BMC Redfish](../docs/references.md#ref-46), CPU performance counters). A
fourth, mcp-ocloud, surfaces the [O-Cloud Manager](../docs/references.md#ref-6) Inventory and Alarms.

A telemetry-boundary note. The data these MCP servers consume (linuxptp daemon state, MachineConfig
pool status, KMM Module load state, kernel driver versions, NIC PHC counters) is O-Cloud-internal
platform telemetry. It is NOT governed by O-RAN O1 ([ref 49](../docs/references.md#ref-49)), which standardizes
SMO-to-managed-element OAM where managed elements are O-CU, O-DU, and O-RU. The O-Cloud platform
layer sits below the managed-element boundary; how it surfaces its own state to local consumers
is implementation specific. The standardized SMO-facing flow downstream of the harness IS
spec-governed: the guardrail engine emits a [TMF688](../docs/references.md#ref-18) AuditEvent and the O-Cloud Manager exposes
alarms via the O2 IMS AlarmEventRecord (O2IMS-INTERFACE R005-v11 Section 3.3.6.2.2,
[ref 3](../docs/references.md#ref-3)). MCP servers and O1 do not overlap.

Three domain agents (Platform, RAN, Hardware) consult those servers and a shared Knowledge Base (RAG,
mapped to [TMF GB922 SID](../docs/references.md#ref-22) for telecom context). Each agent produces structured findings that converge
into a Root Cause Analysis artifact (`harness/schemas/RCA.json`). The Remediation Router consults
`harness/taxonomy.yaml` first: a deterministic lookup against the O-RAN WG6 O-Cloud resource model
that produces an unambiguous classification for the great majority of faults. LLM reasoning is invoked
only when the taxonomy resolves to the `ambiguous` layer. The single most research-credible move in
this design is right there: the routing decision is grounded in O-RAN's own resource layering, not in
a model's opinion.

All of this sits on top of the Digital Twin substrate (visible in
`talk/architecture_zoom_cognitive.mmd` as the wide horizontal foundation at the bottom). The twin is
not a service the cognitive layer calls into. It is the floor the cognitive layer stands on. EvalOps
runs continuously between the twin and the agents (dashed bidirectional arrows in the zoom diagram),
producing the confidence telemetry that travels with every RemediationProposal. Sandbox is a
forward-direction test flight on the twin; Agentic Recoverability is the inverse-action validation
on the twin. Both flow back UP into the Proposal artifact before it leaves the cognitive layer.

## 3. The routing decision (right side, high vs low)

`harness/routing-rules/contribution-1-routing-rule.yaml` declares the rule. The harness splits actions
by O-RAN resource layer:

**High side, service-layer.** Cell re-home, RAN parameter changes, slice intent updates, vDU software
version rollouts. These belong to the partner SMO (Ericsson, Amdocs, Nokia, Mavenir, ZTE). The harness
does not execute them. It emits a [TMF921](../docs/references.md#ref-19) intent and observes the result. This is the harness's
respect for the service-execution boundary.

**Low side, infrastructure-layer.** Host configuration via [MachineConfig](../docs/references.md#ref-9) (delivered by the Machine
Config Operator), driver swaps via [KMM Module](../docs/references.md#ref-10) CRs (delivered by the Kernel Module Management
Operator), node firmware via [Metal3](../docs/references.md#ref-7) HostFirmwareComponents, PerformanceProfile updates via the Node
Tuning Operator, SR-IOV reconfiguration. Every one of these flows into the O-Cloud via the O-RAN O2
IMS API. Red Hat's open-source O-Cloud Manager (`openshift-kni/oran-o2ims`) is the reference O2 IMS
implementation cited in this work.

The routing rule fires the LOW branch alone for most infra remediations, but a higher-blast
case forces both branches in parallel. Scenario E (`scenarios/E_nic_firmware_update/`) shows
this dual-route pattern: an NIC firmware update via Metal3 ([ref 7](../docs/references.md#ref-7))
takes the host offline for a reboot window, so the harness emits a TMF921 companion intent
([ref 19](../docs/references.md#ref-19)) UP to the partner SMO in parallel with the DOWN-route
O2 IMS apply ([ref 3](../docs/references.md#ref-3)). The Metal3 Baremetal Operator
([ref 8](../docs/references.md#ref-8)) drives the apply; under the hood the BMC handles the
firmware write via DMTF Redfish DSP0266 UpdateService.SimpleUpdate
([ref 46](../docs/references.md#ref-46)). The closing TMF688 audit
([ref 18](../docs/references.md#ref-18)) carries the elevated blast radius
(nodes:1, sites:1, cells:4) reflecting the maintenance window. The dual-route companion intent
fires for any node_firmware action regardless of cell count, because firmware reboots require
SMO coordination by their semantic, not just their blast magnitude. This dual-route pattern is
the teaching moment Scenarios A and A-prime cannot show.

The two walkthrough scenarios both demonstrate the LOW branch through different internal delivery
mechanisms. Scenario A masks a host systemd service via MachineConfig (MCO path). Scenario A-prime
swaps an in-tree kernel module for an out-of-tree build via a KMM Module CR (KMM path). Same routing
decision, two execution paths. That contrast is the architectural teaching point of the talk.

## 4. The sandbox and the human-in-the-loop seam

Before any RemediationProposal becomes a live action, the Guardrail engine
(`harness/guardrails.yaml`) gates it deterministically: dry-run default, blast-radius caps (max one
node, one site, four cells in v0), action allowlist, operator-harness co-authorization. Co-authorship
is the deliberate framing: the harness drafts; the operator edits and commits. Not discrete HITL
approve/reject.

The proposal is then exercised against the Digital Twin substrate, a same-topology mirrored cluster
(or a simulated linuxptp plus NIC driver stack) that supports three concurrent activities: the
Sandbox runs the forward-direction action to verify it lands cleanly, EvalOps measures the agents'
historical accuracy on this scenario class, and Agentic Recoverability validates that the inverse
action will land if the operator needs to walk this back. Only twins that converge inside the
expected envelope on all three produce the apply-allowed signal. This is the two-key gate: the
operator authorizes the action class, the twin authorizes the specific payload. Full discussion in
`talk/trust_loop.md` (the twin is the substrate; the three activities run on top of it under the
explicit banner of Intelligence Augmentation).

What the operator finally sees is a [TMF688](../docs/references.md#ref-18)-shaped AuditEvent (`harness/schemas/AuditEvent.json`)
carrying the proposed action plus a populated ReversibilityProfile
(`harness/schemas/ReversibilityProfile.json`): rollback intent, blast radius if reverse, rebuild
timeline, replication history, validation history, risk profile burn-down, and confidence in
reversibility. Seven fields, same place every time, same shape every time. That is the contract
between the harness and the human in the loop.

One more contract sits above the per-action seam: the Killswitch (formal name crisis_mode in
guardrails.yaml, full discussion in `talk/killswitch.md`). It is the global override for macro
events (hurricanes, tornadoes, lightning storms, security incidents) where the harness's normal
pattern matching would actively fight a degraded physical world. When activated by a NOC supervisor,
crisis_mode revokes write access to O2 IMS and the SMO, pins EvalOps confidence at zero, and routes
telemetry to manual human queues. The ReversibilityProfile rewinds one applied action; the
Killswitch freezes all of them. The two compose; they answer different questions.

## 5. Where this lives in the SMO architecture

The harness operates within the scope of the SMO. Specifically, it corresponds to a candidate
Closed-Loop Remediation SMOS (SMO Service) per O-RAN.WG1.TR.Decoupled-SMO-Architecture
(R004-v03.00) ([ref 48](../docs/references.md#ref-48)). The infra route terminates at the O2 IMS
ProvisioningRequest service per O-RAN.WG6.TS.O2IMS-INTERFACE-R005-v11 Section 3.4
([ref 3](../docs/references.md#ref-3)). In a production deployment, the harness's ProvisioningRequests would be
submitted through FOCOM (Federated O-Cloud Orchestration and Management), the SMO function that
consumes O2 IMS for infrastructure management per O-RAN.WG6.O2-GAnP-v01.02 Section 2.2
(Figure 2.2-2: IMS managed by FOCOM, DMS consumed by NFO; [ref 2](../docs/references.md#ref-2)). FOCOM is not
bypassed by this harness; the harness acts as a candidate orchestrator that FOCOM (or the SMO
equivalent) composes into its workflow.

Three layers operate at distinct abstractions. The O-RAN management-plane interfaces
(O1 [ref 49](../docs/references.md#ref-49), A1 [ref 50](../docs/references.md#ref-50),
R1 [ref 51](../docs/references.md#ref-51), E2 [ref 52](../docs/references.md#ref-52),
O2 [ref 3](../docs/references.md#ref-3))
standardize how the SMO interacts with managed elements, the Near-RT RIC, rApps, and the
O-Cloud. MCP (Anthropic Model Context Protocol, [ref 13](../docs/references.md#ref-13)) is a
separate, lower-layer protocol the harness uses to orchestrate its internal LLM agents. MCP does
not replace, bypass, or compete with the O-RAN interfaces; it composes at a different layer.
An rApp realization of this harness pattern would use MCP internally and expose its capabilities
via R1 to the rest of the SMO.

A1 policies ([ref 50](../docs/references.md#ref-50)) target Near-RT RIC behavior (traffic
steering, QoS optimization, slice SLAs). This harness targets infrastructure remediation (host
configuration, kernel drivers, firmware) via the O2 IMS interface
([ref 3](../docs/references.md#ref-3)), which is a different layer of the architecture. The
two compose; they do not compete.

## 6. The 5G platform substrate

This repository ships its own 5G O-RAN simulator at `5G_O-RAN_SIM/` (re-licensed Apache 2.0,
copied wholesale from the author's BF3-5G-Demo project). The simulator is the platform
substrate (SMO, CU/DU, O-Cloud, Open Fronthaul O-RU, Near-RT RIC, Non-RT RIC, OAM, Security)
that the agentic harness operates on top of. Together they form the full closed-loop demo
stack:

- The simulator at `5G_O-RAN_SIM/` provides 13 O-RAN service implementations across WG1, WG2,
  WG3, WG4, WG6, WG9, WG10, and WG11; an aggregation gateway on port 8088; a React dashboard;
  and a 14/14 O-RAN compliance test suite that validates 47 specs against the running services.
- The harness pattern at `harness/` provides the closed-loop intelligence: Agentic Gateway,
  MCP servers, Domain Agents, Router (with ambiguous_path now wired to live LLM-assist), the
  Guardrail engine, and TMF688 audit emission.
- The LLM inference layer at `5G_O-RAN_SIM/llm/` provides a unified `completion()` client and
  a fake OpenShift AI vLLM mock server on port 8090. Anthropic Claude and OpenAI GPT are
  configurable in `5G_O-RAN_SIM/.env` (template at `.env.example`). The default is the local
  vLLM mock so the demo runs without external network calls.

The integration seam is at `harness/runtime/router.py` `_resolve_ambiguous()`: when the
`ORAN_LLM_MODE=live` environment variable is set, the router calls the inference client with
a disambiguation prompt built from the RCA's candidate classifications. The seam is exercised
end-to-end (the LLM hint appears in the router's NotImplementedError message); the router
does not auto-parse the response into a deterministic classification in v0. Default behavior
(env var unset) preserves the historical `NotImplementedError` so the existing verify gate at
10/10 PASS and the unit test `test_route_ambiguous_raises` remain unaffected. This is the
live realization of Contribution 3 (LLM-neutral substrate). Trace logs accumulate at
`5G_O-RAN_SIM/llm/mock_traces.jsonl` (gitignored) for replay analysis as the p2p sync
troubleshooting work unfolds.

## How to read this repo's diagrams

The repo ships one macro diagram plus three zoom diagrams. Read them in this order based on what
you want to understand:

| Diagram                                | When to open                                                                          |
|----------------------------------------|----------------------------------------------------------------------------------------|
| `talk/architecture.mmd`                | FIRST. The macro / billboard. Seven boxes only: Observation on the left, Agent Harness in the middle with the Human Operator co-present and the Digital Twin substrate beneath, Killswitch as an override badge, and the right side forked into UP (TMF921 to SMO) and DOWN (O2 IMS to O-Cloud). Read this in 30 seconds; everything else is a double-click. |
| `talk/architecture_zoom_governance.mmd`| Open when reading section 4 of this narrative. TM Forum governance, TMF688 audit, ReversibilityProfile, co-authorization, and the Killswitch (crisis_mode) all live here. Pairs with `talk/trust_loop.md` and `talk/killswitch.md`. |
| `talk/architecture_zoom_cognitive.mmd` | Open when reading section 2 of this narrative. Agentic Gateway, four MCP servers, three domain agents, the deterministic Router and taxonomy, the LLM-neutral substrate, plus the Digital Twin substrate with EvalOps, Sandbox, and Agentic Recoverability as activities on it. Pairs with `talk/trust_loop.md`. |
| `talk/architecture_zoom_ocloud.mmd`    | Open when reading section 3 of this narrative (low side). Hub cluster O-Cloud, ACM, all seven spoke operators (MCO, KMM, PTP, NTO, Metal3, SR-IOV, NFD), and the worker node with linuxptp, cloud-event-proxy, kernel driver, fw-lldp-agent, Intel E810 NIC, BMC. Where Scenario A and Scenario A-prime actually execute. |
| `talk/sequence_anomaly_lifecycle.mmd`  | Open when you want to see the TEMPORAL flow of a PTP anomaly from CloudEvent detection through twin-validated remediation to operator commit to apply call. The operator step is visibly the bottleneck. Shows that the human is the gatekeeper in the timeline. |
| `talk/sequence_agentic_recovery.mmd`   | Open when you want to see the UNDO sequence. Operator decides 30 minutes after the apply that the fix produced unintended side effects and walks it back. Surgical, per-action, no full failover. Makes the Agentic Recoverability vs Disaster Recovery distinction visual. |
| `talk/state_crisis_mode.mmd`           | Open when you want to see the Killswitch state transitions. Normal Ops to Crisis Activation Pending to Crisis Mode Active to Crisis Deactivation Pending to Recovery Drill back to Normal Ops. Each state annotated with concrete effects per guardrails.yaml crisis_mode. The answer for the AT&T operations team question. |
| `talk/architecture_full.mmd`           | LAST. The comprehensive 30+ component reference (formerly architecture v3). Open this when you want every component visible at once on a single canvas (12K wide PNG). Not the entry point; a deep-dive aid. |

The three behavioral views above (two sequence diagrams plus the crisis_mode state transition) round
out the diagram set. Together with the macro and the three topological zooms, they give the audience
a complete view: WHERE things live (macro + zooms), HOW they move (sequences), and HOW the system
behaves under duress (state).

## Where to look for detail

- Macro architecture diagram source: `talk/architecture.mmd` (open as text or render with mermaid-cli)
- Zoom diagrams: `talk/architecture_zoom_governance.mmd`, `talk/architecture_zoom_cognitive.mmd`, `talk/architecture_zoom_ocloud.mmd`
- Routing rule, declarative form: `harness/routing-rules/contribution-1-routing-rule.yaml`
- Guardrail contract: `harness/routing-rules/contribution-2-guardrail-contract.yaml` plus `harness/guardrails.yaml`
- LLM-neutrality assertion: `harness/routing-rules/contribution-3-llm-neutrality.yaml`
- Trust loop (Digital Twin substrate plus EvalOps, Sandbox, Agentic Recoverability, plus IA principle): `talk/trust_loop.md`
- Killswitch (crisis_mode global override): `talk/killswitch.md`
- ODA Canvas reference mapping: `talk/oda_mapping.md`
- Citation index for every authored file: `harness/conformance.md`
- Bibliography (numbered AMA refs): `docs/references.md`
