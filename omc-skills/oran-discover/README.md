# OMC oran-discover Skill Bundle

Read-before-write companion to the existing `o-ran:` action-oriented bundle. Seven skills that survey
platform state across the harness's instrumented surfaces, in a single namespace so an operator can
walk every layer (left loop, cognitive middle, right loop) before authorizing any remediation.

The `o-ran:` bundle (under `../o-ran/`) does troubleshoot, remediate, sandbox-validation, plan. This
bundle does discover. The pairing is deliberate: discovery is the act that earns the right to act.

## What this bundle does

| Skill                      | Surveys                                                | Reads from                                                         |
|----------------------------|--------------------------------------------------------|--------------------------------------------------------------------|
| `/oran-discover:ptp`       | PTP sync state, PHC drift, cloud-event-proxy alarms    | macbook_lab :8091 (live) or `5G_O-RAN_SIM/oam/ptp_operator_stub.py`|
| `/oran-discover:metal3`    | Metal3 BMO BareMetalHost / HostFirmwareComponents      | macbook_lab :8092 (live) or `5G_O-RAN_SIM/oam/metal3_bmo_stub.py`  |
| `/oran-discover:redfish`   | BMC out-of-band state via DMTF Redfish DSP0266         | macbook_lab :8093 (live) or `5G_O-RAN_SIM/oam/redfish_bmc_stub.py` |
| `/oran-discover:smo`       | TMF921 intent emission, companion intents              | macbook_lab :8094 (live) or `5G_O-RAN_SIM/smo/tmf921_intent_emitter.py`|
| `/oran-discover:taxonomy`  | The 20-entry routing taxonomy grouped by target_layer  | `harness/taxonomy.yaml`                                            |
| `/oran-discover:guardrail` | Deterministic policy: allowlist, caps, crisis_mode     | `harness/guardrails.yaml`                                          |
| `/oran-discover:plan`      | Orchestrator, walks all six in pre-flight order        | all of the above                                                   |

## Dual-mode by design

Every skill in this bundle works in two modes without special flags:

- **Live mode.** If the macbook_lab stack is up (`./macbook_lab/run.sh`), the skill calls the
  corresponding HTTP wrapper from Issue #56 and reports current published state.
- **Static mode.** If the stack is not running, the skill reads the corresponding harness or
  5G_O-RAN_SIM file directly and explains what state WOULD be present.

The skill decides by attempting the HTTP wrapper's `/health` endpoint with a short timeout. The
fall-through is transparent so a user does not need to know which mode they are in.

## Why discover and not just troubleshoot

The existing `o-ran:troubleshoot` skill takes a FaultPayload as input. It assumes the operator has
already received an alarm and wants to walk the evidence chain to an RCA. The `oran-discover` bundle
sits BEFORE that. It is the operator's pre-flight check: what does the platform look like right now,
what are the contracts the harness will enforce, what is in the routing taxonomy that will classify
the next fault? It is a teaching surface and a sanity surface, not an alarm response.

The teaching surface matters for nGRG reviewers because it lets them survey the harness's
instrumented points before reading the talk narrative. Each discovery answers one of the questions
the talk poses, with concrete state instead of prose.

## Running the bundle

```
# Survey the left loop
/oran-discover:ptp

# Survey the right loop, infrastructure side
/oran-discover:metal3
/oran-discover:redfish

# Survey the right loop, service side
/oran-discover:smo

# Survey the middle (the routing and guardrail contracts)
/oran-discover:taxonomy
/oran-discover:guardrail

# Or walk all six in pre-flight order
/oran-discover:plan
```

## File inventory

| File                  | Role                                                              |
|-----------------------|-------------------------------------------------------------------|
| `ptp.md`              | PTP / linuxptp / PHC / cloud-event-proxy state                    |
| `metal3.md`           | Metal3 BMO firmware phases                                        |
| `redfish.md`          | Redfish BMC SimpleUpdate task lifecycle                           |
| `smo.md`              | TMF921 companion intent state                                     |
| `taxonomy.md`         | Routing taxonomy, all entries grouped by target_layer             |
| `guardrail.md`        | Deterministic guardrail policy, allowlist, caps, crisis_mode      |
| `plan.md`             | Orchestrator, calls the six in pre-flight order                   |
| `conformance.md`      | Proves each skill's read paths exist and outputs are well-shaped  |
| `README.md`           | This file                                                         |

## What this bundle is NOT

Not a remediation surface. Not a console. Not a way to mutate state. The HTTP wrappers DO expose
POST endpoints (publish / apply / update / emit), but the `oran-discover` skills only call the GET
endpoints (`/health`, `/state`, `/history`). If you want to trigger an alarm sequence or fire an
intent, use curl directly or the existing `o-ran:remediate` skill.
