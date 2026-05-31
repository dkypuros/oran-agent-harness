---
name: oran-discover:metal3
description: Survey Metal3 BareMetalHost / HostFirmwareComponents state. Report current firmware push phase and any node-firmware actions in flight.
argument-hint: "(no arguments)"
level: 1
citation_anchor:
  inputs:
    - ../../5G_O-RAN_SIM/oam/metal3_bmo_stub.py
    - ../../scenarios/E_nic_firmware_update/
  outputs:
    - ../../5G_O-RAN_SIM/shared_trace/E_nic_firmware_update.jsonl
  bibliography_refs: [7, 8]
---

# /oran-discover:metal3

<Purpose>
Survey the right-loop infrastructure side. Tell the operator what Metal3 BMO is doing: which
BareMetalHost / HostFirmwareComponents are being touched, which phase the firmware push is in
(Preparing, Pushing, Rebooting, Verifying, Updated), and which scenario triggered it.
</Purpose>

<Use_When>
- The operator wants to know if a firmware push is in flight before authorizing another one
- A reviewer is walking scenario E (NIC firmware update via Metal3 + TMF921 companion intent)
- Pre-flight read before invoking `/o-ran:remediate` on a node_firmware-class fault
</Use_When>

<Steps>

1. **Decide live mode vs static mode.** Try `curl -sf --max-time 1 http://localhost:8092/health`.
   If 200: live mode. Otherwise: static mode.

2. **Live mode.**
   - `curl -s http://localhost:8092/state` for current state per scenario
   - `curl -s http://localhost:8092/history?limit=20` for phase progression history

3. **Static mode.**
   - Read `5G_O-RAN_SIM/oam/metal3_bmo_stub.py` to see the phase sequence the stub WOULD emit:
     `Preparing -> Pushing -> Rebooting -> Verifying -> Updated`
   - Read `scenarios/E_nic_firmware_update/remediation.yaml` for the canonical
     HostFirmwareComponents apply target

4. **Format the survey output.** Always include:
   - **Metal3 context**: BareMetalHost / HostFirmwareSettings / HostFirmwareComponents are the
     three CRDs ([ref 8](../../docs/references.md#ref-8)); the BareMetalOperator is the
     reconciler ([ref 7](../../docs/references.md#ref-7))
   - **Phases in flight** (live mode) or **phase pattern** (static mode):
     one line per phase with `component | phase | detail | bytes (if applicable)`
   - **Scenario hint**: scenario E exercises this path with a 41.9 MB firmware blob
     (Intel E810 PF0); scenario E_with_smo_reject exercises the same Metal3 push but with the
     companion intent rejected by the partner SMO (so `dispatch_result.accepted: false`
     lands on the AuditEvent even though the BareMetalHost apply itself proceeds)
   - **Routing context**: actions targeting `node_firmware` fire the DOWN-route via O2 IMS
     ([refs 2, 3](../../docs/references.md#ref-2)) and ALSO emit a TMF921 companion intent UP
     because firmware reboots require SMO coordination regardless of cell count
   - **Citation footer**: Metal3 BareMetalOperator ([ref 7](../../docs/references.md#ref-7)),
     Metal3 CRDs ([ref 8](../../docs/references.md#ref-8))

5. **Do not apply firmware.** This skill is discovery-only. If a firmware push is needed, the
   operator can `curl -X POST http://localhost:8092/apply` or use the harness routing rule via
   `/o-ran:remediate`.

</Steps>

<Determinism_Contract>
Read-only. No POST calls. No state mutation. Output is a function of platform state (live) or
stub source (static).
</Determinism_Contract>

<Verification>
- HTTP wrapper response shape: `macbook_lab/http_wrappers/metal3_bmo_service.py`.
- Stub source: `5G_O-RAN_SIM/oam/metal3_bmo_stub.py`.
- Citation refs 7, 8 are validated by `harness/conformance.md` membership.
</Verification>
