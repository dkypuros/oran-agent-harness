---
title: "Reviewer FAQ"
author: David Kypuros
venue: O-RAN nGRG Workshop, Seattle
date: 4th [THU] JUN 2026
license: Apache-2.0
status: anticipated reviewer questions with citation-anchored answers
---

# Reviewer FAQ

Questions the speaker expects from working-group reviewers, senior engineers, vendor PMs, and
academic readers. Each answer is anchored at file plus line where possible so the reviewer can
verify the claim without taking the speaker's word.

## Q1. How is this different from existing agentic-RAN frameworks?

Most prior agentic-RAN work either stops at the SMO boundary (the proposal terminates as an
intent, no delivery story) or proposes a custom controller plane that side-steps O-RAN's own
resource layering. This bench grounds the right-side execution path in two standardized contracts
simultaneously: O-RAN O2 IMS above (`docs/references.md#ref-2`, `docs/references.md#ref-3`), and
the CRD-shaped delivery contracts below (Metal3 BareMetalHost / HostFirmwareComponents at
`docs/references.md#ref-8`; Machine Config Operator at `docs/references.md#ref-9`). The 2+3+8+9
conjunction is the novelty claim. Full positioning at `talk/architecture_narrative.md` lines
18-35.

## Q2. Why deterministic taxonomy first instead of LLM-first?

LLM-first routing has two failure modes that matter for production telco: nondeterministic
outputs on identical inputs, and silent drift when a model version changes. The bench inverts
this: the taxonomy at `harness/taxonomy.yaml` is a 20-entry deterministic lookup against the
O-RAN WG6 O-Cloud resource model. The LLM is invoked only when the taxonomy resolves to the
`ambiguous` class, which is a minority of faults. The routing rule at
`harness/routing-rules/contribution-1-routing-rule.yaml` enforces this ordering. The deterministic
runtime is at `harness/runtime/router.py`; the test suite at `tests/test_runtime.py` exercises
both the deterministic path and the LLM-assist path.

## Q3. What about LLM bias in the ambiguity resolution step?

EvalOps treats agent quality the way SRE treats latency: continuously measured, tied to specific
scenarios, surfaced as a first-class telemetry signal. The harness tracks, per taxonomy entry,
the historical accuracy of both the deterministic classifier and the LLM-assist tier (see
`talk/trust_loop.md` lines 30-42). Drift in either signal triggers operator review. Plus, every
LLM response on the ambiguous path is recorded in the AuditEvent's `knowledge_base_lookups`
field, so the bias case has an audit trail.

## Q4. How does this interact with the O1 / O2 vs MCP-private telemetry boundary?

The MCP servers consume O-Cloud-internal platform telemetry (linuxptp state, MachineConfig pool
status, KMM Module load state, NIC PHC counters). This is NOT governed by O-RAN O1
(`docs/references.md#ref-49`), which standardizes SMO-to-managed-element OAM where managed
elements are O-CU, O-DU, O-RU. The O-Cloud platform layer sits below the managed-element
boundary. The standardized SMO-facing flow IS spec-governed: the guardrail engine emits a TMF688
AuditEvent (`docs/references.md#ref-18`) and the O-Cloud Manager exposes alarms via the O2 IMS
AlarmEventRecord (O2IMS-INTERFACE R005-v11 Section 3.3.6.2.2,
`docs/references.md#ref-3`). Full boundary discussion at `talk/architecture_narrative.md`
section 2.

## Q5. Why route through Machine Config Operator instead of direct kubectl?

Three reasons. First, MachineConfig (`docs/references.md#ref-9`) is the audited delivery
mechanism on OpenShift O-Cloud; direct kubectl bypasses cluster-admin separation. Second, MCO
handles node draining, ordered reboot, and pool-level coordination, which the harness should not
re-implement. Third, the audit trail lands in the same place every other change does, so the
operator who reviews MCO changes weekly does not need a new tool for harness-driven changes.

## Q6. What's the rollback story?

Every AuditEvent carries a populated ReversibilityProfile (schema at
`harness/schemas/ReversibilityProfile.json`) with seven fields: rollback_intent,
blast_radius_if_reverse, rebuild_timeline, replication_history, validation_history,
risk_profile_burn_down, confidence_in_reversibility. Agentic Recoverability runs the inverse
action on the Digital Twin before the operator commits, and writes the verdict to the
validation_history field. See `talk/trust_loop.md` lines 56-67.

## Q7. What if the digital twin diverges from production?

EvalOps measures twin-vs-prod fidelity continuously as part of the same telemetry stream that
tracks agent accuracy. When fidelity drops below a threshold, the harness downgrades EvalOps
confidence on twin-passed proposals. Twin substrate is operationally flexible per
`talk/trust_loop.md` lines 24-28: a same-topology mirrored cluster OR a simulated linuxptp plus
NIC stack works. The architecture is twin-substrate-neutral.

## Q8. How does crisis_mode get activated and by whom?

A NOC supervisor sets `crisis_mode: true` in `harness/guardrails.yaml`. When active:
all write paths revoked (O2 IMS and SMO TMF921), EvalOps confidence pinned to zero, telemetry
routed to manual queue. Existing in-flight actions allowed to complete or roll back; no new
actions accepted. Full discussion at `talk/killswitch.md` (AT&T-reviewed per the document's
status line). Activation pathway in `harness/runtime/guardrail.py`; the
`test_evaluate_crisis_mode_active` test verifies the override.

## Q9. Is this Red Hat product code or research?

Research bench under Apache 2.0. Not product. The reference O2 IMS implementation cited
throughout IS Red Hat product (`openshift-kni/oran-o2ims`, `docs/references.md#ref-6`), but the
harness pattern itself is operationalization-agnostic. The contracts are portable to LangGraph,
OpenAI Agents SDK, Microsoft Semantic Kernel, or any agent framework that reads JSON Schema and
YAML.

## Q10. What scale has this been exercised at?

The four walkthrough scenarios under `scenarios/` are fixture-driven, exactly as committed. The
research bench at `5G_O-RAN_SIM/bench/` runs all four end-to-end deterministically. The
research foundation is a 1+ year Ericsson Red Hat Intel initiative where the speaker is the
solo Red Hat representative; the bench is the open-source crystallization, not the full
production deployment. Production-scale numbers belong to the partner engagement, not the bench.

## Q11. Where's the paper?

The repo IS the paper. The citation pyramid at `docs/references.md` (52 numbered AMA-style
refs), the narrative at `talk/architecture_narrative.md` anchored at file plus line, and the
runnable demo are the three layers. The verify gate (`scripts/verify.py`) gives a reviewer a
falsifiable yes/no on the structural claims. A traditional paper companion is possible if a
venue requires one, but is not the primary artifact.

## Q12. How portable is this beyond Ericsson?

The harness pattern is operationalization-agnostic. Three contributions: routing rule (declared
at `harness/routing-rules/contribution-1-routing-rule.yaml`), guardrail contract
(`harness/routing-rules/contribution-2-guardrail-contract.yaml` plus
`harness/guardrails.yaml`), LLM-neutrality
(`harness/routing-rules/contribution-3-llm-neutrality.yaml`). The contracts read identically
whether the partner SMO is Ericsson, Nokia, Amdocs, Mavenir, or ZTE. The TMF921 intent shape is
the standardized interop point.

## Q13. Is there a slide deck I can have?

The repo has more than the deck. Point reviewers at the repo URL plus
`talk/architecture_narrative.md` for the full walkthrough. Slide deck is out of scope for this
repo per the locked plan decision (see `talk/slides.md`).
