"""Unit tests for harness.runtime branches not covered by the two walkthrough scenarios.

Run with pytest:
    pytest tests/test_runtime.py -v

Or directly (no framework required):
    python3 -m tests.test_runtime

Covers the five branches identified by the code-reviewer pass on commit 5a7f68b:

1. router.route() service layer branch -> emit_smo_intent
2. router.route() ambiguous layer branch -> NotImplementedError
3. router.route() unknown target_layer -> ValueError
4. router.route() empty candidate_classifications -> ValueError
5. guardrail.evaluate() crisis_mode active branch -> RuntimeError
"""

from __future__ import annotations

from harness.runtime import guardrail, router


def _service_rca() -> dict:
    """Synthetic RCA with a service-layer classification. Uses a fault_id present in
    scenario_stubs.json so the scenario_stub fields (proposalId, contributingSignals, actionTarget,
    actionPayloadRef) are populated. The target_layer override forces the service branch."""
    return {
        "fault_id": "flt-2026-05-14-001",
        "timestamp": "2026-05-14T10:42:15Z",
        "evidence": [],
        "candidate_classifications": [
            {
                "taxonomy_match": "ran_kpi_degradation",
                "target_layer": "service",
                "confidence": "high",
                "rationale": "synthetic service-layer test fixture",
            }
        ],
    }


def _ambiguous_rca() -> dict:
    return {
        "fault_id": "flt-test-ambiguous",
        "timestamp": "2026-05-14T00:00:00Z",
        "evidence": [],
        "candidate_classifications": [
            {
                "taxonomy_match": "host_or_ran_uncertain",
                "target_layer": "ambiguous",
                "confidence": "medium",
                "rationale": "synthetic ambiguous-layer test fixture",
            }
        ],
    }


def _unknown_layer_rca() -> dict:
    return {
        "fault_id": "flt-test-unknown",
        "timestamp": "2026-05-14T00:00:00Z",
        "evidence": [],
        "candidate_classifications": [
            {
                "taxonomy_match": "anything",
                "target_layer": "nonsense_layer",
                "confidence": "low",
                "rationale": "synthetic unknown-layer test fixture",
            }
        ],
    }


def _empty_classifications_rca() -> dict:
    return {
        "fault_id": "flt-test-empty",
        "timestamp": "2026-05-14T00:00:00Z",
        "evidence": [],
        "candidate_classifications": [],
    }


def test_route_service_layer() -> None:
    rca = _service_rca()
    proposal = router.route(rca)
    assert proposal["targetLayer"] == "service", proposal["targetLayer"]
    assert proposal["actionType"] == "emit_smo_intent", proposal["actionType"]
    assert proposal["ocloudInternalPath"] == "smo-tmf921-endpoint", proposal["ocloudInternalPath"]
    assert proposal["taxonomyMatch"] == "ran_kpi_degradation"


def test_route_ambiguous_raises() -> None:
    rca = _ambiguous_rca()
    try:
        router.route(rca)
    except NotImplementedError as exc:
        assert "ambiguous_path" in str(exc), str(exc)
        return
    raise AssertionError("expected NotImplementedError, got none")


def test_route_unknown_layer_raises() -> None:
    rca = _unknown_layer_rca()
    try:
        router.route(rca)
    except ValueError as exc:
        assert "unknown target_layer" in str(exc), str(exc)
        return
    raise AssertionError("expected ValueError, got none")


def test_route_empty_classifications_raises() -> None:
    rca = _empty_classifications_rca()
    try:
        router.route(rca)
    except ValueError as exc:
        assert "no candidate_classifications" in str(exc), str(exc)
        return
    raise AssertionError("expected ValueError, got none")


def test_route_ambiguous_with_llm_mode_live() -> None:
    """ORAN_LLM_MODE=live: router exercises the 5G_O-RAN_SIM/llm seam and re-raises with hint.

    Skipped if ORAN_LLM_MODE is not set (default verify gate behavior must stay unchanged).
    When set, the test asserts the NotImplementedError message carries the LLM disambiguation
    hint, proving the live-mode seam is wired through to the inference client.
    """
    import os as _os

    if _os.environ.get("ORAN_LLM_MODE") != "live":
        print("SKIP: test_route_ambiguous_with_llm_mode_live (ORAN_LLM_MODE not set to live)")
        return
    rca = _ambiguous_rca()
    try:
        router.route(rca)
    except NotImplementedError as exc:
        msg = str(exc)
        assert "LLM-assist returned" in msg, msg
        assert "disambiguation hint" in msg, msg
        return
    raise AssertionError("expected NotImplementedError, got none")


def test_evaluate_crisis_mode_active() -> None:
    """Monkey-patch the crisis_mode seam to True and confirm evaluate raises RuntimeError."""
    original = guardrail._CRISIS_MODE_ACTIVE
    guardrail._CRISIS_MODE_ACTIVE = True
    try:
        proposal = {
            "actionType": "apply_machine_config",
            "requiresHumanApproval": True,
        }
        try:
            guardrail.evaluate(proposal, fault_id="flt-2026-05-14-001")
        except RuntimeError as exc:
            assert "crisis_mode active" in str(exc), str(exc)
            return
        raise AssertionError("expected RuntimeError, got none")
    finally:
        guardrail._CRISIS_MODE_ACTIVE = original


