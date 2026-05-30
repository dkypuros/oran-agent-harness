---
name: oran-discover:guardrail
description: Survey the deterministic guardrail policy. Report action allowlist, blast radius caps, dry-run defaults, co-authorization requirements, and crisis_mode triggers.
argument-hint: "(no arguments)"
level: 1
citation_anchor:
  inputs:
    - ../../harness/guardrails.yaml
    - ../../harness/runtime/guardrail.py
  outputs:
    - ../../harness/schemas/AuditEvent.json
  bibliography_refs: [18]
---

# /oran-discover:guardrail

<Purpose>
Survey the deterministic safety surface that gates every remediation before it becomes a live
action. The guardrail engine is LLM-free by design: a static policy file (`harness/guardrails.yaml`)
and a deterministic Python evaluator (`harness/runtime/guardrail.py`). This skill prints what the
policy currently allows and forbids.
</Purpose>

<Use_When>
- Reviewer is walking the sandbox / operator seam and wants the policy concrete instead of prose
- Operator wants to confirm crisis_mode is or is not active before authorizing anything
- Pre-talk dry-run: confirm the action allowlist covers the actions the scenarios will fire
- Auditor wants to inspect the policy as the source of truth (the policy is the contract)
</Use_When>

<Steps>

1. **Read the policy.** Static mode only (no HTTP wrapper; the policy is declarative).
   - Read `harness/guardrails.yaml`
   - Read `harness/runtime/guardrail.py` so the operator sees the evaluator that enforces it

2. **Surface the four guardrail pillars.** The policy organizes around:
   - **action_allowlist**: which action_type values the harness is allowed to propose at all
   - **blast_radius caps**: max nodes, max sites, max cells per single action (v0 = 1 node,
     1 site, 4 cells)
   - **dry_run defaults**: which action types default to dry-run-required
   - **requires_human_approval**: which action types REQUIRE explicit operator co-authorization

3. **Surface the crisis_mode block.** Per `harness/guardrails.yaml`, crisis_mode is the global
   override. When active:
   - All write paths revoked (O2 IMS, SMO TMF921)
   - EvalOps confidence pinned to zero
   - Telemetry routed to manual queue
   - Existing in-flight actions allowed to complete or roll back, but no new actions accepted

   This skill should print the current crisis_mode flag value if discoverable, otherwise print
   "crisis_mode default: false" and explain how to set it.

4. **Print the AuditEvent shape.** Every gated decision produces a TMF688 AuditEvent
   ([ref 18](../../docs/references.md#ref-18)). The shape is
   `harness/schemas/AuditEvent.json`. Print the top-level fields so the operator knows what to
   expect in the audit log.

5. **Two-key gate reminder.** The guardrail is half of the two-key authorization. The other half
   is the sandbox / digital-twin pass. Surface this: the operator authorizes the ACTION CLASS;
   the twin authorizes the SPECIFIC PAYLOAD.

6. **Citation footer.** TMF688 ([ref 18](../../docs/references.md#ref-18)).

</Steps>

<Determinism_Contract>
The guardrail engine is LLM-free. This skill reads YAML and prints structured output. No LLM call.
</Determinism_Contract>

<Verification>
- Source path: `harness/guardrails.yaml`.
- Evaluator: `harness/runtime/guardrail.py`.
- Output contract: `harness/schemas/AuditEvent.json`.
- The verify gate's walker_e2e check runs the evaluator end-to-end against every committed
  scenario fixture; this skill's output is what the operator would see in a live audit log.
</Verification>
