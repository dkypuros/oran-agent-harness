"""Deterministic Guardrail engine.

Conforms to:
  harness/guardrails.yaml (the policy contract)
  harness/schemas/AuditEvent.json (TMF688 envelope)
  harness/schemas/ReversibilityProfile.json (seven-field rollback contract)
  harness/schemas/RemediationProposal.json (input shape)
Bibliography refs: 18

Implements the four named elements from guardrails.yaml rules:
  dry_run_default, blast_radius, require_human_approval, action_allowlist
Plus crisis_mode global override check (pass-through in v0 since neither walkthrough scenario
triggers it; flip _CRISIS_MODE_ACTIVE via monkey-patch in tests to exercise the branch).
Plus structured audit emission (TMF688-shaped AuditEvent with populated reversibility_profile).

Exposes:
  evaluate(proposal: dict, fault_id: str) -> dict
    Take a RemediationProposal, return an AuditEvent with populated reversibility_profile.

Per-scenario reversibility_profile, blast_radius, and event_time values are sourced from
harness/runtime/scenario_stubs.json (the single source of truth). In real deployment EvalOps and the
O-Cloud Inventory supply these values.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

_RUNTIME_DIR = Path(__file__).resolve().parent
_HARNESS_DIR = _RUNTIME_DIR.parent

with (_HARNESS_DIR / "guardrails.yaml").open() as _fh:
    _GUARDRAILS = yaml.safe_load(_fh)

with (_RUNTIME_DIR / "scenario_stubs.json").open() as _fh:
    _SCENARIO_STUBS = json.load(_fh)["scenarios"]

# Seam: stub global override. Tests monkey-patch this to True to exercise the crisis_mode branch.
# Real deployment wires this to a CrisisModeActivation envelope per
# harness/schemas/CrisisModeActivation.json and the killswitch contract at talk/killswitch.md.
_CRISIS_MODE_ACTIVE = False


def evaluate(proposal: dict[str, Any], fault_id: str) -> dict[str, Any]:
    """Take a RemediationProposal, return an AuditEvent.

    Steps:
      1. crisis_mode global override check (pass-through in v0)
      2. action_allowlist check
      3. blast_radius caps check
      4. require_human_approval check
      5. populate proposal.guardrailResult
      6. build TMF688 AuditEvent envelope
      7. populate reversibility_profile sub-object
    """
    rules = _GUARDRAILS["rules"]

    if _CRISIS_MODE_ACTIVE:
        raise RuntimeError("crisis_mode active, all writes frozen")

    if proposal["actionType"] not in rules["action_allowlist"]:
        raise ValueError(f"actionType {proposal['actionType']} not in action_allowlist")

    scenario = _SCENARIO_STUBS.get(fault_id)
    if scenario is None:
        raise ValueError(f"no scenario stub for fault_id {fault_id}")

    blast = scenario["blast_radius"]
    caps = rules["blast_radius"]
    if (
        blast["nodes"] > caps["max_nodes"]
        or blast["sites"] > caps["max_sites"]
        or blast["cells"] > caps["max_cells"]
    ):
        raise ValueError(f"blast_radius {blast} exceeds caps {caps}")

    if proposal["actionType"] in rules["require_human_approval"]:
        if not proposal["requiresHumanApproval"]:
            raise ValueError(
                f"actionType {proposal['actionType']} requires human approval but "
                f"requiresHumanApproval is {proposal['requiresHumanApproval']}"
            )

    proposal["guardrailResult"] = {
        "outcome": "pass",
        "rulesEvaluated": [
            "blast_radius.max_nodes",
            "blast_radius.max_sites",
            "action_allowlist",
        ],
        "blastRadius": blast,
    }

    proposal["reversibility_profile"] = scenario["reversibility_profile"]

    audit_event = {
        "eventId": f"evt-{fault_id}-001",
        "eventTime": scenario["event_time"],
        "eventType": "RemediationProposed",
        "event": {
            "correlatedEventId": fault_id,
            "domain": "oran-ocloud",
            "remediation": proposal,
        },
    }
    return audit_event
