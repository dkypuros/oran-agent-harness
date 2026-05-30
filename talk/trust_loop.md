---
title: "Trust Loop: Digital Twin substrate, EvalOps, Sandbox, Agentic Recoverability, and the Intelligence Augmentation principle"
author: David Kypuros
venue: O-RAN nGRG Workshop, Seattle
date: 4th [THU] JUN 2026
license: Apache-2.0
status: open-questions content for the closing section of the talk
---

# Trust Loop: the Digital Twin substrate and what runs on top of it

The harness pattern in this repository defends three architectural contributions (routing rule,
guardrail contract, LLM-neutral substrate). Those three are necessary for a closed-loop Day-2 system
to ship. They are not sufficient for the system to be trusted in production. This document covers the
trust layer that sits on top of the three contributions: a Digital Twin substrate that supports three
activities (EvalOps, Sandbox, Agentic Recoverability) plus the architectural principle that ties them
together (Intelligence Augmentation).

## The Digital Twin as substrate

The Digital Twin is the foundation. It is a same-topology mirrored cluster (or a simulated subset of
one: linuxptp + NIC driver + a stand-in for the vDU) where actions can be exercised before they touch
production, telemetry can be measured against a known good baseline, and inverse actions can be
validated before they are committed. Three different concerns run on top of this substrate:
EvalOps measures agent behavior on the twin over time; the Sandbox is a forward-direction test flight
on the twin for one proposed action; Agentic Recoverability uses the twin to confirm that the inverse
of an applied action will land cleanly. None of the three replaces the twin. They are all activities
that the twin makes possible.

The talk's open question about the twin is operational, not architectural: does the twin live inside
the hub OpenShift cluster (cheaper, easier to wire) or is it a fully separate facility (closer to a
real production twin, more credible)? Both have working implementations in adjacent telecom verticals.
The harness pattern is twin-substrate neutral.

## Activity 1: EvalOps, continuous measurement on the twin

A closed-loop remediation agent cannot self-grade. Confidence reported by an LLM is not the same as
empirical reliability over time. EvalOps is the operations discipline that treats agent quality the
way SRE treats latency: continuously measured, tied to specific scenarios, and surfaced as a
first-class telemetry signal alongside the action itself.

Concretely, this means every RemediationProposal emitted by the routing rule carries a confidence
value that is comparable across runs because the twin gives EvalOps a stable surface to measure
against. The harness tracks, per taxonomy entry, the historical accuracy of the deterministic
classifier and the LLM-assist tier. Drift in either is a signal that the taxonomy needs an entry, or
that the LLM provider has changed behavior under the hood. EvalOps is what turns "the model said yes"
into "the model has been right on this scenario class 91 percent of the time over the last 600 events,
and the false-positive cost is one MachineConfig rollback."

## Activity 2: Sandbox, the pre-validation test flight on the twin

The guardrails YAML enforces blast-radius caps and dry-run defaults at the contract level. Those caps
say what cannot happen. They do not say what will happen. The Sandbox layer answers that second
question by running the proposed remediation against the twin before the live action enters the
O-Cloud.

The twin receives the same MachineConfig or KMM Module CR the harness would apply live. The harness
observes the twin's PTP state, NIC counters, and pod readiness after a configurable settle interval.
Only twins that converge inside the expected envelope produce an apply-allowed signal back to the
guardrail engine. This is the two-key gate pattern: the operator authorizes the action class, the
sandbox authorizes the specific payload.

## Activity 3: Agentic Recoverability, undo validation on the twin

Even after EvalOps and Sandbox pass, a closed-loop action must remain reversible at the operational
seam where humans pick up. Agentic Recoverability is the discipline of using the twin to validate the
inverse action (the rollback intent) before the operator commits. It is the per-action undo, not
disaster recovery. Disaster recovery rebuilds the house; Agentic Recoverability undoes the last paint
job. The vocabulary matters because telecom operations teams have decades of DR vocabulary
(RTO, RPO, full failover) that means something specific, and Agentic Recoverability is narrower and
more surgical than any of that.

The contract is the Reversibility Profile, a structured field on every audit event that exposes seven
attributes the operator needs in order to assess and exercise a rollback: rollback_intent,
blast_radius_if_reverse, rebuild_timeline, replication_history, validation_history,
risk_profile_burn_down, and confidence_in_reversibility. The full schema lives at
`harness/schemas/ReversibilityProfile.json` and is applied to both walkthrough scenarios. The
validation_history field carries the twin's verdict on the inverse action: if the twin has not
exercised the rollback recently, the profile says so, and the operator weighs that accordingly.

## The principle: Intelligence Augmentation

The trust layer above is not letting AI loose in a production RAN. It is Intelligence Augmentation
(IA), the discipline of building tools that gather evidence, prepare briefs, and present them to a
human decision maker. The vocabulary predates AI; Doug Engelbart sketched IA in the 1960s as the
goal of computing (augmenting human intellect, not replacing it). The harness is built that way.
The agents observe and propose; the operator decides. The twin runs evidence collection at scale; the
human reads the headline. The Reversibility Profile makes the undo button visible at the moment of
decision instead of buried in vendor documentation.

The system also surrenders control when told to. The Killswitch (`talk/killswitch.md`, formal name
crisis_mode in `harness/guardrails.yaml`) is the global override that freezes all agent write
actions during macro events when the physical world is in a state the agents were never trained for.
IA is not just "the AI prepares the brief and the human decides." It is "the AI prepares the brief,
the human decides, and the human can pull the cord at any moment with no negotiation."

## Where these activities fit in the routing decision

EvalOps gates the agent (is this agent reliable enough to take its proposal seriously?). Sandbox
gates the payload (will this specific action land cleanly on the twin?). Agentic Recoverability gates
the operator (can the operator walk this back if it does not work?). The harness pattern ships with
hooks for all three but mandates only the Reversibility Profile in v0, because that is the part the
operator absolutely needs to read at decision time. The other two are operational disciplines that
mature as the deployment matures.

The contribution is wiring them together onto a shared Digital Twin substrate, under the explicit
banner of Intelligence Augmentation, with a global Killswitch as the operator's reserve power. None
of the individual pieces is novel research. All of them are well-known disciplines from adjacent
fields (LLMOps, infrastructure-as-code, change management, control engineering). The contribution is
the assembly.
