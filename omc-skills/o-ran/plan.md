---
name: o-ran:plan
description: Orchestrating skill that chains o-ran:troubleshoot -> o-ran:remediate -> o-ran:sandbox-validation. End-to-end closed-loop walkthrough from a FaultPayload to a gated AuditEvent
argument-hint: "<path to fault_payload.json>"
level: 3
citation_anchor:
  inputs:
    - ../../harness/schemas/FaultPayload.json
  outputs:
    - ../../harness/schemas/AuditEvent.json
  chains:
    - ./troubleshoot.md
    - ./remediate.md
    - ./sandbox-validation.md
  bibliography_refs: [1, 2, 3, 17, 18, 19, 31, 35]
---

# /o-ran:plan

<Purpose>
End-to-end orchestrator for the closed-loop walkthrough. Takes a FaultPayload, runs diagnosis, runs the
routing rule, runs the guardrail engine, emits a TMF688 AuditEvent. The talk's three contributions all
exercise in one invocation.
</Purpose>

<Use_When>
- Stage demo of the closed-loop pattern from CloudEvent to AuditEvent
- Walkthrough of either of the two PTP scenarios end-to-end
- Verifying that the harness contracts compose into a working pipeline
</Use_When>

<Steps>

1. **Invoke `/o-ran:troubleshoot`** with the FaultPayload path. Capture the RCA artifact.

2. **Invoke `/o-ran:remediate`** with the RCA artifact. Capture the RemediationProposal.

3. **Invoke `/o-ran:sandbox-validation`** with the RemediationProposal. Capture the AuditEvent.

4. **Stop here**. Do NOT call apply tools. v0 is a contract demonstration, not a production enforcer.
   The operator reads the AuditEvent and decides whether to promote to the apply step out of band.

5. **Report**: Summarize the three artifacts plus the routing decision (up vs down), the guardrail
   outcome (pass / fail / warn), and the reversibility confidence (high / medium / low). One sentence
   each. This is the operator's headline at decision time.

</Steps>

<Why_This_Exists>
The three contributions from the abstract (routing rule, guardrail contract, LLM-neutral substrate) are
declarative contracts under `../../harness/`. The three skills above are their operational verbs. This
skill wires the verbs into a closed loop and proves the contracts compose.

LLM-neutrality (contribution 3) is exercised whenever OMC routes any of the three sub-skills' LLM calls
through its provider abstraction. Operators can swap providers via `omc ask <provider>` without changing
any skill body.
</Why_This_Exists>

<Verification>
End-to-end test for Scenario A: invoke with `scenarios/A_fw_lldp_agent/fault_payload.json`. Confirm:
- Output AuditEvent's `targetLayer` is "infra"
- `taxonomyMatch` is "ptp_host_stack"
- `actionType` is "apply_machine_config"
- `dryRun` is true
- `requiresHumanApproval` is true
- `reversibility_profile.confidence_in_reversibility` is "high"

End-to-end test for Scenario A-prime: invoke with
`scenarios/A_prime_ice_driver/fault_payload.json`. Confirm:
- Output AuditEvent's `targetLayer` is "infra"
- `taxonomyMatch` is "host_driver"
- `actionType` is "apply_kmm_module"
- `dryRun` is true
- `requiresHumanApproval` is true
- `reversibility_profile.confidence_in_reversibility` is "medium"

Both tests are part of the Phase 6 verify gate.
</Verification>
