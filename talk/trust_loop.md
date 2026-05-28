---
title: "Trust Loop: EvalOps, Sandboxing, and the Reversibility Profile"
author: David Kypuros
venue: O-RAN nGRG Workshop, Seattle
date: 4th [THU] JUN 2026
license: Apache-2.0
status: open-questions content for the closing section of the talk
---

# Trust Loop: EvalOps, Sandboxing, and the Reversibility Profile

The harness pattern in this repository defends three architectural contributions (routing rule, guardrail
contract, LLM-neutral substrate). Those three are necessary for a closed-loop Day-2 system to ship. They are
not sufficient for the system to be trusted in production. This document covers the three open
human-machine-teaming questions named in the abstract's closing paragraph and proposes how each one becomes
a concrete artifact rather than a hand-wave.

## 1. EvalOps for agentic confidence scoring

A closed-loop remediation agent cannot self-grade. Confidence reported by an LLM is not the same as
empirical reliability over time. EvalOps is the operations discipline that treats agent quality the way SRE
treats latency: continuously measured, tied to specific scenarios, and surfaced as a first-class telemetry
signal alongside the action itself.

Concretely, this means every RemediationProposal emitted by the routing rule carries a confidence value that
is comparable across runs. The harness tracks, per taxonomy entry, the historical accuracy of the
deterministic classifier and the LLM-assist tier. Drift in either is a signal that the taxonomy needs an
entry, or that the LLM provider has changed behavior under the hood. EvalOps is what turns "the model said
yes" into "the model has been right on this scenario class 91 percent of the time over the last 600 events,
and the false-positive cost is one MachineConfig rollback."

## 2. Digital-twin sandboxing prior to live action

The guardrails YAML enforces blast-radius caps and dry-run defaults at the contract level. Those caps say
what cannot happen. They do not say what will happen. The sandbox layer answers that second question by
running the proposed remediation against a digital twin of the target cluster before the live action enters
the O-Cloud.

For an OpenShift Cloud RAN site, the twin is a same-topology test cluster (or a simulated linuxptp + NIC
driver stack) that receives the same MachineConfig or KMM Module CR the harness would apply. The harness
observes the twin's PTP state, NIC counters, and pod readiness after a configurable settle interval. Only
twins that converge inside the expected envelope produce an apply-allowed signal back to the guardrail
engine. This is the "two-key gate" pattern: the operator authorizes the action class, the sandbox authorizes
the specific payload.

The talk's open question is whether the twin lives inside the same hub OpenShift cluster (cheaper, easier
to wire) or is a fully separate facility (closer to a real production twin, more credible). Both have
working implementations in adjacent telecom verticals. The harness pattern is twin-substrate neutral.

## 3. The Reversibility Profile schema

Even after EvalOps and sandbox validation pass, a closed-loop action must remain reversible at the
operational seam where humans pick up. The Reversibility Profile is a structured field on every audit
event that exposes seven attributes the operator needs in order to assess and exercise a rollback:
rollback_intent, blast_radius_if_reverse, rebuild_timeline, replication_history, validation_history,
risk_profile_burn_down, and confidence_in_reversibility. The full schema lives at
harness/schemas/ReversibilityProfile.json and is applied to both walkthrough scenarios in this repository.

The reversibility profile is the contract between the harness and the human in the loop. It says, in the
same place every time and in the same shape every time, what will happen if the operator decides this was
the wrong action. Without it, closed-loop remediation is asking the operator to trust a system whose undo
button is hidden in vendor documentation.

## Where these three pillars fit in the routing decision

EvalOps gates the agent. Sandbox gates the payload. Reversibility gates the operator. The harness pattern
ships with hooks for all three but mandates only the reversibility schema in v0, because that is the part
the operator absolutely needs to read at decision time. The other two are operational layers that mature as
the deployment matures.

These three pillars are what we mean by "human-machine teaming for closed-loop remediation" in the abstract.
None of them is novel research. All three are well-known disciplines from adjacent fields (LLMOps,
infrastructure-as-code, change management). The contribution is wiring them together into a single audit
event that the operator and the operator's tools can both read.
