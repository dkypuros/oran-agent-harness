"""Stub O-RAN O2 IMS (Infrastructure Management Services) endpoint.

Conforms to:
  O-RAN.WG6 O2 General Aspects and Principles (ref 2): the SMO-to-O-Cloud API contract surface
  O-RAN.WG6 O2 IMS Interface Specification (ref 3): the DeploymentRequest envelope shape
Bibliography refs: 2, 3, 6

Represents the O-Cloud Manager (Red Hat oran-o2ims is the reference implementation, ref 6) sitting
between the harness and the underlying delivery layer (Metal3 BMO, Machine Config Operator, KMM).
The harness DOWN-route lands here first; the O-Cloud Manager then reconciles the DeploymentRequest
into the concrete CRD path. Before this stub existed, the harness composed `ocloudInternalPath` as
a synthesized string label without an actual hop. Now the router CALLS this module, and the
returned envelope is what the AuditEvent's `o2ims_dispatch` field reports back to the operator.

The stub is shape-only: no network call, no real reconcile loop. The deterministic response shape
matches what an O2 IMS-conformant O-Cloud Manager would return. Per-scenario overrides come from
harness/runtime/scenario_stubs.json `o2ims_dispatch_outcome`, which allows tests to inject reject
or partial-acceptance paths without modifying the stub.

Exposes:
  deploy_request(scenario_id, action_type, action_target, ocloud_internal_path,
                 deterministic_outcome=None) -> dict
    Returns the O-Cloud Manager's response envelope. If `deterministic_outcome` is provided
    (the scenario_stubs.json override block), its fields take precedence over the synthesized
    defaults. The returned dict is the canonical o2ims_dispatch payload the router attaches
    to the proposal.
"""

from __future__ import annotations

from typing import Any

_OCM_INSTANCE_ID = "ocm-dallas-cluster-01"
_OCM_VERSION = "openshift-kni/oran-o2ims v0-stub"

_INTERNAL_PATH_TO_RECONCILER = {
    "metal3-baremetal-operator": "Metal3 BareMetalOperator (HostFirmwareComponents reconciler)",
    "machine-config-operator": "Machine Config Operator (MachineConfigPool reconciler)",
    "kernel-module-management": "Kernel Module Management Operator (Module v1beta1 reconciler)",
    "smo-tmf921-endpoint": "TMF921 dispatch (up-route, not delivered via O2 IMS)",
}


def deploy_request(
    scenario_id: str,
    action_type: str,
    action_target: str,
    ocloud_internal_path: str,
    deterministic_outcome: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Issue a DeploymentRequest to the stubbed O-Cloud Manager.

    Args:
      scenario_id: trace partition key, e.g. "E_nic_firmware_update" or a fault_id
      action_type: harness action_type (apply_metal3_firmware, apply_machine_config, etc.)
      action_target: the targeted node / resource (e.g. worker-ran-02.dallas.example.com)
      ocloud_internal_path: which delivery reconciler the O-Cloud Manager should dispatch to
      deterministic_outcome: optional override from scenario_stubs.json; when present, its
        fields take precedence over the synthesized defaults so tests can inject reject paths

    Returns:
      An o2ims_dispatch envelope dict. Always carries:
        _conforms_to       (spec metadata for citation)
        accepted           (bool)
        deploymentManagerId
        deploymentRequestId
        request_received_at
        ocloud_internal_path
        reconciler_target  (human-readable name of the downstream reconciler)
        ocm_response       (operator-facing summary)
      When `deterministic_outcome` is provided, additional fields from the override block
      (rejection_reason, etc.) flow through unchanged.
    """
    reconciler = _INTERNAL_PATH_TO_RECONCILER.get(
        ocloud_internal_path,
        f"unknown reconciler for path {ocloud_internal_path!r}",
    )
    base: dict[str, Any] = {
        "_conforms_to": {
            "spec": (
                "O-RAN.WG6 O2 IMS Interface Specification, DeploymentRequest envelope"
            ),
            "spec_section": (
                "Infrastructure Management Services request and response envelope"
            ),
            "spec_version": "O-RAN.WG6.O2IMS-Interface current",
            "bibliography_ref": [2, 3, 6],
        },
        "accepted": True,
        "deploymentManagerId": _OCM_INSTANCE_ID,
        "deploymentRequestId": f"o2ims-req-{scenario_id}-001",
        "ocloud_internal_path": ocloud_internal_path,
        "reconciler_target": reconciler,
        "ocm_version": _OCM_VERSION,
        "ocm_response": (
            f"DeploymentRequest accepted by O-Cloud Manager {_OCM_INSTANCE_ID}; "
            f"will dispatch {action_type} for {action_target} into "
            f"{reconciler}."
        ),
    }
    if deterministic_outcome is not None:
        base.update(deterministic_outcome)
    return base
