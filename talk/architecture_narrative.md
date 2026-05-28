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

The proposal is then run against a digital-twin sandbox, a same-topology test cluster (or a simulated
linuxptp plus NIC driver stack) that receives the same MachineConfig or Module CR the harness would
apply live. The harness observes the twin's PTP state, NIC counters, and pod readiness after a settle
interval. Only twins that converge inside the expected envelope produce the apply-allowed signal.
This is the two-key gate: the operator authorizes the action class, the sandbox authorizes the
specific payload. Full discussion in `talk/trust_loop.md` (Pillar 2).

What the operator finally sees is a TMF688-shaped AuditEvent (`harness/schemas/AuditEvent.json`)
carrying the proposed action plus a populated ReversibilityProfile
(`harness/schemas/ReversibilityProfile.json`): rollback intent, blast radius if reverse, rebuild
timeline, replication history, validation history, risk profile burn-down, and confidence in
reversibility. Seven fields, same place every time, same shape every time. That is the contract
between the harness and the human in the loop.

## Where to look for detail

- Architecture diagram source: `talk/architecture.mmd` (open as text or render with mermaid-cli)
- Routing rule, declarative form: `harness/routing-rules/contribution-1-routing-rule.yaml`
- Guardrail contract: `harness/routing-rules/contribution-2-guardrail-contract.yaml` plus `harness/guardrails.yaml`
- LLM-neutrality assertion: `harness/routing-rules/contribution-3-llm-neutrality.yaml`
- Trust loop (EvalOps + sandbox + reversibility): `talk/trust_loop.md`
- ODA Canvas reference mapping: `talk/oda_mapping.md`
- Citation index for every authored file: `harness/conformance.md`
- Bibliography (43 numbered AMA refs): `references.md`
