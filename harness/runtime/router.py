"""Deterministic Remediation Router.

Conforms to:
  harness/routing-rules/contribution-1-routing-rule.yaml (the rule)
  harness/taxonomy.yaml (the O-RAN.WG6 resource model lookup table)
  harness/schemas/RemediationProposal.json (the output shape)
Bibliography refs: 1, 2, 3, 19

The router consults taxonomy.yaml first (deterministic lookup). LLM-assist runs ONLY on the
ambiguous_path. Neither walkthrough scenario hits that path; both classify as infra-layer with high
confidence via the deterministic lookup.

Exposes:
  route(rca: dict) -> dict
    Take an RCA artifact, return a RemediationProposal that validates against the schema.

Per-scenario actionTarget, actionPayloadRef, contributingSignals, and proposalId are sourced from
harness/runtime/scenario_stubs.json (the single source of truth). In real deployment the Domain
Agents would attach them to the RCA's candidate_classifications.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

_RUNTIME_DIR = Path(__file__).resolve().parent
_HARNESS_DIR = _RUNTIME_DIR.parent

with (_HARNESS_DIR / "routing-rules" / "contribution-1-routing-rule.yaml").open() as _fh:
    _ROUTING_RULE = yaml.safe_load(_fh)

with (_RUNTIME_DIR / "scenario_stubs.json").open() as _fh:
    _SCENARIO_STUBS = json.load(_fh)["scenarios"]

_INFRA_DELIVERY_PATHS = {
    entry["taxonomy_id"]: entry
    for entry in _ROUTING_RULE["routing_rule"]["infra_to_ocloud_path"]["delivery_paths"]
}


def route(rca: dict[str, Any]) -> dict[str, Any]:
    """Take an RCA artifact, return a RemediationProposal.

    Deterministic taxonomy lookup against contribution-1-routing-rule.yaml. The top
    candidate_classification picks the infra delivery_path or the service smo route. The
    ambiguous_path raises NotImplementedError because neither walkthrough scenario hits it (and the
    stub runtime does not call an LLM).
    """
    if not rca.get("candidate_classifications"):
        raise ValueError("RCA has no candidate_classifications, cannot route")

    top = rca["candidate_classifications"][0]
    layer = top["target_layer"]
    fault_id = rca["fault_id"]
    scenario = _SCENARIO_STUBS.get(fault_id, {})

    proposal: dict[str, Any] = {
        "proposalId": scenario.get("proposalId", f"prop-{fault_id[4:]}"),
        "version": "v1alpha1",
        "targetLayer": layer,
        "classificationConfidence": top["confidence"],
        "classificationMethod": "deterministic",
        "taxonomyMatch": top["taxonomy_match"],
        "contributingSignals": scenario.get("contributingSignals", []),
        "actionTarget": scenario.get("actionTarget", ""),
        "actionPayloadRef": scenario.get("actionPayloadRef", ""),
        "dryRun": True,
        "requiresHumanApproval": True,
        "humanApprovalStatus": "pending",
    }

    if layer == "infra":
        path_entry = _INFRA_DELIVERY_PATHS.get(top["taxonomy_match"])
        if path_entry is None:
            raise ValueError(
                f"taxonomy_match {top['taxonomy_match']} has no infra delivery_path entry"
            )
        proposal["actionType"] = path_entry["action_type"]
        proposal["ocloudInternalPath"] = path_entry["ocloud_internal"]
    elif layer == "service":
        proposal["actionType"] = "emit_smo_intent"
        proposal["ocloudInternalPath"] = "smo-tmf921-endpoint"
    elif layer == "ambiguous":
        raise NotImplementedError(
            "ambiguous_path requires LLM-assist tier, not implemented in stub runtime"
        )
    else:
        raise ValueError(f"unknown target_layer {layer}")

    return proposal
