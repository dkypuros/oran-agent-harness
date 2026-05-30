"""Stub Redfish BMC out-of-band management for firmware update.

Conforms to:
  DMTF Redfish DSP0266 (out-of-band management protocol for servers and infrastructure)
Bibliography ref: 46

Simulates the Redfish SimpleUpdate task lifecycle that the Metal3 Baremetal
Operator drives during a firmware push. Real deployments talk to the vendor
BMC (Dell iDRAC, Lenovo XCC, HPE iLO, Supermicro BMC) over HTTPS to invoke
this action. This stub is shape only; the vendor + Red Hat O-Cloud Manager
handle the real protocol exchange.

Exposes:
  simple_update(scenario_id, image_uri) -> task_uri
    Initiates the firmware update task. Returns a synthetic task URI.
  get_task_status(scenario_id, task_uri) -> list[dict]
    Polls the task to completion and returns the lifecycle records.
"""

from __future__ import annotations

import sys
import uuid
from typing import Any


def simple_update(
    scenario_id: str,
    image_uri: str = "registry.redhat.io/firmware/intel-e810:1.13.7",
) -> str:
    """Invoke POST /redfish/v1/UpdateService/Actions/UpdateService.SimpleUpdate.

    Returns the task URI the caller polls via get_task_status().
    """
    from shared_trace import append_trace

    task_id = uuid.uuid4().hex[:12]
    task_uri = f"/redfish/v1/TaskService/Tasks/{task_id}"
    append_trace(
        scenario_id,
        "redfish_bmc",
        {
            "action": "SimpleUpdate.invoke",
            "image_uri": image_uri,
            "task_uri": task_uri,
            "task_state": "Running",
        },
    )
    return task_uri


def get_task_status(scenario_id: str, task_uri: str) -> list[dict[str, Any]]:
    """Poll the synthetic task through Running -> Completed.

    Returns the lifecycle records. Each record is also appended to the trace.
    """
    from shared_trace import append_trace

    lifecycle = [
        {"task_state": "Running", "percent_complete": 25, "message": "image transferred"},
        {"task_state": "Running", "percent_complete": 60, "message": "applying firmware"},
        {"task_state": "Running", "percent_complete": 85, "message": "BMC reset and verify"},
        {"task_state": "Completed", "percent_complete": 100, "message": "firmware updated, host ready"},
    ]
    records: list[dict[str, Any]] = []
    for tick in lifecycle:
        record = {"task_uri": task_uri, **tick}
        append_trace(scenario_id, "redfish_bmc", record)
        records.append(record)
    return records


def main(argv: list[str] | None = None) -> int:
    import json

    argv = argv or sys.argv[1:]
    scenario_id = argv[0] if argv else "E_nic_firmware_update"
    task_uri = simple_update(scenario_id=scenario_id)
    records = get_task_status(scenario_id=scenario_id, task_uri=task_uri)
    print(json.dumps({"task_uri": task_uri, "lifecycle": records}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
