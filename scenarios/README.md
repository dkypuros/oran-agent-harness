# Walkthrough scenarios

Five PTP host-platform scenarios exercise the harness pipeline end to end. The walker at
`harness/runtime/walker.py` reads a FaultPayload from a scenario folder and produces an AuditEvent.
Every intermediate artifact (FaultPayload, RCA, RemediationProposal, AuditEvent) validates against a
JSON Schema under `harness/schemas/`.

## The five scenarios

| Scenario                | Fault                                                       | Remediation                                                | Internal path             | Dual-route |
|-------------------------|-------------------------------------------------------------|------------------------------------------------------------|---------------------------|------------|
| `A_fw_lldp_agent/`      | fw-lldp-agent.service contending for PHC                    | MachineConfig (systemd unit mask)                          | machine-config-operator   | no         |
| `A_prime_ice_driver/`   | ice driver 1.11.17 PHC drift regression                     | KMM Module CR (swap ice 1.11.x for 1.13.7+ via OOT build)  | kernel-module-management  | no         |
| `D_phc_drift_hw_only/`  | software-LOCKED vs hardware-NOT-OK divergence (ice 1.11.17) | KMM Module CR (same swap, divergence forces hardware-side) | kernel-module-management  | no         |
| `E_nic_firmware_update/`| Intel E810 NIC firmware 4.40 PHC bug (KB 8731)              | Metal3 HostFirmwareComponents apply (firmware 4.50+)       | metal3-baremetal-operator | yes, SMO accepts |
| `E_with_smo_reject/`    | Same firmware bug on worker-ran-03                          | Metal3 apply attempted; SMO rejects companion intent       | metal3-baremetal-operator | yes, SMO rejects |

## The pipeline (five stages, four contracts)

```
FaultPayload (in)
  -> stubbed_agents       (Gateway + MCP servers + Domain Agents, all stubbed)
RCA
  -> route()              (real Router: taxonomy.yaml lookup, contribution-1-routing-rule.yaml,
                           plus _maybe_build_companion_intent + dispatch_result capture for node_firmware)
RemediationProposal
  -> sandbox_simulation   (real Sandbox stage: reads twin verdict from scenario_stubs.json,
                           attaches sandbox_verdict to proposal)
RemediationProposal (sandbox verdict attached)
  -> evaluate()           (real Guardrail engine: crisis_mode + sandbox apply-allowed gate +
                           guardrails.yaml rules, AuditEvent emission)
AuditEvent (out)          (TMF688-shaped envelope plus populated reversibility_profile, plus
                           companion_intent with dispatch_result for dual-route scenarios)
```

Each stage emits an artifact that validates against a JSON Schema in `harness/schemas/`:

- FaultPayload.json validates the inbound CloudEvent
- RCA.json validates the cross-domain evidence chain
- RemediationProposal.json validates the Router output
- AuditEvent.json validates the TMF688 envelope (and ReversibilityProfile.json validates the
  reversibility_profile sub-object inside it)

## What is stubbed and what is real

| Component                  | Mode    | Notes                                                                              |
|----------------------------|---------|------------------------------------------------------------------------------------|
| Agentic Gateway            | STUBBED | The FaultPayload is loaded directly from disk, no inbound MCP flow                 |
| 4 MCP servers              | STUBBED | The FaultPayload.evidence array carries what the servers would emit                |
| 3 Domain Agents            | STUBBED | `stubbed_agents` re-shapes evidence into RCA shape                                 |
| Knowledge Base (RAG)       | STUBBED | Not consulted because no committed scenario hits ambiguous_path                    |
| **Remediation Router**     | REAL    | `harness/runtime/router.py`: taxonomy lookup, deterministic; emits companion_intent and captures dispatch_result for node_firmware |
| LLM-neutral substrate      | STUBBED | Inference client wired in `5G_O-RAN_SIM/llm/`; ambiguous_path env-gated by ORAN_LLM_MODE=live, not triggered by committed scenarios |
| **Sandbox stage**          | REAL    | `harness/runtime/walker.py sandbox_simulation()`: attaches the twin verdict to the proposal; the verdict comes from scenario_stubs.json (twin replay STUBBED, gate REAL) |
| EvalOps                    | STUBBED | reversibility_profile values from per-scenario stub table                          |
| Twin replay                | STUBBED | scenario_stubs.json sandbox_verdict blocks; gate fires on apply_allowed=False      |
| SMO TMF921 response        | STUBBED | scenario_stubs.json smo_dispatch_outcome blocks; captured into companion_intent.dispatch_result |
| Agentic Recoverability     | STUBBED | rollback_intent shape inferred from actionType                                     |
| **Guardrail Engine**       | REAL    | `harness/runtime/guardrail.py`: crisis_mode, sandbox apply-allowed, action_allowlist, blast_radius, require_human_approval |
| Audit emission             | REAL    | TMF688-shaped AuditEvent printed to stdout, persisted to shared_trace JSONL        |

