# EvalOps and Validation in the O-RAN Agent Harness

This document is the implementation-level companion to `../talk/trust_loop.md`. The talk file is the narrative version. This file is the repo reference for what EvalOps means in this harness, what validation gates exist today, what is real in v0, and what remains stubbed until a larger deployment supplies live telemetry and a real digital twin.

## Short answer

EvalOps exists in v0 as a contract, schema surface, and future telemetry seam. It is not yet a live measurement service.

Validation is more concrete today. The repo already validates the harness through schema checks, sandbox verdicts, deterministic guardrails, scenario replay, and AuditEvent comparison. The assistant can explain the result, but the validation evidence comes from the harness.

## What is real today

| Surface | Status | Where it lives | What it proves |
| --- | --- | --- | --- |
| Remediation Router | Real | `harness/runtime/router.py` | RCA classifications route through deterministic taxonomy and routing rules. |
| Sandbox gate | Real gate with stubbed verdicts | `harness/runtime/walker.py::sandbox_simulation()` and `harness/runtime/guardrail.py::evaluate()` | A proposal must carry `sandbox_verdict.apply_allowed=true` before the guardrail engine continues. |
| Guardrail engine | Real | `harness/runtime/guardrail.py` plus `harness/guardrails.yaml` | Crisis mode, sandbox gate, action allowlist, blast radius, and human approval checks are deterministic Python. |
| AuditEvent emission | Real | `harness/runtime/guardrail.py` and `harness/schemas/AuditEvent.json` | Every accepted draft emits a TMF688-shaped audit envelope with remediation evidence. |
| ReversibilityProfile shape | Real schema and populated fixture data | `harness/schemas/ReversibilityProfile.json` and `scenarios/*/audit_event.json` | Operators see rollback intent, reverse blast radius, validation history, risk burn-down, and confidence in reversibility in the same place every time. |
| Scenario replay validation | Real | `scripts/verify.py` check 10 | Every committed scenario is walked end to end and compared against its expected `audit_event.json` material fields. |
| Schema validation | Real when `jsonschema` is installed | `scripts/verify.py` check 9 | FaultPayload, RemediationProposal, and ReversibilityProfile shapes validate against declared schemas. |
| Runtime tests | Real | `tests/test_runtime.py` | Tests cover sandbox blocking, crisis mode, SMO rejection capture, and O2 IMS down-route dispatch. |

## What is stubbed today

| Surface | Status | Replacement path |
| --- | --- | --- |
| Live EvalOps telemetry | Stubbed | Replace per-scenario `reversibility_profile` values in `harness/runtime/scenario_stubs.json` with real fleet telemetry. |
| Digital twin replay | Stubbed twin, real gate | Replace `scenario_stubs.json` `sandbox_verdict` blocks with a same-topology twin or simulated linuxptp plus NIC stack. Keep the `sandbox_verdict` contract unchanged. |
| Gateway, MCP servers, and domain agents | Stubbed in deterministic walker | Replace `stubbed_agents()` with real FastMCP servers and domain-agent nodes while preserving RCA schema output. |
| SMO TMF921 response | Stubbed | Replace `scenario_stubs.json` `smo_dispatch_outcome` with real partner SMO dispatch results. Keep `companion_intent.dispatch_result` unchanged. |
| Agentic Recoverability execution | Stubbed values, real profile shape | Replace rollback and validation fields with live inverse-action twin results. Keep the seven-field ReversibilityProfile schema unchanged. |

## Validation path in one pass

The deterministic walker takes a scenario through this pipeline:

```text
FaultPayload
  -> stubbed_agents()
RCA
  -> router.route()
RemediationProposal
  -> walker.sandbox_simulation()
RemediationProposal with sandbox_verdict
  -> guardrail.evaluate()
AuditEvent with ReversibilityProfile
```

The important enforcement point is the Sandbox gate. `walker.sandbox_simulation()` attaches a `sandbox_verdict`; `guardrail.evaluate()` refuses to continue if the verdict is missing or if `apply_allowed` is false. This makes the sandbox more than a diagram. In v0 the verdict is sourced from fixtures, but the gate is real.

## EvalOps contract

EvalOps is the operational discipline that grades agent quality over time. In the trust-loop model, EvalOps answers the question: is this agent reliable enough on this scenario class?

In v0, EvalOps is represented by fields already present in the AuditEvent path:

- `classificationConfidence` on the RemediationProposal
- `reversibility_profile.validation_history`
- `reversibility_profile.risk_profile_burn_down`
- `reversibility_profile.confidence_in_reversibility`
- crisis-mode policy field `evalops_confidence_floor` in `harness/guardrails.yaml`

Those fields are fixture-backed today. In production, a real EvalOps service would write those same fields from measured classifier accuracy, twin-vs-production fidelity, false-positive cost, rollback history, and provider drift.

## Operator-facing validation story

The operator never receives just a model answer. The operator receives an AuditEvent that captures:

- the router decision
- taxonomy match and confidence
- O2 IMS down-route dispatch details when the target is infrastructure
- TMF921 companion intent and `dispatch_result` when service context matters
- sandbox verdict and `apply_allowed`
- guardrail outcome and blast radius
- ReversibilityProfile fields
- pending human approval status

That is the practical validation process: evidence first, deterministic gates second, model explanation third.

## How to verify locally

Run:

```bash
pip install pyyaml jsonschema
python3 scripts/verify.py
```

The main checks for this topic are:

- check 9: schema validation of scenario artifacts, if `jsonschema` is installed
- check 10: end-to-end walker replay against committed `audit_event.json`
- tests under `tests/test_runtime.py` for sandbox block, crisis mode, SMO rejection capture, and O2 IMS dispatch

## Upgrade path

To turn v0 EvalOps into a live implementation, keep the schemas and swap the data sources:

1. Replace `scenario_stubs.json` sandbox verdicts with real digital-twin results.
2. Replace fixture ReversibilityProfile values with real EvalOps telemetry.
3. Store per-taxonomy classifier and LLM-assist accuracy over time.
4. Feed provider drift, false-positive cost, and rollback history into the AuditEvent.
5. Keep `guardrail.py` deterministic. EvalOps supplies evidence; it does not become an LLM prompt.

The contract is already in place. The next phase replaces fixture values with measured values behind the same fields.