def test_evaluate_sandbox_block_when_apply_disallowed() -> None:
    """Sandbox verdict with apply_allowed=False blocks the apply at the twin gate.

    Proves the Sandbox stage in harness/runtime/walker.py is a real gate, not a stub.
    The guardrail evaluator raises ValueError before reaching the action_allowlist or
    blast_radius checks. This is the v0 implementation of trust_loop.md Activity 2
    (Sandbox forward-direction test flight on the twin).
    """
    proposal = {
        "actionType": "apply_machine_config",
        "requiresHumanApproval": True,
        "sandbox_verdict": {
            "simulator_version": "v0-deterministic-replay",
            "twin_converged": False,
            "baseline_match": "envelope_breach",
            "deviation_observed": "phc_drift_post_apply",
            "apply_allowed": False,
            "simulator_run_at": "2026-05-14T10:42:16Z",
            "rationale": "twin replay produced PHC drift regression; apply blocked at gate",
        },
    }
    try:
        guardrail.evaluate(proposal, fault_id="flt-2026-05-14-001")
    except ValueError as exc:
        assert "apply_allowed is False" in str(exc), str(exc)
        return
    raise AssertionError("expected ValueError, got none")


def test_dispatch_result_rejected_on_smo_reject_scenario() -> None:
    """Walk scenarios/E_with_smo_reject/ end-to-end and verify the companion intent
    carries dispatch_result.accepted=False.

    Proves the dual-route is parallel emission with observable rejection capture. The
    operator sees the SMO rejection in the AuditEvent before co-authorization. This is
    the v0 implementation of the dispatch_result extension (trust_loop.md and Q14 in
    talk/reviewer_faq.md).
    """
    from harness.runtime import walker
    audit = walker.walk("scenarios/E_with_smo_reject/fault_payload.json", verbose=False)
    companion = audit["event"]["remediation"]["companion_intent"]
    assert "dispatch_result" in companion, "companion_intent missing dispatch_result"
    assert companion["dispatch_result"]["accepted"] is False, companion["dispatch_result"]
    assert companion["dispatch_result"]["rejection_reason"] == "neighboring_cells_at_capacity"


def test_o2ims_dispatch_attached_on_down_route() -> None:
    """Down-route (layer=infra) crosses the O-RAN O2 IMS hop via 5G_O-RAN_SIM/oam/o2ims_stub.

    Proves the architecture diagram's O2 IMS edge is a real code path, not a synthesized
    string. router.route() must call into the o2ims_stub module and attach the response
    envelope as proposal["o2ims_dispatch"]. The envelope must carry the O2 IMS
    DeploymentRequest contract shape (deploymentManagerId, deploymentRequestId,
    ocloud_internal_path, reconciler_target) and cite the foundation refs (2, 3, 6).
    Service-layer routes do NOT cross O2 IMS, so service routes must NOT attach
    o2ims_dispatch. Bibliography refs: 2 (O2 GA&P), 3 (O2 IMS Interface), 6 (oran-o2ims).
    """
    infra_rca = {
        "fault_id": "flt-2026-05-14-001",
        "timestamp": "2026-05-14T10:42:15Z",
        "evidence": [],
        "candidate_classifications": [
            {
                "taxonomy_match": "ptp_host_stack",
                "target_layer": "infra",
                "confidence": "high",
                "rationale": "synthetic infra-layer test fixture (ptp_host_stack -> MCO)",
            }
        ],
    }
    proposal = router.route(infra_rca)
    assert "o2ims_dispatch" in proposal, "infra route missing o2ims_dispatch"
    dispatch = proposal["o2ims_dispatch"]
    assert dispatch["accepted"] is True, dispatch
    assert dispatch["deploymentManagerId"] == "ocm-dallas-cluster-01", dispatch
    assert dispatch["deploymentRequestId"].startswith("o2ims-req-flt-"), dispatch
    assert dispatch["ocloud_internal_path"] == "machine-config-operator", dispatch
    assert "Machine Config Operator" in dispatch["reconciler_target"], dispatch
    assert set(dispatch["_conforms_to"]["bibliography_ref"]) == {2, 3, 6}

    service_proposal = router.route(_service_rca())
    assert "o2ims_dispatch" not in service_proposal, (
        "service route must not cross O2 IMS; got o2ims_dispatch on TMF921 route"
    )


_TESTS = [
    test_route_service_layer,
    test_route_ambiguous_raises,
    test_route_unknown_layer_raises,
    test_route_empty_classifications_raises,
    test_route_ambiguous_with_llm_mode_live,
    test_evaluate_crisis_mode_active,
    test_evaluate_sandbox_block_when_apply_disallowed,
    test_dispatch_result_rejected_on_smo_reject_scenario,
    test_o2ims_dispatch_attached_on_down_route,
]


def main() -> int:
    failures = []
    for t in _TESTS:
        try:
            t()
            print(f"PASS: {t.__name__}")
        except AssertionError as exc:
            failures.append((t.__name__, str(exc)))
            print(f"FAIL: {t.__name__}: {exc}")
        except Exception as exc:
            failures.append((t.__name__, f"unexpected {type(exc).__name__}: {exc}"))
            print(f"FAIL: {t.__name__}: unexpected {type(exc).__name__}: {exc}")
    print()
    print(f"SUMMARY: {len(_TESTS) - len(failures)}/{len(_TESTS)} tests passed")
    return 0 if not failures else 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
