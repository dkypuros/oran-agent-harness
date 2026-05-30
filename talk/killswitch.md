---
title: "Killswitch: the Agentic Circuit Breaker for macro events"
author: David Kypuros
venue: O-RAN nGRG Workshop, Seattle
date: 4th [THU] JUN 2026
license: Apache-2.0
status: operational-context content for the closing section of the talk
---

# Killswitch: the Agentic Circuit Breaker for macro events

## Where this came from

The per-action guardrails in `harness/guardrails.yaml` (dry-run default, blast-radius caps, action
allowlist, operator-harness co-authorization, audit emission) cover the everyday case: one anomaly,
one proposed action, one operator decision. They do not cover the case AT&T operations engineers
flagged when this architecture was walked past them: what happens during a hurricane, a tornado, a
regional lightning storm, or a power-grid event when the physical world has become something the
agents were never trained for.

This basis is informal operational feedback from an architecture walk-through with AT&T operations engineers, not a published joint endorsement.

In a traditional appliance world the operator pulls the power cord or the fiber line. In a
software-defined Cloud RAN there is no cord. The "appliance" is distributed across thousands of
Kubernetes pods on hundreds of bare-metal nodes. An agent trained on normal anomaly patterns, faced
with a hurricane, will try to "fix" the degraded network by re-homing cells and shifting workloads.
That creates a control-plane storm that fights physical reality and makes the outage worse.

The Killswitch (formally crisis_mode in guardrails.yaml) is the cord.

## What it does

When activated, crisis_mode flips a global override that supersedes every per-action setting:

- dry_run_default forced to true (live application is impossible regardless of any individual rule)
- require_human_approval forced to all (every action class, no exceptions)
- write access to O2 IMS revoked (the down-route is severed)
- write access to the TMF921 SMO endpoint revoked (the up-route is severed)
- EvalOps confidence floor pinned at 0.0 (the agents are told their historical training is invalid
  because the physical world is in an extreme state)
- telemetry routing flipped to manual queues (alerts bypass the harness entirely and land in
  traditional human-managed ticketing)

The agents are not turned off. They can still observe, classify, and propose. Their hands are
digitally tied behind their backs. Operators take direct control until the physical crisis is
resolved.

## The 5-second acknowledgement

A killswitch that takes 30 seconds to propagate across a distributed agent fleet is not a
killswitch. The guardrails.yaml contract says acknowledgement_latency_max_seconds is 5. Every
agent in the fleet (platform, RAN, hardware, router, guardrail engine, gateway) must acknowledge
the freeze within 5 seconds of activation, and the CrisisModeActivation event records each
acknowledgement as it arrives. If the fleet has not fully acknowledged by the deadline, the
operator is paged with the list of non-responsive agents and can choose to force-kill those
specific containers or escalate. This is non-trivial. It is also the contract.

## The key-holder model

Activation requires explicit operator action by a NOC supervisor or a designated key holder.
Deactivation also requires explicit operator action, with multi-key activation recommended (two
key holders required to come out of crisis mode). After deactivation, the harness performs a
full diagnostic re-baseline before agents continue autonomous reasoning. The point is to make
returning to normal operation a deliberate, audited act, not an accidental drift back into agent
control.

## Vocabulary: Killswitch versus Reversibility Profile

These are two different mechanisms answering two different questions:

- **Reversibility Profile** (in every AuditEvent, schema at `harness/schemas/ReversibilityProfile.json`)
  answers: the action I took yesterday turned out bad, walk it back. Targeted, per-action, surgical.
- **Killswitch** (crisis_mode in `harness/guardrails.yaml`) answers: the physical world is in a
  state my agents were never trained for, stand down all of them until I say otherwise. Global,
  blanket, blunt by design.

The two compose. After a hurricane has passed and crisis mode is deactivated, individual
remediation actions can still carry their Reversibility Profiles for fine-grained walkbacks.
Crisis mode does not replace the per-action contract; it suspends it.