The REAL components (Router, Sandbox gate, Guardrail engine, Audit emission) are the
deterministic core. The walker's output is fully reproducible across runs because the only
non-deterministic component (the LLM substrate) is only called on ambiguous_path, which no
committed scenario hits.

For the implementation-level EvalOps and validation status, including what is real versus stubbed in v0, see `../docs/evalops-and-validation.md`.

## Running the demo

From the repo root:

```bash
./scripts/demo.sh
```

That walks the committed scenarios with `--verbose`, printing each pipeline stage to stdout.

Or run a single scenario directly:

```bash
python3 -m harness.runtime.walker scenarios/A_fw_lldp_agent/fault_payload.json
python3 -m harness.runtime.walker scenarios/E_with_smo_reject/fault_payload.json
```

Without `--verbose`, only the final AuditEvent prints.

## Per-scenario fixtures

Each scenario folder contains:

```
A_fw_lldp_agent/
  fault_payload.json         the inbound CloudEvent shape (FaultPayload)
  rca.json                   the expected output of stubbed_agents
  remediation_proposal.json  the expected output of route() + sandbox_simulation
  remediation.yaml           the actual MachineConfig or KMM or Metal3 CR the harness would apply
  audit_event.json           the expected final TMF688 AuditEvent with reversibility_profile,
                             sandbox_verdict, and (for dual-route scenarios) companion_intent
                             with dispatch_result
```

The walker's output matches `audit_event.json` on these material fields:

- event.remediation.targetLayer
- event.remediation.taxonomyMatch
- event.remediation.actionType
- event.remediation.ocloudInternalPath
- event.remediation.actionPayloadRef
- event.remediation.dryRun
- event.remediation.requiresHumanApproval
- event.remediation.sandbox_verdict.apply_allowed
- event.remediation.companion_intent.dispatch_result.accepted (for dual-route scenarios)
- event.remediation.reversibility_profile.confidence_in_reversibility

Verify gate check #10 enforces this match across all five committed scenarios.

## Expected output (summary)

Scenario A (fw_lldp_agent): targetLayer infra, taxonomyMatch ptp_host_stack, actionType
apply_machine_config, machine-config-operator, dryRun true, requiresHumanApproval true,
sandbox apply_allowed true, no companion_intent, confidence_in_reversibility high.

Scenario A-prime (ice_driver): targetLayer infra, taxonomyMatch host_driver, actionType
apply_kmm_module, kernel-module-management, sandbox apply_allowed true, no companion_intent,
confidence_in_reversibility medium.

Scenario D (phc_drift_hw_only): targetLayer infra, taxonomyMatch host_driver, actionType
apply_kmm_module, kernel-module-management, sandbox apply_allowed true, no companion_intent,
confidence_in_reversibility medium. The teaching contrast is in the FaultPayload evidence:
software-LOCKED plus hardware-NOT-OK divergence pattern.

Scenario E (nic_firmware_update): targetLayer infra, taxonomyMatch node_firmware, actionType
apply_metal3_firmware, metal3-baremetal-operator, sandbox apply_allowed true, companion_intent
with dispatch_result.accepted true, confidence_in_reversibility medium. The dual-route teaching
moment.

Scenario E_with_smo_reject: identical pipeline to E but on worker-ran-03; companion_intent
dispatch_result.accepted false, rejection_reason neighboring_cells_at_capacity. The operator
is the reconciliation point.

## Moving to a bigger environment

When you graduate from stubs to real components, swap them one at a time. The contracts at every
seam stay the same:

1. Replace stubbed_agents with real FastMCP servers per harness/mcp-tool-schemas/, plus three real
   LangGraph nodes per omc-skills/o-ran/troubleshoot.md.
2. Replace the scenario_stubs.json sandbox_verdict block with a real Digital Twin (same-topology
   cluster or simulated subset). The contract (twin_converged, baseline_match, apply_allowed)
   lives in the proposal's sandbox_verdict field; the gate logic in guardrail.py does not change.
3. Replace the scenario_stubs.json smo_dispatch_outcome block with real TMF921 emission to the
   partner SMO endpoint. The companion_intent.dispatch_result shape stays the same.
4. Replace the per-scenario reversibility_profile values in scenario_stubs.json with values
   sourced from real EvalOps telemetry. The schemas already mandate the field shapes.

The Router, Sandbox gate, and Guardrail engine stay as deterministic Python. They are the talk's
research-credible move and they should not become LLM prompts.
