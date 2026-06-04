---
title: "Trust Loop: Digital Twin substrate, EvalOps, Sandbox, Agentic Recoverability, and the Intelligence Augmentation principle"
author: David Kypuros
venue: O-RAN nGRG Workshop, Seattle
date: 4th [THU] JUN 2026
license: Apache-2.0
status: open-questions content for the closing section of the talk
---

# Trust Loop: the Digital Twin substrate and what runs on top of it

The three architectural contributions (routing rule, guardrail contract, LLM-neutral substrate) are
necessary for a closed-loop Day-2 system to ship, but not sufficient for it to be trusted in
production. This document covers the trust layer that sits on top: a Digital Twin substrate
supporting three activities (EvalOps, Sandbox, Agentic Recoverability) plus the principle that ties
them together (Intelligence Augmentation).

## The Digital Twin as substrate

The Digital Twin is the foundation. It is a same-topology mirrored cluster, or a simulated subset of
one (linuxptp plus NIC driver plus a stand-in for the vDU), where actions can be exercised before
they touch production, telemetry can be measured against a known good baseline, and inverse actions
can be validated before they are committed. Three concerns run on top: EvalOps measures agent
behavior on the twin over time; the Sandbox is a forward-direction test flight on the twin for one
proposed action; Agentic Recoverability uses the twin to confirm that the inverse of an applied
action will land cleanly. The talk's open question about the twin is operational, not
architectural: does it live inside the hub OpenShift cluster or as a separate facility? Both work.
The harness pattern is twin-substrate neutral.

## Activity 1: EvalOps, continuous measurement on the twin

A closed-loop remediation agent cannot self-grade. Confidence reported by an LLM is not the same as
empirical reliability over time. EvalOps treats agent quality the way SRE treats latency:
continuously measured, tied to specific scenarios, surfaced as a first-class telemetry signal
alongside the action.

Every RemediationProposal carries a confidence value comparable across runs because the twin gives
EvalOps a stable surface to measure against. The harness tracks, per taxonomy entry, the historical
accuracy of the deterministic classifier and the LLM-assist tier. Drift in either signals that the
taxonomy needs an entry or that the LLM provider changed behavior. EvalOps is what turns "the model
said yes" into "the model has been right on this scenario class 91 percent of the time over 600
events, and the false-positive cost is one MachineConfig rollback."

## Activity 2: Sandbox, the pre-validation test flight on the twin

The guardrails YAML enforces blast-radius caps and dry-run defaults at the contract level. Those
caps say what cannot happen; they do not say what will. The Sandbox answers the second question by
running the proposed remediation against the twin before the live action enters the O-Cloud.

The twin receives the same MachineConfig or KMM Module CR the harness would apply live. The harness
observes PTP state, NIC counters, and pod readiness after a configurable settle interval. Only
twins that converge inside the expected envelope produce an apply-allowed signal back to the
guardrail engine. This is the two-key gate: the operator authorizes the action class, the sandbox
authorizes the specific payload.

## Activity 3: Agentic Recoverability, undo validation on the twin

Even after EvalOps and Sandbox pass, a closed-loop action must remain reversible. Agentic
Recoverability uses the twin to validate the inverse action before the operator commits. It is the
per-action undo, not disaster recovery. Disaster recovery rebuilds the house; Agentic Recoverability
undoes the last paint job. RTO and RPO concepts do not apply.

The contract is the Reversibility Profile, a structured field on every audit event exposing seven
attributes: rollback_intent, blast_radius_if_reverse, rebuild_timeline, replication_history,
validation_history, risk_profile_burn_down, and confidence_in_reversibility. The full schema lives
at `harness/schemas/ReversibilityProfile.json` and is applied to both walkthrough scenarios. The
validation_history field carries the twin's verdict on the inverse action.

## The principle: Intelligence Augmentation

This trust layer is not letting AI loose in a production RAN. It is Intelligence Augmentation, a
discipline Doug Engelbart sketched in the 1960s as the goal of computing. The harness is built that
way: agents observe and propose, the operator decides. The twin runs evidence collection at scale,
the human reads the headline. The Reversibility Profile puts the undo button at the moment of
decision instead of buried in vendor documentation.

The system also surrenders control when told to. The Killswitch (`talk/killswitch.md`, formal name
crisis_mode in `harness/guardrails.yaml`) is the global override that freezes all agent write
actions during macro events. IA is not just "AI prepares the brief, human decides." It is "the
human can pull the cord at any moment with no negotiation."

## Where these activities fit in the routing decision

EvalOps gates the agent (is this agent reliable enough?). Sandbox gates the payload (will this
action land cleanly?). Agentic Recoverability gates the operator (can this be walked back?). The
harness ships with hooks for all three but mandates only the Reversibility Profile in v0, because
that is what the operator absolutely needs at decision time. EvalOps and Sandbox are operational
disciplines that mature with the deployment.

The contribution is the assembly: a Digital Twin substrate, three activities running on it,
Intelligence Augmentation as the explicit banner, and a global Killswitch as the operator's reserve
power.

For the implementation-level status of EvalOps, validation gates, and what is real versus stubbed in v0, see `../docs/evalops-and-validation.md`.
