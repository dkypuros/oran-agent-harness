---
name: oran-discover:smo
description: Survey TMF921 intent emission state. Report companion intents the harness has emitted UP toward the partner SMO during dual-route remediations.
argument-hint: "(no arguments)"
level: 1
citation_anchor:
  inputs:
    - ../../5G_O-RAN_SIM/smo/tmf921_intent_emitter.py
    - ../../scenarios/E_nic_firmware_update/companion_intent.json
    - ../../scenarios/E_with_smo_reject/companion_intent.json
    - ../../harness/runtime/router.py
  outputs:
    - ../../5G_O-RAN_SIM/shared_trace/E_nic_firmware_update.jsonl
  bibliography_refs: [18, 19]
---

# /oran-discover:smo

<Purpose>
Survey the right-loop service side. Tell the operator what intents the harness has emitted UP to
the partner SMO (Ericsson, Nokia, Amdocs, Mavenir, ZTE). The harness does not execute service-layer
actions; it emits a TMF921 intent and observes the result. This skill reports those emissions.
</Purpose>

<Use_When>
- Operator wants to see which intents have been emitted toward the SMO recently
- Reviewer is walking the dual-route pattern (scenario E) and wants to see the companion intent
  alongside the Metal3 firmware push
- Pre-flight read before deciding whether a new action will fire a companion intent
</Use_When>

<Steps>

1. **Decide live mode vs static mode.** Try `curl -sf --max-time 1 http://localhost:8094/health`.

2. **Live mode.**
   - `curl -s http://localhost:8094/state` for emission counter and latest intent
   - `curl -s http://localhost:8094/history?limit=20` for full intent history

3. **Static mode.**
   - Read `5G_O-RAN_SIM/smo/tmf921_intent_emitter.py` for the canonical intent envelope shape
   - Read `scenarios/E_nic_firmware_update/companion_intent.json` for the canonical scenario E
     companion intent

4. **Format the survey output.** Always include:
   - **TMF921 context**: TMF921 Intent Management API ([ref 19](../../docs/references.md#ref-19))
     is the standardized contract for SMO-bound intents. The envelope carries `intent_id`,
     `intent_type`, `affected_resources`, `service_impact_hint`,
     `expected_outage_window_minutes`, `dispatch_route`, `rationale`, and (when present) the
     v0 `dispatch_result` subfield. TMF688 ([ref 18](../../docs/references.md#ref-18)) is the
     audit event shape that wraps everything.
   - **The `dispatch_result` field** (v0 implementation): the partner SMO's response to a
     companion intent lands in `companion_intent.dispatch_result` on the AuditEvent, populated
     by `harness/runtime/router.py::_maybe_attach_dispatch_result()` from the per-scenario
     `smo_dispatch_outcome` block in `harness/runtime/scenario_stubs.json`. Surface it as
     `accepted | rejection_reason | smo_response`. The operator sees both routes' outcomes
     before co-authorization.
   - **Dual-route teaching contrast**: scenario E (`scenarios/E_nic_firmware_update/`) shows
     the accepted path (`dispatch_result.accepted: true`, SMO scheduled the handovers).
     Scenario E_with_smo_reject (`scenarios/E_with_smo_reject/`) shows the rejected path
     (`accepted: false`, `rejection_reason: neighboring_cells_at_capacity`). Compare the two
     companion_intent.json fixtures side by side to see the teaching moment.
   - **Recent intents** (live mode) or **intent pattern** (static mode):
     one line per intent with `intent_id | intent_type | affected | dispatch_result.accepted`
   - **Dual-route hint**: a companion intent firing alongside a Metal3 apply is the signature
     of scenario E (both variants). The harness emits it for any `node_firmware` action
     regardless of blast cell count, because firmware reboots require SMO coordination by their
     semantic.
   - **Citation footer**: TMF921 ([ref 19](../../docs/references.md#ref-19)), TMF688
     ([ref 18](../../docs/references.md#ref-18))

5. **Do not emit an intent.** Discovery-only.

</Steps>

<Determinism_Contract>
Read-only. No POST calls. The intent envelope shape is deterministic and matches
`harness/schemas/AuditEvent.json` companion-intent extensions.
</Determinism_Contract>

<Verification>
- HTTP wrapper response shape: `macbook_lab/http_wrappers/tmf921_smo_service.py`.
- Static source: `5G_O-RAN_SIM/smo/tmf921_intent_emitter.py`.
- Canonical intent fixture: `scenarios/E_nic_firmware_update/companion_intent.json`.
- Citation refs 18, 19 are validated by `harness/conformance.md` membership.
</Verification>
