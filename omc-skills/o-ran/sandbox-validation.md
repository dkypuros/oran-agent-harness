---
name: o-ran:sandbox-validation
description: Run the deterministic guardrail engine from harness/guardrails.yaml against a RemediationProposal, emit a TMF688-shaped AuditEvent with a populated reversibility_profile
argument-hint: "<path to remediation_proposal.json>"
level: 2
citation_anchor:
  inputs:
    - ../../harness/schemas/RemediationProposal.json
    - ../../harness/guardrails.yaml
  outputs:
    - ../../harness/schemas/AuditEvent.json
    - ../../harness/schemas/ReversibilityProfile.json
  bibliography_refs: [18]
---

# /o-ran:sandbox-validation

<Purpose>
Runs the LLM-free guardrail engine against a RemediationProposal. Emits a TMF688-shaped AuditEvent with a
populated ReversibilityProfile so the operator has the rollback contract at decision time, in the same
place every time and in the same shape every time.
</Purpose>

<Use_When>
- A RemediationProposal has been emitted by `/o-ran:remediate` and must be evaluated
- Operator wants to see what would happen, with which guardrails firing, before promotion
- Audit emission is required before any apply call enters the O-Cloud
</Use_When>

<Steps>

1. **Load RemediationProposal**: Read the file path provided as argument. Validate against
   `../../harness/schemas/RemediationProposal.json`.

1b. **Verify the sandbox verdict prerequisite (v0 two-key gate)**: confirm
   `proposal.sandbox_verdict` is present and populated. In the v0 walker, this block is
   attached by `../../harness/runtime/walker.py::sandbox_simulation()`, which reads the
   per-scenario `sandbox_verdict` from `../../harness/runtime/scenario_stubs.json` and stamps
   it onto the proposal before the guardrail runs. If `sandbox_verdict.apply_allowed` is
   `False`, the guardrail engine at gate 2 raises `ValueError` and the apply is blocked at the
   twin. This is the down-route half of the two-key authorization (operator approval is the
   up-route half). The block carries `apply_allowed` (bool), `verdict` (string), and `reason`
   (operator-facing summary). If the field is missing entirely, fail closed: the proposal was
   constructed outside the canonical walker path and is not eligible for the v0 sandbox gate.

2. **Run the guardrail engine** (from `../../harness/guardrails.yaml`):
   - Gate 1: `crisis_mode` global override. If active, raise RuntimeError immediately.
   - Gate 2: **sandbox apply-allowed**. Read `proposal.sandbox_verdict.apply_allowed` (set in
     Step 1b). If False, raise ValueError("sandbox_verdict.apply_allowed is False").
   - Gate 3: `action_allowlist`. `actionType` must be in the allowed list. Fail closed if not.
   - Gate 4: `blast_radius`. Count expected affected `nodes`, `sites`, `cells` based on the
     `actionTarget` and the action_type semantics. Must not exceed the v0 hard caps
     (max_nodes=1, max_sites=1, max_cells=4).
   - Gate 5: `require_human_approval`. If `actionType` is in the list, ensure
     `requiresHumanApproval` is true. (For v0, every action class requires human approval.)
   - Record outcome (pass / fail / warn), rules evaluated, and blast radius. Populate
     `RemediationProposal.guardrailResult`.

3. **Build the ReversibilityProfile** (per `../../harness/schemas/ReversibilityProfile.json`):
   - `rollback_intent`: the inverse intent for this action class
   - `blast_radius_if_reverse`: predicted scope of rollback (nodes, sites, cells, user impact)
   - `rebuild_timeline`: estimated minutes plus confidence band
   - `replication_history`: pattern usage and rollback count over the 30 day window
   - `validation_history`: twin runs and pass rate from the EvalOps signal
   - `risk_profile_burn_down`: initial risk, current risk, burn-down rate per minute
   - `confidence_in_reversibility`: operator-facing summary (high / medium / low)

4. **Build the AuditEvent** (per `../../harness/schemas/AuditEvent.json`):
   - `eventId` generated as `evt-<correlatedFaultId>-001`
   - `eventTime` set to now
   - `eventType: RemediationProposed`
   - `event.correlatedEventId` from the originating FaultPayload
   - `event.domain: oran-ocloud`
   - `event.remediation` carries the full RemediationProposal plus the ReversibilityProfile.
     For infra-layer (DOWN-route) proposals it also carries `o2ims_dispatch`, the O-Cloud
     Manager's DeploymentRequest response attached by `router.py::_call_o2ims_deploy()` via
     `5G_O-RAN_SIM/oam/o2ims_stub.deploy_request()`. The block carries `accepted`,
     `deploymentManagerId`, `deploymentRequestId`, `reconciler_target`, `ocm_version`, and
     `ocm_response` per O-RAN.WG6 O2 IMS Interface Specification ([refs 2, 3](../../docs/references.md#ref-2)).
     The operator sees this row before co-authorization so the O2 IMS hop is visible in the
     audit, not just synthesized as a path string.

5. **Emit**: Per `audit_sink: stdout+file` in guardrails.yaml v0, the AuditEvent is printed to stdout and
   appended to `audit.jsonl`. Production deployments swap the sink for Kafka, AMQ Streams, or a
   TMF688-conformant broker. Do NOT call apply tools here. The audit is the GATE; live apply requires
   operator promotion per the co_authorization commit_phase.

</Steps>

<Determinism_Contract>
The guardrail engine is LLM-FREE. Every decision in this skill is rule-driven and reproducible. The
ReversibilityProfile content may use EvalOps signals (counts, rates) that come from observed telemetry,
but the schema enforcement is deterministic.
</Determinism_Contract>

<Verification>
Output must validate against `../../harness/schemas/AuditEvent.json` AND the embedded reversibility_profile
must validate against `../../harness/schemas/ReversibilityProfile.json`. For the five walkthrough
scenarios (A_fw_lldp_agent, A_prime_ice_driver, D_phc_drift_hw_only, E_nic_firmware_update,
E_with_smo_reject), output must match the corresponding `scenarios/<id>/audit_event.json` on the
named material fields, including `sandbox_verdict.apply_allowed` and (where present)
`companion_intent.dispatch_result.accepted`. The negative-path test
`tests/test_runtime.py::test_evaluate_sandbox_block_when_apply_disallowed` proves the gate 2
behavior end-to-end.
</Verification>
