"""Stub TMF921 Intent Management API intent emitter.

Conforms to:
  TM Forum TMF921 Intent Management API (User Guide and REST Specification)
Bibliography ref: 19

Emits a TMF921-shaped intent envelope that the partner SMO would consume.
Used by the harness Router when blast radius forces SMO awareness, e.g.
a NIC firmware update that takes the node offline for several minutes.
The intent is fire-and-forget at the harness boundary: the harness emits
the envelope, trusts the partner SMO to act on it, and observes the
outcome via downstream telemetry.

Exposes:
  emit_intent(scenario_id, intent_type, affected_resources, window_start,
              window_end, service_impact_hint, expected_handover_count) -> dict
    Returns the TMF921 envelope as a dict with a _conforms_to header.
"""

from __future__ import annotations

import sys
import uuid
from datetime import datetime, timezone
from typing import Any


def emit_intent(
    scenario_id: str,
    intent_type: str = "MaintenanceWindowNotification",
    affected_resources: list[str] | None = None,
    window_start: str | None = None,
    window_end: str | None = None,
    service_impact_hint: str = "reduced_capacity",
    expected_handover_count: int = 0,
) -> dict[str, Any]:
    """Build a TMF921 intent envelope and append it to the shared trace."""
    from shared_trace import append_trace

    if affected_resources is None:
        affected_resources = []
    if window_start is None:
        window_start = datetime.now(timezone.utc).isoformat()
    if window_end is None:
        window_end = window_start

    intent_id = f"INT-{scenario_id}-{uuid.uuid4().hex[:6]}"
    envelope = {
        "_conforms_to": {
            "spec": "TMF921 Intent Management API envelope",
            "spec_section": "Intent expression and negotiation between Intent Owner and Intent Handler",
            "spec_version": "TMF921 current",
            "bibliography_ref": [19],
        },
        "intent_id": intent_id,
        "intent_type": intent_type,
        "affected_resources": affected_resources,
        "window_start": window_start,
        "window_end": window_end,
        "service_impact_hint": service_impact_hint,
        "expected_handover_count": expected_handover_count,
        "issuer": "oran-agent-harness/companion_intent",
    }
    append_trace(
        scenario_id,
        "smo_intent",
        {
            "intent_id": intent_id,
            "intent_type": intent_type,
            "affected_resources": affected_resources,
            "window_start": window_start,
            "window_end": window_end,
            "service_impact_hint": service_impact_hint,
            "expected_handover_count": expected_handover_count,
            "tmf921_envelope": True,
        },
    )
    return envelope


def main(argv: list[str] | None = None) -> int:
    import json

    argv = argv or sys.argv[1:]
    scenario_id = argv[0] if argv else "E_nic_firmware_update"
    envelope = emit_intent(
        scenario_id=scenario_id,
        intent_type="MaintenanceWindowNotification",
        affected_resources=["site/dallas-edge-01", "node/worker-ran-02.dallas.example.com"],
        window_start="2026-05-30T11:30:00Z",
        window_end="2026-05-30T11:38:00Z",
        service_impact_hint="reduced_capacity",
        expected_handover_count=47,
    )
    print(json.dumps(envelope, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
