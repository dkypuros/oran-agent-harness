# OMC O-RAN Skill Bundle, Conformance Index

Proves each skill in this bundle reads and writes data that validates against the harness contract set.
Companion to the central `../../harness/conformance.md`.

## Per-skill input and output schema mapping

| Skill                       | Input                                                                  | Output                                                                          | Bibliography refs |
|-----------------------------|-------------------------------------------------------------------------|----------------------------------------------------------------------------------|--------------------|
| `troubleshoot.md`           | `../../harness/schemas/FaultPayload.json` (FaultPayload)               | `../../harness/schemas/RCA.json` (RCA)                                          | 31, 35             |
| `remediate.md`              | `../../harness/schemas/RCA.json` (RCA) plus `../../harness/taxonomy.yaml` and `../../harness/routing-rules/contribution-1-routing-rule.yaml` | `../../harness/schemas/RemediationProposal.json` (RemediationProposal) | 1, 2, 3, 19        |
| `sandbox-validation.md`     | `../../harness/schemas/RemediationProposal.json` (RemediationProposal) plus `../../harness/guardrails.yaml` | `../../harness/schemas/AuditEvent.json` (AuditEvent) embedding `../../harness/schemas/ReversibilityProfile.json` | 18 |
| `plan.md`                   | `../../harness/schemas/FaultPayload.json` (FaultPayload)               | `../../harness/schemas/AuditEvent.json` (AuditEvent), end-to-end                | 1, 2, 3, 17, 18, 19, 31, 35 |

## End-to-end test mapping

| Test                                    | Input                                                              | Expected output match against                                       |
|------------------------------------------|---------------------------------------------------------------------|----------------------------------------------------------------------|
| Scenario A end-to-end                    | `../../scenarios/A_fw_lldp_agent/fault_payload.json`               | `../../scenarios/A_fw_lldp_agent/audit_event.json` on material fields |
| Scenario A-prime end-to-end              | `../../scenarios/A_prime_ice_driver/fault_payload.json`            | `../../scenarios/A_prime_ice_driver/audit_event.json` on material fields |
| Scenario D end-to-end                    | `../../scenarios/D_phc_drift_hw_only/fault_payload.json`           | `../../scenarios/D_phc_drift_hw_only/audit_event.json` on material fields |
| Scenario E end-to-end (accepted)         | `../../scenarios/E_nic_firmware_update/fault_payload.json`         | `../../scenarios/E_nic_firmware_update/audit_event.json` on material fields |
| Scenario E end-to-end (SMO reject)       | `../../scenarios/E_with_smo_reject/fault_payload.json`             | `../../scenarios/E_with_smo_reject/audit_event.json` on material fields |

Material fields (the fields that must match exactly, not just shape): `targetLayer`, `taxonomyMatch`,
`actionType`, `ocloudInternalPath`, `dryRun`, `requiresHumanApproval`,
`reversibility_profile.confidence_in_reversibility`,
`sandbox_verdict.apply_allowed` (v0 two-key gate, set by walker's `sandbox_simulation()`),
`companion_intent.dispatch_result.accepted` (v0 SMO outcome, set by router's
`_maybe_attach_dispatch_result()` from `harness/runtime/scenario_stubs.json`),
`o2ims_dispatch.accepted` (v0 O-RAN O2 IMS hop outcome, set by router's `_call_o2ims_deploy()`
via `5G_O-RAN_SIM/oam/o2ims_stub.deploy_request()`; absent on service-layer routes).

Non-material fields (may differ across LLM provider, model, or run): timestamps, contributingSignals
ordering, free-text descriptions, validation_history.last_twin_run_at.

## How the Phase 6 verify gate uses this index

The gate runs the two end-to-end tests above. For each, it loads the input FaultPayload, invokes
`/o-ran:plan`, captures the final AuditEvent, and diffs against the reference scenario audit_event.json
on the named material fields. Any mismatch on a material field fails the gate.

The gate also runs JSON Schema validation against the input and output of each individual skill, not just
the end-to-end pipeline. A skill that produces output not validating against its declared output schema
fails the gate even if the end-to-end test passes accidentally.
