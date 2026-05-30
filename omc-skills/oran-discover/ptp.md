---
name: oran-discover:ptp
description: Survey current PTP sync state across linuxptp, the PHC, and cloud-event-proxy. Report alarm history and the verdicts each carries (software_ok, hardware_anomaly, firmware_anomaly).
argument-hint: "(no arguments)"
level: 1
citation_anchor:
  inputs:
    - ../../5G_O-RAN_SIM/oam/ptp_operator_stub.py
    - ../../scenarios/D_phc_drift_hw_only/
  outputs:
    - ../../5G_O-RAN_SIM/shared_trace/D_phc_drift_hw_only.jsonl
  bibliography_refs: [26, 27, 28, 29, 30, 31, 44]
---

# /oran-discover:ptp

<Purpose>
Survey the left side of the harness diagram. Tell the operator what PTP synchronization looks like
right now: the linuxptp daemon's reported state, the PHC's measured drift, and what
cloud-event-proxy has published recently. Pre-flight read for any operator who is about to
authorize a routing decision.
</Purpose>

<Use_When>
- The operator wants to know what PTP is doing before reading any alarm
- A reviewer is walking the harness's left loop and wants concrete state
- Pre-talk dry-run: confirm the lab is emitting the alarm pattern the narrative claims
- Scenario D walkthrough: show software_ok vs hardware_anomaly divergence
</Use_When>

<Steps>

1. **Decide live mode vs static mode.** Try `curl -sf --max-time 1 http://localhost:8091/health`.
   If it returns 200, the macbook_lab PTP operator stub is up: live mode. Otherwise: static mode.

2. **Live mode.**
   - `curl -s http://localhost:8091/state` for current published state
   - `curl -s http://localhost:8091/history?limit=20` for recent alarm sequence
   - Parse the response. Each event has `source`, `type`, `time`, and `data.verdict`.

3. **Static mode.**
   - Read `5G_O-RAN_SIM/oam/ptp_operator_stub.py` to see the alarm sequence the stub WOULD emit
   - Read `5G_O-RAN_SIM/shared_trace/D_phc_drift_hw_only.example.jsonl` if present, for the
     canonical example alarm sequence used in the verify gate

4. **Format the survey output.** Always include, in this order:
   - **PTP profile context**: G.8275.1 telecom profile ([ref 44](../../docs/references.md#ref-44)),
     the standard alarm shape (O-RAN WG6 O-Cloud Notification API,
     [ref 31](../../docs/references.md#ref-31)), CloudEvents 1.0 envelope
     ([ref 30](../../docs/references.md#ref-30))
   - **Recent alarms** (live mode) or **alarm pattern** (static mode):
     one line per event with `time | source | type | verdict`
   - **Verdict legend**: `software_ok`, `software_ok_persistent`, `hardware_anomaly`,
     `firmware_anomaly`. The verdict is the disambiguator that drives the routing decision
     downstream.
   - **Scenario hint**: if any event carries `software_ok` and the next carries `hardware_anomaly`
     for the same node, point the operator at scenario D (the software-OK vs hardware-NOT-OK
     divergence pattern).
   - **Citation footer**: linuxptp ([ref 27](../../docs/references.md#ref-27)), Red Hat PTP Operator
     ([ref 28](../../docs/references.md#ref-28)), cloud-event-proxy
     ([ref 29](../../docs/references.md#ref-29)), IEEE 1588-2019
     ([ref 26](../../docs/references.md#ref-26)).

5. **Do not propose a remediation.** This skill is discovery-only. If the alarm sequence calls for
   action, point the operator at `/o-ran:troubleshoot <fault_payload.json>`.

</Steps>

<Determinism_Contract>
Read-only. No POST calls. No state mutation. The survey output is a function of platform state
(live mode) or stub source (static mode), nothing else. Re-running the skill on identical state
produces identical output modulo timestamps.
</Determinism_Contract>

<Verification>
- The HTTP wrapper response shape (live mode) is documented in
  `macbook_lab/http_wrappers/ptp_operator_service.py`. Any change there must update this skill.
- The stub source path (static mode) is `5G_O-RAN_SIM/oam/ptp_operator_stub.py`. Any change there
  must update this skill.
- Citation refs 26, 27, 28, 29, 30, 31, 44 are validated by `harness/conformance.md` membership.
</Verification>
