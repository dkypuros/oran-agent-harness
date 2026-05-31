---
title: "Trust Loop Framing: Digital Twin substrate, three activities, Intelligence Augmentation, Killswitch"
author: David Kypuros
license: Apache-2.0
status: promotion of talk/trust_loop.md content to a foregrounded standalone narrative
audience: architects, working-group reviewers, anyone asking how this gets trusted in production
---

# Trust Loop Framing

The three architectural contributions (routing rule, guardrail contract, LLM-neutral substrate)
are necessary to ship a closed-loop day-2 system. They are not sufficient to TRUST it in
production. The trust layer sits on top of all three: a Digital Twin substrate carrying three
activities (EvalOps, Sandbox, Agentic Recoverability) under the explicit banner of
Intelligence Augmentation, with a global Killswitch as the operator's reserve power.

This narrative foregrounds material that lives in `../talk/trust_loop.md` and
`../talk/killswitch.md`. The talk references it briefly. The reader who wants the trust posture
in full should land here.

## The Digital Twin as substrate, not as service

The Twin is the floor the cognitive layer stands on. Same-topology mirrored cluster, or a
simulated subset of one (linuxptp plus NIC driver plus stand-in vDU). Three activities run on
top, not next to it. The bench is twin-substrate-neutral: the Twin can live inside the hub
OpenShift cluster, in a separate facility, or as a simulation host. The harness pattern does
not pick.

This matters because deployment teams will negotiate the Twin's home with the platform team and
the infosec team. The harness contract is the activities, not the Twin's location.

## Activity 1: EvalOps, continuous agent measurement

A closed-loop remediation agent cannot self-grade. LLM-reported confidence is not the same as
empirical reliability over time. EvalOps treats agent quality the way SRE treats latency:
continuously measured, tied to specific scenarios, surfaced as a first-class telemetry signal
alongside the action itself.

Every RemediationProposal carries a confidence value comparable across runs because the Twin
gives EvalOps a stable surface to measure against. The harness tracks, per taxonomy entry, the
historical accuracy of both the deterministic classifier and the LLM-assist tier. Drift in
either signals either that the taxonomy needs a new entry or that the LLM provider's behavior
changed. EvalOps is what turns "the model said yes" into "the model has been right on this
scenario class 91 percent of the time over 600 events, and the false-positive cost is one
MachineConfig rollback."

EvalOps gates the agent. The question it answers: is this agent reliable enough to be on the
proposal path for this scenario class right now?

## Activity 2: Sandbox, the per-action test flight

The guardrails enforce blast-radius caps and dry-run defaults at the contract level. Those caps
say what CANNOT happen. They do not say what WILL. The Sandbox answers the second question by
running the proposed remediation against the Twin before the live action enters the O-Cloud.

The Twin receives the same MachineConfig, KMM Module CR, HostFirmwareComponents apply, or
TMF921 intent the harness would emit live. The harness observes PTP state, NIC counters, pod
readiness, and intent acceptance after a configurable settle interval. Only Twins that converge
inside the expected envelope produce an apply-allowed signal back to the guardrail engine.

The Sandbox gates the payload. The question it answers: will THIS specific action land cleanly
on a topologically identical system?

## Activity 3: Agentic Recoverability, undo validation on the Twin

Even when EvalOps and the Sandbox both pass, a closed-loop action must remain reversible. The
per-action undo is not disaster recovery; it is the recovery affordance attached to one
specific change. Disaster recovery rebuilds the house. Agentic Recoverability undoes the last
paint job. RTO and RPO concepts do not apply.

