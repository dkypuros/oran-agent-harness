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


_TESTS = [
    test_route_service_layer,
    test_route_ambiguous_raises,
    test_route_unknown_layer_raises,
    test_route_empty_classifications_raises,
    test_evaluate_crisis_mode_active,
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
