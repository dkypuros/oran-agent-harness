---
name: o-ran:remediate
description: Take an RCA artifact, run the routing rule from contribution-1-routing-rule.yaml against taxonomy.yaml, emit a RemediationProposal conforming to harness/schemas/RemediationProposal.json
argument-hint: "<path to rca.json>"
level: 2
citation_anchor:
  inputs:
    - ../../harness/schemas/RCA.json
    - ../../harness/taxonomy.yaml
    - ../../harness/routing-rules/contribution-1-routing-rule.yaml
  outputs:
    - ../../harness/schemas/RemediationProposal.json
  bibliography_refs: [1, 2, 3, 19]
---

# /o-ran:remediate

<Purpose>
Takes an RCA artifact emitted by `/o-ran:troubleshoot`. Runs the routing rule. Produces a
RemediationProposal that either routes DOWN to the O-Cloud via O2 IMS (infra-layer actions) or UP to the
partner SMO via TMF921 intent (service-layer actions).
</Purpose>

<Use_When>
- An RCA artifact is ready and the operator wants a proposed remediation
- Walking either of the two PTP scenarios through the closed-loop pipeline
</Use_When>

<Steps>

1. **Load RCA**: Read the file path provided as argument. Validate against
   `../../harness/schemas/RCA.json`.

2. **Pick the top candidate classification**: From `candidate_classifications`, select the entry with the
   highest confidence. If the top entry's `target_layer` is "ambiguous", the routing rule's
   `ambiguous_path` runs an LLM-assist disambiguation that consults the evidence chain and the knowledge
   base. The disambiguated layer (infra or service) is what the rule then routes on.

3. **Apply the routing rule** (from `../../harness/routing-rules/contribution-1-routing-rule.yaml`):
   - If `target_layer == "infra"`: look up the matching `delivery_paths` entry by `taxonomy_id`. The entry
     specifies the `ocloud_internal` (machine-config-operator, kernel-module-management, etc.) and
     `action_type` (apply_machine_config, apply_kmm_module, etc.).
   - If `target_layer == "service"`: route to `service_to_smo_path` with `action_type: emit_smo_intent`.
     The harness does NOT execute service-layer actions; it emits a TMF921-style intent to the partner SMO.

4. **Build RemediationProposal**: Construct a JSON document conforming to
   `../../harness/schemas/RemediationProposal.json`:
   - `proposalId` generated as `prop-<date>-<seq>`
   - `version: v1alpha1`
   - `targetLayer` from step 2
   - `classificationConfidence`, `classificationMethod`, `taxonomyMatch` from the RCA
   - `contributingSignals` derived from the evidence chain
   - `actionType` and `ocloudInternalPath` from step 3
   - `actionTarget` from the RCA fault node
   - `actionPayloadRef` is the canonical name of the MachineConfig, Module, or intent document
   - `dryRun: true` (guardrails.yaml dry_run_default is true)
   - `requiresHumanApproval: true` (always for v0)
   - `humanApprovalStatus: pending`
   - `guardrailResult` is empty here; populated by `/o-ran:sandbox-validation`.

5. **Hand off**: The RemediationProposal goes to `/o-ran:sandbox-validation`. Do NOT call apply tools
   directly. The guardrail contract must evaluate before any apply.

</Steps>

<Determinism_Contract>
The routing decision is grounded in O-RAN's resource layering, not in a model's opinion. The deterministic
taxonomy lookup runs first; LLM-assist runs only on `ambiguous` edges. The talk's single most
research-credible move is right here.
</Determinism_Contract>

<Verification>
Output must validate against `../../harness/schemas/RemediationProposal.json`. For the two walkthrough
scenarios, the output must match the corresponding `scenarios/A_*/remediation.yaml` payload reference on
material fields (target_layer, taxonomy_match, action_type, dryRun, requiresHumanApproval).
</Verification>
