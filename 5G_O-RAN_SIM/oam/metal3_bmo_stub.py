"""Stub Metal3 Baremetal Operator (BMO) firmware push.

Conforms to:
  Metal3 project (the bare-metal provisioning framework)
  metal3-io/baremetal-operator (BareMetalHost, HostFirmwareSettings, HostFirmwareComponents CRDs)
Bibliography refs: 7, 8

Simulates the phase sequence the real Metal3 BMO produces when reconciling a
HostFirmwareComponents apply: Preparing -> Pushing -> Rebooting -> Verifying ->
Updated. Each phase appends one record to the shared trace layer so the demo
can replay the firmware-push timeline.

This module is a stub. In a real OpenShift deployment, the Metal3 BMO talks
to the host BMC via Redfish (see redfish_bmc_stub.py for the next layer
down). The vendor (Dell, Lenovo, Supermicro, HPE) and Red Hat O-Cloud Manager
handle the actual firmware push. This stub is shape only.

Exposes:
  apply_firmware(scenario_id, component, firmware_image_uri) -> list[dict]
    Runs the phase sequence and returns the per-phase records. Each phase is
    also written to the shared trace layer.
"""

from __future__ import annotations

import sys
import time
from typing import Any


def apply_firmware(
    scenario_id: str,
    component: str = "intel-e810-nic",
    firmware_image_uri: str = "registry.redhat.io/firmware/intel-e810:1.13.7",
    sleep_between_phases: float = 0.0,
) -> list[dict[str, Any]]:
    """Run the canned Metal3 BMO firmware-push phase sequence.

    Args:
      scenario_id: trace partition key, e.g. "E_nic_firmware_update"
      component: which hardware component is being updated
      firmware_image_uri: registry path to the firmware image
      sleep_between_phases: seconds between phases (0 for instant, >0 for demo realism)

    Returns:
      List of phase records, one per Preparing/Pushing/Rebooting/Verifying/Updated stage.
    """
    from shared_trace import append_trace

    phases = [
        {"phase": "Preparing", "detail": "validating HostFirmwareComponents spec, draining workload"},
        {"phase": "Pushing", "detail": "transferring firmware image to BMC", "bytes": 41943040},
        {"phase": "Rebooting", "detail": "BMC initiated host reboot for firmware activation"},
        {"phase": "Verifying", "detail": "post-boot firmware version readback and self-test"},
        {"phase": "Updated", "detail": "firmware active, NIC re-bound, ready for service"},
    ]

    records: list[dict[str, Any]] = []
    for phase_info in phases:
        record = {
            "component": component,
            "firmware_image_uri": firmware_image_uri,
            "scenario_id": scenario_id,
            **phase_info,
        }
        append_trace(scenario_id, "metal3_bmo", record)
        records.append(record)
        if sleep_between_phases > 0:
            time.sleep(sleep_between_phases)
    return records


def main(argv: list[str] | None = None) -> int:
    import json

    argv = argv or sys.argv[1:]
    scenario_id = argv[0] if argv else "E_nic_firmware_update"
    component = argv[1] if len(argv) > 1 else "intel-e810-nic"
    records = apply_firmware(scenario_id=scenario_id, component=component)
    for record in records:
        print(json.dumps(record, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
