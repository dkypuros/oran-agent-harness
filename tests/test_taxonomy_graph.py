"""Tests for the LangGraph-compatible taxonomy orchestration runner."""

from __future__ import annotations

import pytest

from harness.runtime import taxonomy_graph, walker


def _rca(taxonomy_match: str, target_layer: str | None = None) -> dict[str, object]:
    candidate: dict[str, object] = {
        "taxonomy_match": taxonomy_match,
        "confidence": "medium",
        "rationale": "synthetic graph test",
    }
    if target_layer is not None:
        candidate["target_layer"] = target_layer
    return {
        "fault_id": "flt-test-graph",
        "timestamp": "2026-05-14T00:00:00Z",
        "evidence": [],
        "candidate_classifications": [candidate],
    }


def test_load_taxonomy_flattens_canonical_yaml() -> None:
    taxonomy = taxonomy_graph.load_taxonomy()

    assert taxonomy["ptp_host_stack"]["layer"] == "infra"
    assert taxonomy["slice_intent"]["section"] == "service_layer"
    assert taxonomy["ptp_boundary"]["layer"] == "ambiguous"


def test_taxonomy_graph_fallback_walk_matches_existing_walker() -> None:
    runner = taxonomy_graph.TaxonomyGraphRunner(prefer_langgraph=False)
    scenario = "scenarios/A_fw_lldp_agent/fault_payload.json"

    result = runner.walk_fault_payload(scenario)

    assert result.backend == "fallback"
    assert result.audit_event == walker.walk(scenario)
    remediation = result.audit_event["event"]["remediation"]  # type: ignore[index]
    assert remediation["taxonomyMatch"] == "ptp_host_stack"
    assert remediation["guardrailResult"]["outcome"] == "pass"
    assert result.node_trace == (
        taxonomy_graph.NODE_LOAD_TAXONOMY,
        taxonomy_graph.NODE_CLASSIFY,
        taxonomy_graph.NODE_ROUTE,
        taxonomy_graph.NODE_SANDBOX,
        taxonomy_graph.NODE_GUARDRAIL,
    )


def test_taxonomy_graph_normalizes_missing_layer_from_taxonomy() -> None:
    normalized = taxonomy_graph.normalize_rca_with_taxonomy(
        _rca("ran_parameter"),
        taxonomy_graph.load_taxonomy(),
    )

    top = normalized["candidate_classifications"][0]
    assert top["target_layer"] == "service"
    assert top["taxonomy_entry"]["section"] == "service_layer"


def test_taxonomy_graph_rejects_unknown_taxonomy_match() -> None:
    runner = taxonomy_graph.TaxonomyGraphRunner(prefer_langgraph=False)

    with pytest.raises(ValueError, match="not found in taxonomy.yaml"):
        runner.invoke(_rca("not_a_real_taxonomy_id", "infra"))


def test_taxonomy_graph_rejects_layer_mismatch() -> None:
    runner = taxonomy_graph.TaxonomyGraphRunner(prefer_langgraph=False)

    with pytest.raises(ValueError, match="target_layer mismatch for host_driver"):
        runner.invoke(_rca("host_driver", "service"))

    with pytest.raises(ValueError, match="target_layer mismatch for ptp_boundary"):
        runner.invoke(_rca("ptp_boundary", "infra"))


def test_taxonomy_graph_blocks_ambiguous_classification_at_boundary() -> None:
    result = taxonomy_graph.TaxonomyGraphRunner(prefer_langgraph=False).invoke(
        _rca("ptp_boundary", "ambiguous")
    )

    assert result.audit_event is None
    assert result.state["status"] == "blocked_ambiguous"
    assert result.state["ambiguity_status"] == "blocked_for_human_review"
    assert "ambiguous_path" in result.state["ambiguity_hint"]
    assert taxonomy_graph.NODE_ROUTE not in result.node_trace


def test_taxonomy_graph_blocks_ambiguous_even_when_resolver_returns_hint() -> None:
    calls: list[dict[str, object]] = []

    def fake_resolver(rca: dict[str, object]) -> str:
        calls.append(rca)
        return "operator hint: inspect upstream grandmaster before choosing a route"

    runner = taxonomy_graph.TaxonomyGraphRunner(
        prefer_langgraph=False,
        ambiguity_resolver=fake_resolver,
    )

    result = runner.invoke(_rca("ptp_boundary", "ambiguous"))

    assert len(calls) == 1
    assert result.audit_event is None
    assert result.state["status"] == "blocked_ambiguous"
    assert result.state["ambiguity_hint"] == (
        "operator hint: inspect upstream grandmaster before choosing a route"
    )
    assert taxonomy_graph.NODE_ROUTE not in result.node_trace


def test_run_fault_payload_convenience_returns_audit_event() -> None:
    audit_event = taxonomy_graph.run_fault_payload("scenarios/A_prime_ice_driver/fault_payload.json")

    assert audit_event["eventType"] == "RemediationProposed"
    assert audit_event["event"]["remediation"]["taxonomyMatch"] == "host_driver"
