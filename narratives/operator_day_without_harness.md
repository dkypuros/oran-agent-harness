---
title: "A multivendor diagnosis day without the harness"
author: David Kypuros
license: Apache-2.0
status: the "From" half of the talk title made concrete, audience-hook narrative
audience: operations engineers, SREs, day-2 leads, anyone who has run a multivendor cell site
---

# A multivendor diagnosis day without the harness

The talk is titled *From Multivendor Diagnosis to Closed-Loop Remediation*. The "From" half
is the day that exists today. It is the day this work is built to retire. Until the reader
has the texture of that day in mind, the architecture pages read as abstract. This narrative
gives the texture.

## 09:14 local time, a Tuesday in 2026

The on-call NOC engineer at a Tier-1 operator gets a PagerDuty alert. The alert title says
"PTP holdover at site X12, two cells degraded, voice-quality SLI dropping." Two cells means
roughly 480 connected handsets right now, but the SLA penalty math is what matters: the cells
fall outside the contracted four-nines window inside seven minutes if the cause is not
identified.

The site is a multivendor build. The vDU is one vendor (call them Vendor A). The radios are a
different vendor. The cell site router is a third. The host platform is OpenShift on Dell
hardware. The PTP grandmaster is a Microchip box. Most days nothing crosses a vendor boundary;
today something has.

## The five consoles

The on-call engineer pulls up the consoles in this order. Each one shows part of the truth.

  1. **Splunk**. Search query for PTP-related events at site X12 in the last 30 minutes. Returns
     420 hits, dominated by linuxptp daemon transitions on three worker nodes. The console says
     `ptp4l[12431]: master offset spike at 09:11:43, then nominal again at 09:12:01`. So PTP did
     recover. Good. Why are the cells still degraded?

  2. **Vendor A EMS**. The vDU vendor's element manager. The vDU reports cell sync alarm,
     severity major. The vDU was holding cell timing from PHC, the PHC was holding from PTP,
     PTP recovered, but the vDU has not. Vendor A's recommendation: open a ticket, restart the
     vDU.

  3. **Red Hat ACM**. The cluster manager. The worker nodes look healthy. CPU, memory,
     scheduling all green. MachineConfig pool is in a steady state. No node has rebooted.

  4. **Grafana, host platform board**. The NIC tx_hwtstamp_timeouts counter on one of the three
     worker nodes is climbing. It was zero an hour ago, it is 4,200 now. The PHC frequency
     adjustment graph for the same node is sawtoothing. The other two worker nodes look normal.

  5. **Vendor A again, this time the radio EMS**. The radios are happy. Connected handsets are
     attached. Beam patterns are normal.

The engineer now has five partial truths. PTP recovered (Splunk). The vDU is still alarmed
(Vendor A EMS). The cluster is fine (ACM). The NIC on one node is misbehaving (Grafana). The
radios are unaffected (Vendor A radio EMS). The cause is somewhere in the gap between consoles
2 and 4: the vDU thinks PTP is bad, but the linuxptp daemon says it is fine, except on one node
where the hardware-timestamping path is degrading.

## The vendor boundary

This is where day-2 in 2026 gets hard. The PHC lives on a NIC. The NIC is silicon. The driver
is Linux-kernel code. The driver delivers PTP hardware timestamps to linuxptp. If the NIC's
PHC is drifting under the daemon, the daemon's reported state is technically correct but
operationally lying. The on-call engineer has to know to look at
`/sys/class/net/<dev>/device/ptp/ptp*/frequency`, has to know that `ethtool -T <dev>` exposes
the timestamping capability, has to know that the Red Hat PTP Operator drives linuxptp via a
PtpConfig CR, has to know that the NIC driver in question (ice 1.11.x for an Intel E810) has a
known issue per Intel's driver release notes.

The engineer does not know all of this. The on-call rotation is shared by seven engineers
across two time zones. The one who knows the ice driver story by heart is in Singapore and
asleep. The runbook is six clicks deep in Confluence and last updated in 2025.

So the engineer opens a Jira ticket. Severity 2. Assigns to the host platform team. The host
platform team is on a different shift schedule. They acknowledge the ticket in 18 minutes. By
that time the cells have crossed the SLA threshold. The operator's customer-side commercial
team is also now paged.

The vDU vendor is meanwhile asked to look at the cell sync alarm. They say "PTP." The host
platform team says "the host is fine, look at PTP." Both are technically saying the right thing,
but ownership is ambiguous because the cause is the firmware-driver-PHC boundary, which has no
single vendor on it.

By the time someone identifies the root cause and proposes the fix (downgrade ice driver to
1.10.x via a KMM Module CR, or apply the upstream patch via a MachineConfig), 47 minutes have
elapsed. The SLA window is gone. The customer escalation is open. Three vendors are on a
bridge call. The fix itself takes nine minutes to land once anybody decides who is allowed to
land it.

## Where the harness lives in this story

The harness does not eliminate the firmware-driver-PHC ambiguity. The ambiguity is real and
will continue to exist as long as multivendor cell sites exist. What the harness does is take
the diagnosis-to-action path off the human's critical path.

When the same PagerDuty alarm fires:

  1. The cloud-event-proxy sidecar on each worker node publishes the linuxptp state transitions
     as O-RAN CloudEvents (per `docs/references.md#ref-29`,
     `docs/references.md#ref-31`).

  2. The Agentic Gateway terminates the CloudEvents stream and produces a FaultPayload (schema
     at `harness/schemas/FaultPayload.json`).

  3. The three domain agents walk the evidence chain. The Hardware Agent reads the NIC PHC
     introspection via the mcp-hardware MCP server and surfaces the `tx_hwtstamp_timeouts`
     climb. The Platform Agent reads the linuxptp daemon state via mcp-platform and sees the
     daemon says SYNCHRONIZED. The divergence is now explicit in the RCA artifact, not buried
     in two consoles.

  4. The Remediation Router looks up the taxonomy. The fault pattern
     `phc_drift_with_software_locked_reporting` resolves to `target_layer: hardware` with high
     confidence. Deterministic, no LLM. (Scenario D in this repo exercises exactly this:
     `scenarios/D_phc_drift_hw_only/`.)

  5. The router fires the LOW route: a KMM Module CR or HostFirmwareComponents apply targets
     the offending node, delivered via the O-Cloud's O2 IMS interface. The Guardrail engine
     gates the action: dry-run first, blast radius (one node, one site, two cells) within
     caps, action allowlist hit, operator co-authorization required.

  6. The operator sees a TMF688 AuditEvent (`harness/schemas/AuditEvent.json`) with a populated
     ReversibilityProfile carrying the seven trust fields. The operator reads the proposed
     action, signs it.

  7. The action lands. The PHC stops drifting. The vDU clears the cell sync alarm. Total time
     from the PagerDuty alert to remediation applied: under 5 minutes, with the vendor
     boundary explicit and the rollback already validated against the Digital Twin.

## What the harness does and does not change

It does not replace the on-call engineer. It does not make vendor boundaries disappear. It does
not negotiate SLAs. It does not run unattended in production until EvalOps reports a track
record on the relevant scenario class.

It changes one thing: the human is at the decision point with a populated artifact, not in the
middle of the diagnosis. The five consoles still exist, but the operator does not have to walk
them to know which one carries the truth this time. The harness already walked them and wrote
the answer down in a structured artifact the operator can sign.

That is the "From" half of the title. From multivendor diagnosis as a 47-minute human walk
across five consoles, to closed-loop remediation as a 5-minute sign-and-apply against a
deterministic taxonomy with a populated ReversibilityProfile.
