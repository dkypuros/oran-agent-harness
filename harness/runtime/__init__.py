"""Stubbed runtime walker for the O-RAN Agent Harness.

Conforms to:
  harness/routing-rules/contribution-1-routing-rule.yaml (routing logic)
  harness/guardrails.yaml (guardrail policy)
  harness/taxonomy.yaml (O-RAN.WG6 resource model lookup)
Bibliography refs: 1, 2, 3, 17, 18, 19

Components:
  router.py     deterministic Remediation Router (real). Reads taxonomy + routing rule at import.
  guardrail.py  deterministic Guardrail engine (real). Reads guardrails.yaml at import.
  walker.py     orchestrator. Stubs Gateway / MCP / Domain Agents / Digital Twin. Real Router + Guardrail.

Stubbed vs real:
  REAL: Router (taxonomy lookup), Guardrail engine (rule evaluation), AuditEvent emission
  STUB: Gateway, MCP servers, Domain Agents (canned RCA from FaultPayload evidence array)
  STUB: Digital Twin, Sandbox, Agentic Recoverability (canned twin_pass_rate 1.0)

When you later move to a bigger environment, swap stubs for real components one at a time. The
contracts at every seam stay the same.
"""
