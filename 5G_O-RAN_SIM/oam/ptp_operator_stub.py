"""Stub Red Hat PTP Operator + cloud-event-proxy publisher.

Conforms to:
  O-RAN.WG6 O-Cloud Notification API v04.00 (the inner schema for the alarm)
  CNCF CloudEvents 1.0 (the outer envelope)
  IEEE 1588-2019 PTP (state machine: SYNCHRONIZED, HOLDOVER, FREE_RUNNING, UNCALIBRATED)
  ITU-T G.8275.1 (telecom profile, full timing support)
  Red Hat PTP Operator for OpenShift (runs linuxptp + cloud-event-proxy as DaemonSet)
  redhat-cne/cloud-event-proxy (reference implementation)
Bibliography refs: 26, 28, 29, 30, 31, 44

The "software-LOCKED vs hardware-NOT-OK" diagnostic teaching moment:
ptp4l reports SYNCHRONIZED with master_offset_ns within nominal range
(software thinks PTP is fine), while simultaneously phc2sys reports monotonic
PPB drift AND the NIC reports rising tx_hwtstamp_timeouts. The divergence is
the alarm. The remediation is a kernel module swap via KMM.

This module is a stub. In a real OpenShift deployment, the PTP Operator runs
linuxptp on each node, the cloud-event-proxy sidecar observes linuxptp state
transitions, and publishes CloudEvents to a configured AMQP or HTTP endpoint.
This stub emits the same shape, in-process, for demo flows.

Exposes:
  emit_alarm_sequence(node, scenario_id) -> list of CloudEvent-shaped dicts
    Each dict is a CNCF CloudEvent 1.0 envelope carrying an O-RAN WG6 O-Cloud
    Notification API payload. The sequence shows the software-vs-hardware
    divergence pattern.

  CLI: python -m 5G_O-RAN_SIM.oam.ptp_operator_stub <node> <scenario_id>
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from typing import Any

_TOPIC_PREFIX = "/cluster/node"


def _ce_envelope(
    source: str, event_type: str, data_schema: str, data: dict[str, Any]
) -> dict[str, Any]:
    """Build a CNCF CloudEvents 1.0 envelope around an O-RAN WG6 payload."""
    return {
        "specversion": "1.0",
        "type": event_type,
        "source": source,
        "id": f"evt-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%f')}",
        "time": datetime.now(timezone.utc).isoformat(),
        "datacontenttype": "application/json",
        "dataschema": data_schema,
        "data": data,
    }


def emit_alarm_sequence(
    node: str = "worker-ran-02.dallas.example.com",
    scenario_id: str = "D_phc_drift_hw_only",
) -> list[dict[str, Any]]:
    """Emit the canonical software-OK / hardware-NOT-OK alarm sequence.

    Returns a list of CloudEvent envelopes (NOT yet published). Caller can
    forward to a real sink or feed into the shared trace layer.

    Sequence:
      1. ptp4l reports SYNCHRONIZED with normal master_offset_ns. Software
         says PTP is fine.
      2. phc2sys reports monotonic PPB drift. Hardware clock is wandering
         despite software lock.
      3. os-clock reports rising tx_hwtstamp_timeouts. NIC hardware
         timestamping is failing.
      4. ptp4l holds the SYNCHRONIZED state for a second beat to highlight
         that the daemon does not yet detect the underlying hardware issue.

    The diagnostic gold is the divergence: software is locked, hardware is
    not. Resolution is a kernel module swap via KMM, not a service mask or
    a ptp4l reconfig.
    """
    base_src = f"{_TOPIC_PREFIX}/{node}"
    sequence: list[dict[str, Any]] = []

    sequence.append(
        _ce_envelope(
            source=f"{base_src}/sync/ptp4l/state",
            event_type="event.sync.ptp-state-change.locked",
            data_schema="https://www.o-ran.org/specifications#O-Cloud-Notification-API-v04.00",
            data={
                "version": "v1",
                "values": [
                    {
                        "resource": f"{base_src}/sync/ptp4l/state",
                        "data_type": "notification",
                        "value_type": "enumeration",
                        "value": "SYNCHRONIZED",
                    },
                    {
                        "resource": f"{base_src}/sync/ptp4l/master-offset-ns",
                        "data_type": "metric",
                        "value_type": "decimal64.3",
                        "value": "12.000",
                    },
                ],
                "scenario_id": scenario_id,
                "verdict": "software_ok",
            },
        )
    )

    sequence.append(
        _ce_envelope(
            source=f"{base_src}/sync/phc2sys/drift",
            event_type="event.sync.phc-drift.anomaly",
            data_schema="https://www.o-ran.org/specifications#O-Cloud-Notification-API-v04.00",
            data={
                "version": "v1",
                "values": [
                    {
                        "resource": f"{base_src}/sync/phc2sys/drift",
                        "data_type": "metric",
                        "value_type": "decimal64.3",
                        "value": "47.300",
                        "unit": "ppb",
                    },
                    {
                        "resource": f"{base_src}/sync/phc2sys/state",
                        "data_type": "notification",
                        "value_type": "enumeration",
                        "value": "DRIFTING",
                    },
                ],
                "scenario_id": scenario_id,
                "verdict": "hardware_anomaly",
            },
        )
    )

    sequence.append(
        _ce_envelope(
            source=f"{base_src}/sync/os-clock/tx-hwtstamp-timeouts",
            event_type="event.sync.nic-hwtstamp.spike",
            data_schema="https://www.o-ran.org/specifications#O-Cloud-Notification-API-v04.00",
            data={
                "version": "v1",
                "values": [
                    {
                        "resource": f"{base_src}/sync/os-clock/tx-hwtstamp-timeouts",
                        "data_type": "metric",
                        "value_type": "uint64",
                        "value": "1241",
                    },
                    {
                        "resource": f"{base_src}/sync/os-clock/driver",
                        "data_type": "notification",
                        "value_type": "string",
                        "value": "ice 1.11.17",
                    },
                ],
                "scenario_id": scenario_id,
                "verdict": "hardware_anomaly",
            },
        )
    )

    sequence.append(
        _ce_envelope(
            source=f"{base_src}/sync/ptp4l/state",
            event_type="event.sync.ptp-state-change.locked",
            data_schema="https://www.o-ran.org/specifications#O-Cloud-Notification-API-v04.00",
            data={
                "version": "v1",
                "values": [
                    {
                        "resource": f"{base_src}/sync/ptp4l/state",
                        "data_type": "notification",
                        "value_type": "enumeration",
                        "value": "SYNCHRONIZED",
                    },
                    {
                        "resource": f"{base_src}/sync/ptp4l/master-offset-ns",
                        "data_type": "metric",
                        "value_type": "decimal64.3",
                        "value": "14.000",
                    },
                ],
                "scenario_id": scenario_id,
                "verdict": "software_ok_persistent",
                "diagnostic": (
                    "ptp4l holds SYNCHRONIZED despite phc2sys drift and rising "
                    "tx_hwtstamp_timeouts. The daemon's view does not surface the "
                    "underlying hardware-timestamping failure. Resolution path is "
                    "kernel module swap via KMM, not a ptp4l configuration change."
                ),
            },
        )
    )

    return sequence


def main(argv: list[str] | None = None) -> int:
    argv = argv or sys.argv[1:]
    node = argv[0] if argv else "worker-ran-02.dallas.example.com"
    scenario_id = argv[1] if len(argv) > 1 else "D_phc_drift_hw_only"
    for event in emit_alarm_sequence(node=node, scenario_id=scenario_id):
        print(json.dumps(event, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
