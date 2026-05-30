---
title: "Trajectory: what Day-3 looks like after this bench lands Day-2"
author: David Kypuros
license: Apache-2.0
status: the post-Day-2 roadmap, the case for continued investment
audience: O-RAN nGRG workshop reviewers, research funding bodies, Red Hat / Ericsson / Intel program leads
---

# Trajectory: what Day-3 looks like

The bench lands closed-loop Day-2 remediation for a single-site multivendor Cloud RAN with the
operator co-authoring every action. That is the scope of the current contribution. It is the
scope a research workshop should fund as the proof of concept.

The interesting question is what Day-3 looks like. Single-site Day-2 is necessary but not
sufficient for the full vision. This narrative names the four workstreams that sit downstream of
the current bench and explains why each one is research, not engineering. A reviewer who is
deciding whether to fund continued work on this thesis should read this file as the explicit
roadmap.

## What Day-2 means and what it does not mean

Day-2 in the operations vocabulary is "the system is running and now needs to be maintained,
upgraded, troubleshooted, scaled." It is the long tail of post-deployment activity. The bench
addresses one slice of Day-2: closed-loop remediation when a fault is detected. It does not
address:

  - Multi-site coordination (one fault pattern across many cell sites at once)
  - Cross-operator learning (signatures and remediations shared across operator deployments)
  - Capacity-driven changes (proactive infrastructure changes ahead of forecasted load)
  - Cross-layer optimization (jointly tuning service and infrastructure layers for SLA cost)
  - Federated trust posture (EvalOps measurements composed across deployments)

These are Day-3 concerns. They are not gaps in the current bench; they are the next research
frontier the bench enables.

## Workstream 1: multi-site coordination

Today the bench's blast-radius caps are one node, one site, four cells. That is a deliberate
choice. The harness assumes a single-site operator. A regional or national operator runs
thousands of sites, and a fault pattern often presents at many sites simultaneously: a vendor
driver regression deploys to all sites in a maintenance window, a PHC drift signature appears
on all sites in a coastal region during a thermal event, a TMF921 intent failure rate climbs on
all sites served by one SMO instance.

Day-3 multi-site coordination requires:

  1. **Cross-site fault correlation.** When PHC drift fires at 14 sites in the same hour, the
     correct response is not 14 independent remediations. It is one investigation into the
     shared cause (driver version, NIC firmware batch, thermal event). The taxonomy needs a
     "patterned-across-sites" classification class that the current bench does not have.
  2. **Coordinated remediation.** When 14 sites need a driver rollback, the action plan is a
     staged rollout (canary one site, observe, expand to 3, observe, expand to all). The
     harness today emits one MachineConfig per fault; it needs an orchestrated multi-site plan
     and the guardrail caps need to scale with the canary structure.
  3. **Inter-SMO coordination.** Sites under different partner SMOs need their TMF921 intents
     coordinated. If 14 sites span Vendor A's SMO and Vendor B's SMO, the harness needs to
     emit intents to both in a coordinated window.

This workstream is research because the multi-site correlation problem is unsolved in the
agentic literature. Solutions exist for narrow signals (Wide-Area Network telemetry
correlation, BGP route flap detection), but none are designed for the O-RAN service-plus-O-Cloud
substrate the bench addresses.

## Workstream 2: cross-operator federated learning

A single operator running the bench produces a stream of audit events: faults observed,
classifications chosen, remediations emitted, outcomes validated. That stream is operationally
valuable to the operator. It is RESEARCH-valuable to the field if a privacy-preserving way
exists to share signatures across operators.

The model is how the LLVM compiler project gets bug reports from millions of users without
seeing any user's source code: the bug report carries the diagnostic without the surrounding
program. A federated EvalOps would carry the fault signature, the taxonomy hit, and the
remediation success rate, without the operator-identifying telemetry.

Day-3 cross-operator learning requires:

  1. **Signature anonymization.** A PHC drift signature on one operator's NIC must be
     representable as a vendor-and-driver-version-keyed pattern, not as an operator-specific
     telemetry sample.
  2. **Aggregation infrastructure.** A trusted aggregator (the O-RAN Alliance, or an
     independent research consortium) maintains the cross-operator taxonomy enrichment.
  3. **Differential incentive design.** Operators contribute signatures in exchange for access
     to the aggregated knowledge base. Incentive design is the unsolved problem; the technical
     infrastructure is simpler.

This workstream is research because the privacy-utility trade-off in telemetry sharing across
competing operators is open. Existing work in differential privacy and federated learning
addresses some of the building blocks; assembly into an O-RAN-specific shared-learning system
is the contribution.

## Workstream 3: capacity-driven proactive changes

The current bench reacts to faults. The next step is anticipating them. A Cloud RAN site has
predictable load curves (commuter traffic in the morning, event traffic in the evening, seasonal
patterns), and many infrastructure changes are usefully done ahead of load rather than during
it.

Day-3 proactive changes require:

  1. **Forecast-driven action proposals.** The cognitive middle proposes a MachineConfig change
     not because a fault fired but because load forecasting predicts a fault if the change is
     not made before 16:00 local time.
  2. **Confidence-bounded scheduling.** Forecasts are probabilistic. The harness needs a
     scheduling layer that combines forecast confidence with the action's risk profile to
     decide when to act.
  3. **Backout-driven trust posture.** Proactive actions are higher-stakes than reactive
     actions because the operator cannot validate the necessity. EvalOps must track
     proactive-action accuracy separately from reactive-action accuracy.

