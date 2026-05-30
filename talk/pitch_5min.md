---
title: "5-minute pitch, for hallway capture at nGRG"
author: David Kypuros
venue: O-RAN nGRG Workshop, Seattle
date: 4th [THU] JUN 2026
license: Apache-2.0
status: spoken-word script, 5 minutes, mid-walk audience
---

# 5-minute pitch

When someone catches you between sessions and asks "what is your work about?" Five minutes is the
budget. Names the novelty, lands at the repo URL.

## Beats (with time)

### Beat 1 (00:30). The problem

When PTP drifts on a multivendor Cloud RAN site, no single operator can pinpoint the cause without
crossing four or five vendor boundaries. Today that takes 30 minutes minimum before a vendor
even confirms ownership. The day-2 status quo is human triage across vendor consoles, with the
operator carrying the cross-vendor model in their head.

### Beat 2 (01:30). The harness pattern

We built a research bench for closed-loop day-2 remediation. The harness sits between the
observation loop on the left (Intel NIC PHC, linuxptp, cloud-event-proxy) and the action layer on
the right (the SMO, the O-Cloud). Inside, three things happen: a deterministic taxonomy classifies
the fault against the O-RAN WG6 O-Cloud resource model, an LLM disambiguates only the residual
ambiguous class, and a routing rule splits actions by O-RAN resource layer.

### Beat 3 (01:30). The novelty

The right-side execution path grounds infrastructure remediation in two standardized contracts at
once. The O-RAN O2 IMS interface above, the CRD-shaped delivery contracts below (Metal3
BareMetalHost / HostFirmwareComponents for node firmware, Machine Config Operator for host
configuration). The 2+3+8+9 conjunction is what lets a single remediation proposal travel from
the cognitive layer through a standardized O-RAN interface into a concrete Kubernetes-native
contract that already runs in production. Most prior agentic-RAN work either stops at the SMO
boundary without a delivery story or proposes a custom controller plane that side-steps O-RAN's
resource layering.

### Beat 4 (01:00). Concrete proof

Two scenarios make this concrete. Scenario D shows the software-LOCKED vs hardware-NOT-OK
divergence pattern: linuxptp reports synchronized while the NIC reports rising hardware timestamp
timeouts. The harness sees through the surface signal and routes to the hardware layer. Scenario
E fires a NIC firmware update via Metal3, AND emits a TMF921 companion intent UP to the SMO in
parallel because firmware reboots require SMO coordination regardless of cell count. That dual-route
pattern is the teaching moment.

### Beat 5 (00:30). What it is and what's next

This is a research bench under Apache 2.0. The talk is one moment of it. The bench lives at
github.com/dkypuros/oran-agent-harness. We are extending toward multi-site coordination and
cross-vendor shared learning. If you are working in this space, the contracts are portable to
LangGraph, OpenAI Agents SDK, Microsoft Semantic Kernel, or any agent framework that reads JSON
Schema and YAML.

## Variants by audience

- **Working group chair**: lead with the citation discipline. "Every claim anchored at file plus
  line, verify gate gives reviewers a falsifiable yes/no."
- **Vendor PM**: lead with the dual-route pattern. "Your service-layer intents are not subsumed,
  the harness emits TMF921 to your SMO, you stay in charge of what you control."
- **Senior engineer**: lead with the deterministic taxonomy. "LLM is invoked only when the
  taxonomy resolves to ambiguous, which it does on a minority of faults."
- **Academic / research lab**: lead with the bench framing. "Apache 2.0 substrate you can build
  on; the contracts are operationalization-agnostic."

## Handoff

End the pitch by saying "the repo has the full architecture narrative at
`talk/architecture_narrative.md` and a 25 minute runsheet at `talk/runsheet_25min.md`; pull
either when you have time." Repo URL on a business card if you are old school.
