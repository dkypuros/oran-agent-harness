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
import os
import sys
from pathlib import Path
from typing import Any

import yaml

_RUNTIME_DIR = Path(__file__).resolve().parent
_HARNESS_DIR = _RUNTIME_DIR.parent
_REPO_ROOT = _HARNESS_DIR.parent

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
        hint = _resolve_ambiguous(rca)
        raise NotImplementedError(
            f"ambiguous_path LLM-assist returned a disambiguation hint: {hint!r}. "
            f"Router does not parse LLM responses into deterministic classifications in v0; "
            f"the seam is exercised but the resulting RemediationProposal is not auto-emitted."
        )
    else:
        raise ValueError(f"unknown target_layer {layer}")

    companion = _maybe_build_companion_intent(rca, proposal, scenario)
    if companion is not None:
        proposal["companion_intent"] = companion

    return proposal


def _resolve_ambiguous(rca: dict[str, Any]) -> str:
    """LLM-assist tier for ambiguous_path. Env-gated.

    Default (ORAN_LLM_MODE unset): raises NotImplementedError preserving the historical
    behavior so the existing verify gate at 10/10 PASS and the unit test
    test_route_ambiguous_raises are unaffected.

    Live (ORAN_LLM_MODE=live): imports the 5G_O-RAN_SIM/llm inference client and calls
    completion() with a disambiguation prompt built from the RCA's candidate classifications.
    Returns the LLM's textual response. The router's ambiguous branch then re-raises
    NotImplementedError with the hint included; the seam is exercised but the resulting
    classification is not auto-applied. Future work could parse the response into a
    deterministic classification.

    Bibliography refs: 13 (Anthropic MCP context), 17 (LiteLLM-style abstraction)
    """
    if os.environ.get("ORAN_LLM_MODE") != "live":
        raise NotImplementedError(
            "ambiguous_path requires LLM-assist tier, not implemented in stub runtime "
            "(set ORAN_LLM_MODE=live and configure 5G_O-RAN_SIM/.env to enable)"
        )
    sim_path = _REPO_ROOT / "5G_O-RAN_SIM"
    if str(sim_path) not in sys.path:
        sys.path.insert(0, str(sim_path))
    try:
        from llm.inference_client import completion
    except ImportError as exc:
        raise NotImplementedError(
            f"ambiguous_path live mode failed to import 5G_O-RAN_SIM/llm/inference_client: {exc}"
        ) from exc
    fault_id = rca.get("fault_id", "<unknown>")
    candidates = rca.get("candidate_classifications", [])
    prompt = (
        f"Disambiguate the following ambiguous fault classification for fault {fault_id}. "
        f"Candidates: {candidates}. "
        f"Return the most likely concrete classification (e.g. host_driver, ran_parameter) "
        f"and explain in one sentence."
    )
    return completion(prompt, tier="medium")


def _maybe_build_companion_intent(
    rca: dict[str, Any],
    proposal: dict[str, Any],
    scenario: dict[str, Any],
) -> dict[str, Any] | None:
    """Attach a TMF921 SMO companion intent for high-blast infra remediation.

    Returns a TMF921-shaped intent envelope when the proposal's blast radius
    forces SMO awareness (e.g. a node-rebooting firmware update). Returns None
    otherwise. The harness emits this alongside the down-route O2 IMS apply so
    the partner SMO can pre-handover, suppress alarms downstream, or adjust
    slice SLAs during the maintenance window.

    Trigger rule for v0: taxonomyMatch == "node_firmware" AND blast_radius
    nodes >= 1. Cell-level reach is the secondary teaching signal: firmware
    updates take a full host offline for the reboot window, so service-layer
    impact is non-trivial even if the deterministic classification is infra.

    Bibliography refs: 19 (TMF921 Intent Management API)
    """
    if proposal.get("taxonomyMatch") != "node_firmware":
        return None
    blast = scenario.get("blast_radius") or {}
    if blast.get("nodes", 0) < 1:
        return None
    return {
        "_conforms_to": {
            "spec": "TMF921 Intent Management API envelope, companion intent",
            "spec_section": "Intent expression between Intent Owner and Intent Handler",
            "spec_version": "TMF921 current",
            "bibliography_ref": [19],
        },
        "intent_id": f"INT-{rca.get('fault_id', 'unknown')}-companion",
        "intent_type": "MaintenanceWindowNotification",
        "affected_resources": [
            proposal.get("actionTarget", "node/unknown"),
        ],
        "service_impact_hint": "reduced_capacity",
        "expected_outage_window_minutes": 8,
        "issuer": "oran-agent-harness/router._maybe_build_companion_intent",
        "dispatch_route": "smo-tmf921-endpoint",
        "rationale": (
            "Firmware update via Metal3 requires host reboot; the partner SMO is "
            "notified in parallel so it can pre-handover cells and gate downstream "
            "alarms during the maintenance window."
        ),
    }