This workstream is research because the bench's current trust posture assumes the alarm is the
ground truth. A proactive system has no alarm yet; the forecast IS the ground truth, and
calibrating that ground truth is an open problem.

## Workstream 4: cross-layer optimization for SLA cost

Today the bench treats service-layer and infrastructure-layer actions as independent. A NIC
firmware update fires the dual-route pattern because both sides need to know, not because
either side affects the other's cost function.

In practice the two layers are coupled. A vDU upgrade (service layer) often allows a
PerformanceProfile relaxation (infrastructure layer) that saves CPU. A driver upgrade
(infrastructure layer) often enables better slice isolation (service layer). The current bench
does not exploit this coupling.

Day-3 cross-layer optimization requires:

  1. **Joint cost function.** The bench needs a unified SLA-cost model that scores actions
     across layers, not just within layers.
  2. **Optimization loop.** A periodic loop that proposes actions to reduce SLA cost given
     current state, separate from the fault-reactive loop the bench has today.
  3. **Vendor-cost transparency.** The cost function needs partner-SMO and vendor-published
     numbers (per-call cost of a handover, per-watt cost of a CPU isolation policy) that
     vendors today do not publish in a structured way.

This workstream is research because the cost-function ground truth is not available. Vendor
pricing is opaque, infrastructure cost models are operator-specific, SLA penalty structures are
contract-specific. Constructing a working cost function in the absence of these inputs is the
contribution.

## Workstream 5: federated trust posture

The trust loop (`./trust_loop_framing.md`) is per-deployment in the current bench. EvalOps
measures one operator's agent quality. Agentic Recoverability uses one operator's Digital Twin.
The Killswitch is one operator's NOC.

A federated trust posture would compose these signals across operators while preserving
local sovereignty. If three operators have observed a class of remediation success on their
Digital Twins, a fourth operator should be able to use that aggregate as part of their own
confidence calculation. The local trust posture remains authoritative; the federation
contributes prior probability.

Day-3 federated trust requires:

  1. **Cross-deployment EvalOps composition.** A formal way to compose per-deployment EvalOps
     measurements into a prior over remediation success rates.
  2. **Twin fidelity comparison.** Two Digital Twins from two operators are not identical;
     federated trust requires explicit modeling of twin-vs-twin fidelity.
  3. **Sovereignty preservation.** No operator's twin telemetry leaves the operator's premises.
     Only structured signatures and aggregate measurements participate in the federation.

This workstream is research because federated probabilistic models with strong locality
guarantees are an open problem in machine learning broadly, not just in telco.

## Why each workstream depends on this bench

The five workstreams above are not independent. Each builds on the current bench's contracts:

  - The TMF921 envelope is the high-side coordination point for multi-site (workstream 1).
  - The audit event schema is the carrier for federated signatures (workstreams 2, 5).
  - The deterministic taxonomy is the classification surface that proactive forecasts extend
    (workstream 3).
  - The routing rule's resource-layer split is the boundary that cross-layer optimization
    must respect (workstream 4).
  - The trust loop's per-action contracts are what a federated trust posture composes
    (workstream 5).

Without the current bench landing Day-2, none of the five workstreams have an architectural
foundation. With the current bench, all five become tractable research projects with a clear
scope and a clear interface to existing work.

## A note on what "Day-3" does not include

This narrative is deliberately conservative about what comes next. It does not propose:

  - Autonomous remediation without operator approval. The Intelligence Augmentation principle
    remains. The operator remains the decider; Day-3 makes the operator's decisions better-
    informed, not less authoritative.
  - General-purpose agentic operations. The bench is closed-loop O-RAN day-2 remediation. It is
    not a generic LLM-driven SRE assistant. Day-3 extends the same vertical, not the horizontal.
  - Replacement of the partner SMO. TMF921 emission remains the high-side contract. Day-3
    multi-site coordination uses TMF921 across more SMOs, not around them.

These exclusions are intentional. The bench's contribution is precisely the discipline of
staying narrow and trustworthy. Day-3 extends the discipline; it does not abandon it.

## What a workshop reviewer should take from this

The five workstreams are the research roadmap downstream of this bench. Each is well-scoped,
each has a clear interface to the current contracts, each is research rather than engineering
because the underlying problem is open in the literature.

If this work is funded as continuation:

  1. Workstream 1 (multi-site coordination) is the first to ship because it is the most
     operator-demanded extension and has the clearest contract foundation.
  2. Workstream 2 (federated learning) and Workstream 5 (federated trust) compose well and
     should be funded together.
  3. Workstream 3 (proactive changes) and Workstream 4 (cross-layer optimization) are longer
     horizons because they require inputs (forecasts, cost functions) that need to be
     constructed alongside the workstream.

The bench is the foundation. The workstreams are the structure. The reviewer who is asking
"where does this go after Day-2?" now has the answer in five specific directions, each anchored
in the contracts the bench already exposes.

This is the trajectory the talk does not have time to walk in 25 minutes. It is the trajectory
the repo carries.
