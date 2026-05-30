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

Per-scenario actionTarget and actionPayloadRef values come from a small stub table because in real
deployment the Domain Agents would attach them to the RCA's candidate_classifications. The stub
covers the two walkthrough scenarios.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

_RUNTIME_DIR = Path(__file__).resolve().parent
_HARNESS_DIR = _RUNTIME_DIR.parent
_REPO_ROOT = _HARNESS_DIR.parent

with (_HARNESS_DIR / "taxonomy.yaml").open() as _fh:
    _TAXONOMY = yaml.safe_load(_fh)

with (_HARNESS_DIR / "routing-rules" / "contribution-1-routing-rule.yaml").open() as _fh:
    _ROUTING_RULE = yaml.safe_load(_fh)

_INFRA_DELIVERY_PATHS = {
    entry["taxonomy_id"]: entry
    for entry in _ROUTING_RULE["routing_rule"]["infra_to_ocloud_path"]["delivery_paths"]
}

# Per-scenario actionTarget and actionPayloadRef. Real Domain Agents would emit these on the RCA.
# Stubbed here for the two walkthrough scenarios. Keyed by fault_id.
_SCENARIO_ACTION = {
    "flt-2026-05-14-001": {
        "actionTarget": "worker-ran-01.dallas.example.com",
        "actionPayloadRef": "99-worker-ran-disable-fw-lldp-agent",
        "contributingSignals": [
            "platform.ptp_host_stack.master_offset_anomaly",
            "platform.ptp_host_stack.state_unstable",
            "platform.ptp_host_stack.fw_lldp_agent_active",
            "platform.host_nic.tx_hwtstamp_timeouts",
        ],
        "proposalId": "prop-2026-05-14-001",
    },
    "flt-2026-05-14-002": {
        "actionTarget": "worker-ran-02.dallas.example.com",
        "actionPayloadRef": "ice-driver-update",
        "contributingSignals": [
            "platform.ptp_host_stack.phc_drift_monotonic",
            "platform.ptp_host_stack.state_uncalibrated",
            "platform.host_driver.version_outdated",
            "platform.host_driver.known_issue_match",
        ],
        "proposalId": "prop-2026-05-14-002",
    },
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
    scenario = _SCENARIO_ACTION.get(fault_id, {})

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


def taxonomy_entry(taxonomy_match: str) -> dict[str, Any] | None:
    """Lookup a taxonomy entry by id. Returns None if not present in any layer."""
    for layer in ("infra_layer", "service_layer", "ambiguous"):
        for entry in _TAXONOMY["resource_taxonomy"].get(layer, []):
            if entry["id"] == taxonomy_match:
                return entry
    return None
