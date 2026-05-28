---
title: "From Multivendor Diagnosis to Closed-Loop Remediation: An Agent Harness for Cloud RAN Day-2"
author: David Kypuros
venue: O-RAN nGRG Workshop, Seattle
date: 4th [THU] JUN 2026
license: Apache-2.0
status: canonical submission
---

Multivendor Cloud RAN faults routinely span RAN software, the cloud platform, and underlying hardware,
making Day-2 triage slow and brittle. Agentic systems integrated through an Agentic Gateway over MCP have
begun to address the diagnosis half of the problem by coordinating domain-specific agents over controlled
interfaces while preserving vendor-private knowledge. PTP synchronization is a particularly demanding test,
with root causes ranging from hardware timestamp inconsistency to host-level misconfiguration interfering
with PTP traffic.

This talk asks what it takes to extend such diagnostic substrates into closed-loop Day-2 operations. We
propose an agent harness pattern that bridges the diagnostic layer to O-Cloud via the O-RAN O2 IMS API
and bare-metal lifecycle management, using Red Hat's open-source O-Cloud Manager as the reference O2 IMS
implementation. The pattern layers three contributions on top of generic agent frameworks:

A remediation routing rule that follows O-RAN's resource layering, sending service-layer actions (cell
re-home, RAN parameter change) upward to partner orchestrators via intent interfaces, and infrastructure
actions (firmware, kernel config, PTP tuning) downward through O2 IMS.

A guardrail contract layer specifying operator-harness co-authorization, blast-radius caps, dry-run
defaults, and structured audit emission.

An LLM-neutral substrate ensuring operators retain control over model choice and data sovereignty.

We walk host-platform PTP scenarios (a fw-lldp-agent misconfiguration and an outdated NIC driver) through
the harness, from linuxptp state changes published as O-RAN CloudEvents by Cloud Event Proxy, to fixes
routing into the O-Cloud as MachineConfig and KMM Module artifacts delivered via O2 IMS rather than
escalating to the SMO. We close with open questions on human-machine teaming for closed-loop remediation
(agent governance, digital-twin sandboxing prior to live action, and EvalOps for agentic confidence
scoring), alongside the role of MCP relative to O-RAN-native interfaces.