The contract is the ReversibilityProfile (schema at
`../harness/schemas/ReversibilityProfile.json`). Seven attributes on every AuditEvent:

  - `rollback_intent` (what the inverse action is)
  - `blast_radius_if_reverse` (what undoing it touches)
  - `rebuild_timeline` (how long the inverse takes)
  - `replication_history` (whether the inverse has worked in the past)
  - `validation_history` (the Twin's verdict on the inverse, populated by Agentic Recoverability)
  - `risk_profile_burn_down` (how the risk decays as the inverse settles)
  - `confidence_in_reversibility` (the composite headline value)

Seven fields, same place every time, same shape every time. That is the contract between the
harness and the human at decision time.

Agentic Recoverability gates the operator. The question it answers: if the operator signs this
and it goes wrong, can they walk it back?

## The principle: Intelligence Augmentation, not Artificial Intelligence

This trust layer is not letting AI loose in a production RAN. It is Intelligence Augmentation,
a discipline Doug Engelbart sketched in the 1960s as the goal of computing. Agents observe and
propose; the operator decides. The Twin runs evidence collection at scale; the human reads the
headline. The ReversibilityProfile puts the undo button at the moment of decision instead of
buried in vendor documentation.

The framing is deliberate. "AI" in production telco reads as "ungoverned." "IA" reads as
"governed, with human authority intact." The harness contracts are written to make the second
reading correct: every action is a Proposal, every Proposal arrives with a ReversibilityProfile,
every commit is signed by an operator. The taxonomy is deterministic where possible because
deterministic is auditable. The LLM is invoked only on the ambiguous residual because that is
where its judgment beats deterministic rules.

## The Killswitch (crisis_mode)

The system also surrenders control when told to. The Killswitch (formal name `crisis_mode` in
`../harness/guardrails.yaml`) is the global override that freezes all agent write actions
during macro events: hurricanes, tornadoes, lightning storms, security incidents, anything
where the harness's normal pattern matching would actively fight a degraded physical world.

When `crisis_mode: true`:

  - All write paths revoked, both O2 IMS (low side) and SMO TMF921 (high side).
  - EvalOps confidence pinned to zero, every proposal flagged as ungated.
  - Telemetry routed to manual human queues; the agentic gateway becomes a read-only relay.
  - Existing in-flight actions allowed to complete or roll back, but no new actions accepted.

The Killswitch is the operator's reserve power. The ReversibilityProfile undoes one applied
action. The Killswitch freezes all of them. The two compose; they answer different questions.

Full framing including the AT&T review notes is at `../talk/killswitch.md`. The
deterministic evaluator that enforces crisis_mode is at `../harness/runtime/guardrail.py`; the
test at `../tests/test_runtime.py` (`test_evaluate_crisis_mode_active`) verifies the override
mid-proposal.

## Where these activities live in the talk and the bench

  - EvalOps: hooks exist in the harness contract; full continuous-measurement implementation
    is operational discipline that matures with the deployment.
  - Sandbox: implemented in v0. The stage is `sandbox_simulation()` in
    `../harness/runtime/walker.py`; the per-scenario twin verdict lives in
    `../harness/runtime/scenario_stubs.json` `sandbox_verdict` blocks; the apply-allowed gate
    is enforced in `../harness/runtime/guardrail.py` before the action_allowlist check; tested
    in `../tests/test_runtime.py::test_evaluate_sandbox_block_when_apply_disallowed`. The Twin
    substrate (same-topology mirrored cluster vs simulated subset) is the engineering
    decision the deployment makes; the bench ships the contract and the gate.
  - Agentic Recoverability: the ReversibilityProfile schema is mandatory in v0 of the bench
    (`../harness/schemas/ReversibilityProfile.json`).
  - Intelligence Augmentation: the explicit banner over all three.
  - Killswitch: declared in `../harness/guardrails.yaml`, enforced in
    `../harness/runtime/guardrail.py`, tested in
    `../tests/test_runtime.py::test_evaluate_crisis_mode_active`.
  - SMO dispatch_result capture (the dual-route reconciliation field): implemented in
    `../harness/runtime/router.py::_maybe_attach_dispatch_result()`, populated from
    `../harness/runtime/scenario_stubs.json` `smo_dispatch_outcome` blocks. The accepted path
    is `../scenarios/E_nic_firmware_update/`; the rejected path is
    `../scenarios/E_with_smo_reject/`. Tested by
    `../tests/test_runtime.py::test_dispatch_result_rejected_on_smo_reject_scenario`.

The contribution is the assembly. A Digital Twin substrate, three activities running on it,
Intelligence Augmentation as the explicit banner, and a global Killswitch as the operator's
reserve power. None of these alone is novel; the assembly with the specific contracts above is.

## What this means for the reader

If you are a working-group reviewer asking how this gets trusted in production, the answer is
not "trust the model." The answer is the trust loop: bound the agent's authority (deterministic
taxonomy first, LLM only on ambiguous), measure the agent's performance over time (EvalOps),
pre-validate every specific action against an identical-topology Twin (Sandbox), require every
action to declare its own undo (ReversibilityProfile), make the operator's reserve power
explicit (Killswitch), and frame the whole thing as Intelligence Augmentation rather than
autonomous AI.

Trust here is not a posture, it is a set of contracts. Every contract has a file path in this
repo. Every file path has a citation to a standard or a piece of upstream Kubernetes-native
infrastructure. The reader can verify the trust posture by reading the files.
