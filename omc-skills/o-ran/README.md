# OMC O-RAN Skill Bundle

Reference operationalization for the O-RAN Agent Harness. Four skills that exercise the declarative
contracts under `../../harness/` against the five walkthrough scenarios under `../../scenarios/`
(A_fw_lldp_agent, A_prime_ice_driver, D_phc_drift_hw_only, E_nic_firmware_update, E_with_smo_reject).

The harness pattern is operationalization-agnostic. This bundle provides one reference operationalization
via [oh-my-claudecode (OMC)](https://github.com/yeachan-heo/oh-my-claudecode), an extensible multi-agent
orchestration layer for Claude Code. The stub contracts (taxonomy, guardrails, schemas) are portable to
LangGraph, OpenAI Agents SDK, Microsoft Semantic Kernel, or any agent framework that can read JSON Schema
and YAML.

## What this bundle does

The four skills exercise the three architectural contributions from the talk:

| Skill                               | Talk contribution exercised                                | Reads from harness/                                          |
|-------------------------------------|------------------------------------------------------------|---------------------------------------------------------------|
| `/o-ran:troubleshoot`               | Diagnostic substrate (prior work, the floor we build on)   | schemas/FaultPayload.json, scenarios/*/fault_payload.json     |
| `/o-ran:remediate`                  | Contribution 1, routing rule                               | taxonomy.yaml, routing-rules/contribution-1-routing-rule.yaml, schemas/RemediationProposal.json |
| `/o-ran:sandbox-validation`         | Contribution 2, guardrail contract                         | guardrails.yaml, schemas/AuditEvent.json, schemas/ReversibilityProfile.json |
| `/o-ran:plan`                       | Orchestrating wrapper that chains the three above          | all of the above                                              |

Contribution 3, LLM-neutral substrate, is automatic because OMC already abstracts the model behind its
Skill tool routing (haiku, sonnet, opus) and supports provider swap via `omc ask <provider>`. See
`../../harness/routing-rules/contribution-3-llm-neutrality.yaml` for the declarative assertion.

## Installing

This bundle assumes oh-my-claudecode is installed in your Claude Code environment. If not:

```
# Install OMC per upstream docs
# https://github.com/yeachan-heo/oh-my-claudecode
```

Then drop the four skill markdown files (`plan.md`, `troubleshoot.md`, `remediate.md`,
`sandbox-validation.md`) into your OMC skills directory. Each file's frontmatter declares its OMC
metadata.

## Running the walkthroughs

```
# Scenario A, fw-lldp-agent host service interfering with PTP
/o-ran:plan scenarios/A_fw_lldp_agent/fault_payload.json

# Scenario A-prime, outdated ice driver causing PHC drift
/o-ran:plan scenarios/A_prime_ice_driver/fault_payload.json

# Scenario D, hardware-only PHC drift (no software layer routing)
/o-ran:plan scenarios/D_phc_drift_hw_only/fault_payload.json

# Scenario E, NIC firmware update with TMF921 companion intent (SMO accepts)
/o-ran:plan scenarios/E_nic_firmware_update/fault_payload.json

# Scenario E_with_smo_reject, same firmware path but SMO rejects the companion intent
/o-ran:plan scenarios/E_with_smo_reject/fault_payload.json
```

Each run reads a FaultPayload, walks the evidence chain, picks a routing direction via the deterministic
taxonomy lookup (with LLM-assist on ambiguous edges), evaluates against guardrails, and emits a TMF688
AuditEvent with a ReversibilityProfile.

The skill outputs are designed to match the shape of `scenarios/A_*/remediation.yaml` and
`scenarios/A_*/audit_event.json` on material fields (target_layer, taxonomy_match, action_type, dry_run,
requires_human_approval). The decision CONTENT may vary across LLM provider and model selection; the
envelope shape must not.

## File inventory

| File                  | Role                                                            |
|-----------------------|------------------------------------------------------------------|
| `plan.md`             | Orchestrator, chains troubleshoot -> remediate -> sandbox-validation |
| `troubleshoot.md`     | Reads a fault_payload, produces an RCA artifact                   |
| `remediate.md`        | Takes an RCA, runs the routing rule, emits a RemediationProposal  |
| `sandbox-validation.md` | Runs guardrails.yaml, emits an AuditEvent with reversibility_profile |
| `conformance.md`      | Proves each skill's inputs and outputs validate against harness/schemas/ |
| `README.md`           | This file                                                        |

## What this bundle is NOT

This is a REFERENCE operationalization. It is not a production agent platform. It does not call into a
live O-Cloud, a live SMO, or live RAN hardware. The walkthrough scenarios are fixture-driven, exactly as
they are in `scenarios/`. The runnable layer that wires these skills to real MCP servers (FastMCP over
stdio against `mcp-platform`, `mcp-ran`, `mcp-hardware`, `mcp-ocloud`) is intentionally out of scope for
this repo per the locked plan decision to ship stub-only on the main branch.
