# Walkthrough scenarios

Two PTP host-platform scenarios exercise the harness pipeline end to end. The walker at
`harness/runtime/walker.py` reads a FaultPayload from a scenario folder and produces an AuditEvent.
Every intermediate artifact (FaultPayload, RCA, RemediationProposal, AuditEvent) validates against a
JSON Schema under `harness/schemas/`.

## The two scenarios

| Scenario              | Fault                                       | Remediation                                            | Internal path          |
|-----------------------|----------------------------------------------|---------------------------------------------------------|------------------------|
| `A_fw_lldp_agent/`    | fw-lldp-agent.service contending for PHC    | MachineConfig (systemd unit mask)                       | machine-config-operator |
| `A_prime_ice_driver/` | ice driver 1.11.17 PHC drift regression     | KMM Module CR (swap ice 1.11.x for 1.13.7+ via OOT build) | kernel-module-management |

## The pipeline (four stages, three contracts)

```
FaultPayload (in)
  -> stubbed_agents       (Gateway + MCP servers + Domain Agents, all stubbed)
RCA
  -> route()              (real Router: taxonomy.yaml lookup, contribution-1-routing-rule.yaml)
RemediationProposal
  -> stubbed_twin         (Digital Twin Sandbox pass, stubbed twin_pass_rate 1.0)
RemediationProposal (twin verdict attached)
  -> evaluate()           (real Guardrail engine: guardrails.yaml rules, AuditEvent emission)
AuditEvent (out)          (TMF688-shaped envelope plus populated reversibility_profile)
```

Each stage emits an artifact that validates against a JSON Schema in `harness/schemas/`:

- FaultPayload.json validates the inbound CloudEvent
- RCA.json validates the cross-domain evidence chain
- RemediationProposal.json validates the Router output
- AuditEvent.json validates the TMF688 envelope (and ReversibilityProfile.json validates the
  reversibility_profile sub-object inside it)

## What is stubbed and what is real

| Component                  | Mode    | Notes                                                                 |
|----------------------------|---------|----------------------------------------------------------------------|
| Agentic Gateway            | STUBBED | The FaultPayload is loaded directly from disk, no inbound MCP flow   |
| 4 MCP servers              | STUBBED | The FaultPayload.evidence array carries what the servers would emit  |
| 3 Domain Agents            | STUBBED | `stubbed_agents` re-shapes evidence into RCA shape                   |
| Knowledge Base (RAG)       | STUBBED | Not consulted because neither scenario hits ambiguous_path           |
| **Remediation Router**     | REAL    | `harness/runtime/router.py`: taxonomy lookup, deterministic           |
| LLM-neutral substrate      | STUBBED | LiteLLM is not called (no ambiguous_path hits in either scenario)    |
| Digital Twin               | STUBBED | `stubbed_twin` returns canned pass-allowed                           |
| EvalOps                    | STUBBED | reversibility_profile values from per-scenario stub table            |
| Sandbox                    | STUBBED | twin_pass_rate 1.0 always                                            |
| Agentic Recoverability     | STUBBED | rollback_intent shape inferred from actionType                       |
| **Guardrail Engine**       | REAL    | `harness/runtime/guardrail.py`: action_allowlist, blast_radius, etc.  |
| Audit emission             | REAL    | TMF688-shaped AuditEvent printed to stdout                           |

The two REAL components (Router and Guardrail engine) are the deterministic core. The walker's
output is fully reproducible across runs because the only non-deterministic component (LiteLLM) is
only called on the ambiguous_path, which neither scenario hits.

## Running the demo

From the repo root:

```bash
./scripts/demo.sh
```

That walks both scenarios with `--verbose`, printing each pipeline stage to stdout.

Or run a single scenario directly:

```bash
python3 -m harness.runtime.walker scenarios/A_fw_lldp_agent/fault_payload.json
```

Without `--verbose`, only the final AuditEvent prints.

## Per-scenario fixtures

Each scenario folder contains:

```
A_fw_lldp_agent/
  fault_payload.json         the inbound CloudEvent shape (FaultPayload)
  rca.json                   the expected output of stubbed_agents
  remediation_proposal.json  the expected output of route()
  remediation.yaml           the actual MachineConfig or KMM Module CR the harness would apply
  audit_event.json           the expected final TMF688 AuditEvent with reversibility_profile
```

The walker's output matches `audit_event.json` on these material fields:

- event.remediation.targetLayer
- event.remediation.taxonomyMatch
- event.remediation.actionType
- event.remediation.ocloudInternalPath
- event.remediation.actionPayloadRef
- event.remediation.dryRun
- event.remediation.requiresHumanApproval
- event.remediation.reversibility_profile.confidence_in_reversibility

Verify gate check #10 enforces this match.

## Expected output

Scenario A (fw_lldp_agent): targetLayer infra, taxonomyMatch ptp_host_stack, actionType
apply_machine_config, ocloudInternalPath machine-config-operator, actionPayloadRef
99-worker-ran-disable-fw-lldp-agent, dryRun true, requiresHumanApproval true,
confidence_in_reversibility high.

Scenario A-prime (ice_driver): targetLayer infra, taxonomyMatch host_driver, actionType
apply_kmm_module, ocloudInternalPath kernel-module-management, actionPayloadRef ice-driver-update,
dryRun true, requiresHumanApproval true, confidence_in_reversibility medium.

## Moving to a bigger environment

When you graduate from stubs to real components, swap them one at a time. The contracts at every
seam stay the same:

1. Replace stubbed_agents with real FastMCP servers per harness/mcp-tool-schemas/, plus three real
   LangGraph nodes per omc-skills/o-ran/troubleshoot.md.
2. Replace stubbed_twin with a real Digital Twin (same-topology cluster or simulated subset). The
   contract (twin_pass_rate, last_twin_run_at) lives in ReversibilityProfile.json.
3. Replace the per-scenario stub tables in router.py and guardrail.py with values sourced from
   real EvalOps telemetry. The schemas already mandate the field shapes.

The Router and Guardrail engine stay as deterministic Python. They are the talk's research-credible
move and they should not become LLM prompts.
