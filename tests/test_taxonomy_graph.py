"""Tests for the LangGraph-compatible taxonomy orchestration runner."""

from __future__ import annotations

from harness.runtime import taxonomy_graph


def test_load_taxonomy_flattens_canonical_yaml() -> None:
    taxonomy = taxonomy_graph.load_taxonomy()

    assert taxonomy["ptp_host_stack"]["layer"] == "infra"
    assert taxonomy["slice_intent"]["section"] == "service_layer"
    assert taxonomy["ptp_boundary"]["layer"] == "ambiguous"


def test_taxonomy_graph_fallback_walk_matches_existing_walker() -> None:
    runner = taxonomy_graph.TaxonomyGraphRunner(prefer_langgraph=False)

    result = runner.walk_fault_payload("scenarios/A_fw_lldp_agent/fault_payload.json")

    assert result.backend == "fallback"
    assert result.audit_event is not None
    assert result.audit_event["event"]["correlatedEventId"] == "flt-2026-05-14-001"
    remediation = result.audit_event["event"]["remediation"]
    assert remediation["taxonomyMatch"] == "ptp_host_stack"
    assert remediation["guardrailResult"]["outcome"] == "pass"
    assert taxonomy_graph.NODE_LOAD_TAXONOMY in result.node_trace
    assert taxonomy_graph.NODE_ROUTE in result.node_trace
    assert taxonomy_graph.NODE_SANDBOX in result.node_trace
    assert taxonomy_graph.NODE_GUARDRAIL in result.node_trace


def test_taxonomy_graph_blocks_ambiguous_classification_at_boundary() -> None:
    rca = {
        "fault_id": "flt-test-ambiguous",
        "timestamp": "2026-05-14T00:00:00Z",
        "evidence": [],
        "candidate_classifications": [
            {
                "taxonomy_match": "ptp_boundary",
                "target_layer": "ambiguous",
                "confidence": "medium",
                "rationale": "synthetic ambiguous edge",
            }
        ],
    }

    result = taxonomy_graph.TaxonomyGraphRunner(prefer_langgraph=False).invoke(rca)

    assert result.audit_event is None
    assert result.state["status"] == "blocked_ambiguous"
    assert "ambiguous_path" in result.state["ambiguity_status"]
    assert taxonomy_graph.NODE_ROUTE not in result.node_trace


def test_run_fault_payload_convenience_returns_audit_event() -> None:
    audit_event = taxonomy_graph.run_fault_payload("scenarios/A_prime_ice_driver/fault_payload.json")

    assert audit_event["eventType"] == "RemediationProposed"
    assert audit_event["event"]["remediation"]["taxonomyMatch"] == "host_driver"
