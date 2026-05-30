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

## 1. The observation loop (the left side of the diagram)

PTP synchronization on a Cloud RAN site flows downward from a GNSS source disciplining a PTP
Grandmaster (T-GM, profile G.8275.1), optionally through a Boundary Clock, and into the worker node's
NIC, where the PTP Hardware Clock (PHC) handles hardware timestamping. On the host, the linuxptp
daemon (`ptp4l` plus `phc2sys`) runs as an Ordinary or Boundary Clock and disciplines the system clock
to the network's time source. The vDU consumes that timing via `clock_gettime(CLOCK_TAI)`.

When PTP starts to drift, the cloud-event-proxy sidecar observes the linuxptp state transitions
(LOCKED, UNCALIBRATED, FREE_RUNNING, master offset spikes, PHC frequency drift in parts per billion)
and publishes O-RAN CloudEvents conforming to O-RAN.WG6 Cloud Notifications on top of CNCF
CloudEvents 1.0. Those events are the empirical evidence that something is wrong. They are the inbound
contract the harness reads. The schema each event populates is `harness/schemas/FaultPayload.json`.

## 2. The cognitive middle (the harness itself)

The Agentic Gateway terminates the CloudEvents stream and exposes vendor-private tooling under
controlled MCP interfaces (mTLS, OAuth2, IP allowlist). Three FastMCP servers run behind the gateway:
mcp-platform (linuxptp, host services, driver versions, NIC stats), mcp-ran (cell sync, PM counters,
RAN parameters), and mcp-hardware (NIC PHC introspection, BMC Redfish, CPU performance counters). A
fourth, mcp-ocloud, surfaces the O-Cloud Manager Inventory and Alarms.

Three domain agents (Platform, RAN, Hardware) consult those servers and a shared Knowledge Base (RAG,
mapped to TMF GB922 SID for telecom context). Each agent produces structured findings that converge
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
does not execute them. It emits a TMF921 intent and observes the result. This is the harness's
respect for the service-execution boundary.

**Low side, infrastructure-layer.** Host configuration via MachineConfig (delivered by the Machine
Config Operator), driver swaps via KMM Module CRs (delivered by the Kernel Module Management
Operator), node firmware via Metal3 HostFirmwareComponents, PerformanceProfile updates via the Node
Tuning Operator, SR-IOV reconfiguration. Every one of these flows into the O-Cloud via the O-RAN O2
IMS API. Red Hat's open-source O-Cloud Manager (`openshift-kni/oran-o2ims`) is the reference O2 IMS
implementation cited in this work.

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

What the operator finally sees is a TMF688-shaped AuditEvent (`harness/schemas/AuditEvent.json`)
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

## How to read this repo's diagrams

The repo ships one macro diagram plus three zoom diagrams. Read them in this order based on what
you want to understand:

| Diagram                                | When to open                                                                          |
|----------------------------------------|----------------------------------------------------------------------------------------|
| `talk/architecture.mmd`                | FIRST. The macro / billboard. Seven boxes only: Observation on the left, Agent Harness in the middle with the Human Operator co-present and the Digital Twin substrate beneath, Killswitch as an override badge, and the right side forked into UP (TMF921 to SMO) and DOWN (O2 IMS to O-Cloud). Read this in 30 seconds; everything else is a double-click. |
| `talk/architecture_zoom_governance.mmd`| Open when reading section 4 of this narrative. TM Forum governance, TMF688 audit, ReversibilityProfile, co-authorization, and the Killswitch (crisis_mode) all live here. Pairs with `talk/trust_loop.md` and `talk/killswitch.md`. |
| `talk/architecture_zoom_cognitive.mmd` | Open when reading section 2 of this narrative. Agentic Gateway, four MCP servers, three domain agents, the deterministic Router and taxonomy, the LLM-neutral substrate, plus the Digital Twin substrate with EvalOps, Sandbox, and Agentic Recoverability as activities on it. Pairs with `talk/trust_loop.md`. |
| `talk/architecture_zoom_ocloud.mmd`    | Open when reading section 3 of this narrative (low side). Hub cluster O-Cloud, ACM, all seven spoke operators (MCO, KMM, PTP, NTO, Metal3, SR-IOV, NFD), and the worker node with linuxptp, cloud-event-proxy, kernel driver, fw-lldp-agent, Intel E810 NIC, BMC. Where Scenario A and Scenario A-prime actually execute. |
| `talk/architecture_full.mmd`           | LAST. The comprehensive 30+ component reference (formerly architecture v3). Open this when you want every component visible at once on a single canvas (12K wide PNG). Not the entry point; a deep-dive aid. |

Sequence diagrams (a day in the life of a PTP anomaly; the agentic recovery undo sequence) and the
crisis_mode state-transition diagram are deferred to v0.2 (see follow-up GitHub issues). The macro
plus three zooms above are sufficient for the v0 talk.

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
- Bibliography (47 numbered AMA refs): `references.md`
