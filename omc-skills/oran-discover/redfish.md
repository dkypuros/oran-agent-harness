---
name: oran-discover:redfish
description: Survey BMC out-of-band state via DMTF Redfish DSP0266. Report current SimpleUpdate task lifecycle (Pending, Running, Completed, Failed).
argument-hint: "(no arguments)"
level: 1
citation_anchor:
  inputs:
    - ../../5G_O-RAN_SIM/oam/redfish_bmc_stub.py
    - ../../scenarios/E_nic_firmware_update/
  outputs:
    - ../../5G_O-RAN_SIM/shared_trace/E_nic_firmware_update.jsonl
  bibliography_refs: [46]
---

# /oran-discover:redfish

<Purpose>
Survey the BMC layer underneath Metal3. Tell the operator what the BMC out-of-band channel is
doing: which Redfish UpdateService.SimpleUpdate task is in flight, its task state, and percent
complete. This is the lowest layer in the right-loop stack.
</Purpose>

<Use_When>
- Operator wants to see the BMC perspective on a firmware push
- Reviewer is walking scenario E and wants to see where Metal3 actually delegates the write
- Pre-flight read to confirm BMC connectivity exists before invoking
  `/oran-discover:metal3`
</Use_When>

<Steps>

1. **Decide live mode vs static mode.** Try `curl -sf --max-time 1 http://localhost:8093/health`.

2. **Live mode.**
   - `curl -s http://localhost:8093/state` for current task state per scenario
   - `curl -s http://localhost:8093/history?limit=20` for task lifecycle history

3. **Static mode.**
   - Read `5G_O-RAN_SIM/oam/redfish_bmc_stub.py` for the canonical task lifecycle:
     `Pending -> Running (percent_complete climbs) -> Completed`
   - Note the stub follows DSP0266 task semantics: a task URI, a task state, a percent_complete,
     a message string

4. **Format the survey output.** Always include:
   - **Redfish context**: DMTF Redfish DSP0266 ([ref 46](../../docs/references.md#ref-46)) defines
     the BMC-side API; UpdateService.SimpleUpdate is the firmware push entry point
   - **Task lifecycle** (live mode) or **task pattern** (static mode):
     one line per state with `task_uri | task_state | percent_complete | message`
   - **Where this sits in the stack**: Metal3 BMO delegates the actual write to the BMC, which
     uses Redfish to surface progress. The BMC is the lowest layer the harness can observe.
   - **Citation footer**: DMTF Redfish DSP0266 ([ref 46](../../docs/references.md#ref-46))

5. **Do not start a SimpleUpdate.** Discovery-only.

</Steps>

<Determinism_Contract>
Read-only. No POST calls.
</Determinism_Contract>

<Verification>
- HTTP wrapper response shape: `macbook_lab/http_wrappers/redfish_bmc_service.py`.
- Stub source: `5G_O-RAN_SIM/oam/redfish_bmc_stub.py`.
- Citation ref 46 is validated by `harness/conformance.md` membership.
</Verification>
