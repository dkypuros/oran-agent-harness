"""5G_O-RAN_SIM research bench runner.

Conforms to:
  harness-unique orchestration, no upstream spec
Bibliography refs: n/a (composition layer over the platform stubs and the harness walker)

Orchestrates all 4 walkthrough scenarios end to end:
  A_fw_lldp_agent, A_prime_ice_driver, D_phc_drift_hw_only, E_nic_firmware_update

For each scenario:
  1. Emit PTP operator alarm sequence via ptp_operator_stub.emit_alarm_sequence()
  2. Append each alarm event to the shared trace
  3. Invoke harness.runtime.walker.walk(<fault_payload_path>) and capture the AuditEvent
  4. Append a router stage record (taxonomy, action, companion_intent presence)
  5. For E: also fire metal3_bmo_stub.apply_firmware() and tmf921_intent_emitter.emit_intent()
  6. Append an audit stage record

Outputs:
  - shared_trace/{scenario_id}.jsonl (runtime, gitignored)
  - bench/last_run_summary.md (gitignored)

Exposes:
  run_scenario(scenario_id) -> dict
  run_all() -> list of dict + summary dict

CLI:
  python 5G_O-RAN_SIM/bench/runner.py [scenario_id|all]

The directory name "5G_O-RAN_SIM" is not a valid Python module identifier (starts with a
digit, contains a hyphen), so the bench is invoked via direct script path; the script
self-adjusts sys.path to make the inner packages importable.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import Any

_SIM_ROOT = Path(__file__).resolve().parent.parent
_REPO_ROOT = _SIM_ROOT.parent
_SCENARIOS_DIR = _REPO_ROOT / "scenarios"


SCENARIO_IDS = [
    "A_fw_lldp_agent",
    "A_prime_ice_driver",
    "D_phc_drift_hw_only",
    "E_nic_firmware_update",
]

_FAULT_ID_BY_SCENARIO = {
    "A_fw_lldp_agent": "flt-2026-05-14-001",
    "A_prime_ice_driver": "flt-2026-05-14-002",
    "D_phc_drift_hw_only": "flt-D-001",
    "E_nic_firmware_update": "flt-E-001",
}

_NODE_BY_SCENARIO = {
    "A_fw_lldp_agent": "worker-ran-01.dallas.example.com",
    "A_prime_ice_driver": "worker-ran-02.dallas.example.com",
    "D_phc_drift_hw_only": "worker-ran-02.dallas.example.com",
    "E_nic_firmware_update": "worker-ran-02.dallas.example.com",
}


def _ensure_path() -> None:
    """Make 5G_O-RAN_SIM importable when run as a module from the repo root."""
    sim_str = str(_SIM_ROOT)
    if sim_str not in sys.path:
        sys.path.insert(0, sim_str)
    repo_str = str(_REPO_ROOT)
    if repo_str not in sys.path:
        sys.path.insert(0, repo_str)


def run_scenario(scenario_id: str) -> dict[str, Any]:
    """Run one scenario end to end and capture the audit event.

    Args:
      scenario_id: one of SCENARIO_IDS

    Returns:
      {
        "scenario_id": str,
        "fault_id": str,
        "node": str,
        "audit_event": dict (the AuditEvent the walker emitted),
        "trace_path": str (path to the per-scenario JSONL trace file),
        "companion_intent_attached": bool,
        "duration_seconds": float,
      }
    """
    if scenario_id not in SCENARIO_IDS:
        raise ValueError(
            f"unknown scenario {scenario_id}; expected one of {SCENARIO_IDS}"
        )

    _ensure_path()
    from oam.ptp_operator_stub import emit_alarm_sequence
    from shared_trace import append_trace
    from harness.runtime import walker

    start = time.time()
    fault_payload_path = _SCENARIOS_DIR / scenario_id / "fault_payload.json"
    node = _NODE_BY_SCENARIO[scenario_id]
    fault_id = _FAULT_ID_BY_SCENARIO[scenario_id]

    alarm_events = emit_alarm_sequence(node=node, scenario_id=scenario_id)
    for event in alarm_events:
        append_trace(
            scenario_id,
            "ptp_operator",
            {
                "topic": event.get("source"),
                "verdict": event.get("data", {}).get("verdict"),
                "event_type": event.get("type"),
            },
        )

    append_trace(
        scenario_id,
        "gateway",
        {"fault_id": fault_id, "ingested": True, "source": "ptp-operator-stub"},
    )

    audit_event = walker.walk(str(fault_payload_path), verbose=False)
    remediation = audit_event.get("event", {}).get("remediation", {})
    companion = remediation.get("companion_intent")

    append_trace(
        scenario_id,
        "router",
        {
            "target_layer": remediation.get("targetLayer"),
            "taxonomy_match": remediation.get("taxonomyMatch"),
            "action_type": remediation.get("actionType"),
            "ocloud_internal_path": remediation.get("ocloudInternalPath"),
            "companion_intent_attached": companion is not None,
        },
    )

    if scenario_id == "E_nic_firmware_update":
        from oam.metal3_bmo_stub import apply_firmware
        from oam.redfish_bmc_stub import simple_update, get_task_status
        from smo.tmf921_intent_emitter import emit_intent

        emit_intent(
            scenario_id=scenario_id,
            intent_type="MaintenanceWindowNotification",
            affected_resources=[node],
            window_start="2026-05-30T11:30:00Z",
            window_end="2026-05-30T11:38:00Z",
            service_impact_hint="reduced_capacity",
            expected_handover_count=47,
        )
        apply_firmware(scenario_id=scenario_id, component="intel-e810-nic")
        task_uri = simple_update(scenario_id=scenario_id)
        get_task_status(scenario_id=scenario_id, task_uri=task_uri)

    append_trace(
        scenario_id,
        "guardrail",
        {
            "outcome": remediation.get("guardrailResult", {}).get("outcome"),
            "blast_radius": remediation.get("guardrailResult", {}).get("blastRadius"),
        },
    )

    append_trace(
        scenario_id,
        "audit",
        {
            "event_id": audit_event.get("eventId"),
            "event_type": audit_event.get("eventType"),
            "tmf688_emitted": True,
            "reversibility_confidence": remediation.get("reversibility_profile", {}).get(
                "confidence_in_reversibility"
            ),
        },
    )

    duration = time.time() - start
    trace_path = _SIM_ROOT / "shared_trace" / f"{scenario_id}.jsonl"

    return {
        "scenario_id": scenario_id,
        "fault_id": fault_id,
        "node": node,
        "audit_event": audit_event,
        "trace_path": str(trace_path),
        "companion_intent_attached": companion is not None,
        "duration_seconds": round(duration, 3),
    }


def run_all() -> dict[str, Any]:
    """Run every scenario in order and produce a summary dict."""
    results = [run_scenario(sid) for sid in SCENARIO_IDS]
    summary = {
        "scenario_count": len(results),
        "scenarios_with_companion_intent": sum(
            1 for r in results if r["companion_intent_attached"]
        ),
        "total_duration_seconds": round(sum(r["duration_seconds"] for r in results), 3),
        "per_scenario": [
            {
                "scenario_id": r["scenario_id"],
                "fault_id": r["fault_id"],
                "action_type": r["audit_event"]
                .get("event", {})
                .get("remediation", {})
                .get("actionType"),
                "target_layer": r["audit_event"]
                .get("event", {})
                .get("remediation", {})
                .get("targetLayer"),
                "blast_cells": r["audit_event"]
                .get("event", {})
                .get("remediation", {})
                .get("guardrailResult", {})
                .get("blastRadius", {})
                .get("cells"),
                "companion_intent_attached": r["companion_intent_attached"],
                "trace_path": r["trace_path"],
                "duration_seconds": r["duration_seconds"],
            }
            for r in results
        ],
    }
    return {"results": results, "summary": summary}


def main(argv: list[str] | None = None) -> int:
    argv = argv or sys.argv[1:]
    target = argv[0] if argv else "all"
    if target == "all":
        report = run_all()
        from bench.summary import summarize, write_summary

        markdown = summarize(report)
        write_summary(markdown)
        print(markdown)
        return 0
    result = run_scenario(target)
    print(json.dumps(
        {k: v for k, v in result.items() if k != "audit_event"},
        indent=2,
    ))
    return 0


if __name__ == "__main__":
    _ensure_path()
    sys.exit(main())
