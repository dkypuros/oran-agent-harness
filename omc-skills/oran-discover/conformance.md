# oran-discover Bundle Conformance

Each skill in this bundle reads from a documented source path and produces a survey output
in a documented shape. This file is the citation-anchored index for those paths.

## Citation table

| Skill                      | Live source (HTTP)                                                            | Static source (file)                                        | Spec refs                                  |
|----------------------------|--------------------------------------------------------------------------------|-------------------------------------------------------------|--------------------------------------------|
| `oran-discover:ptp`        | macbook_lab/http_wrappers/ptp_operator_service.py:1                            | 5G_O-RAN_SIM/oam/ptp_operator_stub.py:1                     | refs 26, 27, 28, 29, 30, 31, 44            |
| `oran-discover:metal3`     | macbook_lab/http_wrappers/metal3_bmo_service.py:1                              | 5G_O-RAN_SIM/oam/metal3_bmo_stub.py:1                       | refs 7, 8                                  |
| `oran-discover:redfish`    | macbook_lab/http_wrappers/redfish_bmc_service.py:1                             | 5G_O-RAN_SIM/oam/redfish_bmc_stub.py:1                      | ref 46                                     |
| `oran-discover:smo`        | macbook_lab/http_wrappers/tmf921_smo_service.py:1                              | 5G_O-RAN_SIM/smo/tmf921_intent_emitter.py:1                 | refs 18, 19                                |
| `oran-discover:taxonomy`   | (no HTTP wrapper, taxonomy is declarative)                                     | harness/taxonomy.yaml:1                                     | refs 2, 3, 8, 9, 10                        |
| `oran-discover:guardrail`  | (no HTTP wrapper, policy is declarative)                                       | harness/guardrails.yaml:1                                   | ref 18                                     |
| `oran-discover:plan`       | composes the six above                                                         | composes the six above                                      | union of the above                         |

## Live mode response shapes

The HTTP wrappers each expose:
- `GET /health` -> `{"service": "<name>", ...}` (200 OK when live)
- `GET /state` -> service-specific current state
- `GET /history?limit=N` -> service-specific event history

Each `oran-discover` skill calls only the GET surface. POST endpoints exist on the wrappers but
are out of scope for discovery and out of scope for this bundle.

Per-service response shape pointers:

| Wrapper                              | Key response fields                                                                         |
|--------------------------------------|---------------------------------------------------------------------------------------------|
| `ptp_operator_service.py`            | `events[*].source`, `events[*].type`, `events[*].time`, `events[*].data.verdict`            |
| `metal3_bmo_service.py`              | `phases[*].component`, `phases[*].phase`, `phases[*].detail`, `phases[*].bytes`             |
| `redfish_bmc_service.py`             | `tasks[*].task_uri`, `tasks[*].task_state`, `tasks[*].percent_complete`, `tasks[*].message` |
| `tmf921_smo_service.py`              | `intents[*].intent_id`, `intents[*].intent_type`, `intents[*].affected_resources`           |

## Static mode source-path inventory

Every static source is committed to the repo and tracked by git. The verify gate's leakage and
schema checks already cover these paths.

```
5G_O-RAN_SIM/oam/ptp_operator_stub.py
5G_O-RAN_SIM/oam/metal3_bmo_stub.py
5G_O-RAN_SIM/oam/redfish_bmc_stub.py
5G_O-RAN_SIM/smo/tmf921_intent_emitter.py
harness/taxonomy.yaml
harness/guardrails.yaml
harness/runtime/guardrail.py
harness/runtime/router.py
harness/schemas/AuditEvent.json
```

## Bibliography ref index (for the bundle as a whole)

| Ref | Source                                                                  | Used by                          |
|-----|-------------------------------------------------------------------------|----------------------------------|
| 2   | O-RAN.WG6 O2 General Aspects and Principles                             | taxonomy                         |
| 3   | O-RAN.WG6 O2 IMS Interface Specification                                | taxonomy, metal3 (DOWN-route)    |
| 7   | Metal3 BareMetalOperator (repo)                                         | metal3                           |
| 8   | Metal3 BareMetalHost / HostFirmwareComponents (CRDs)                    | metal3, taxonomy                 |
| 9   | OpenShift Machine Config Operator                                       | taxonomy                         |
| 10  | KMM Kernel Module Management Operator                                   | taxonomy                         |
| 18  | TMF688 Event Management API                                             | smo, guardrail                   |
| 19  | TMF921 Intent Management API                                            | smo                              |
| 26  | IEEE 1588-2019 (PTP)                                                    | ptp                              |
| 27  | linuxptp                                                                | ptp                              |
| 28  | Red Hat PTP Operator                                                    | ptp                              |
| 29  | cloud-event-proxy                                                       | ptp                              |
| 30  | CNCF CloudEvents 1.0                                                    | ptp                              |
| 31  | O-RAN.WG6 O-Cloud Notification API                                      | ptp                              |
| 44  | ITU-T G.8275.1 (telecom profile)                                        | ptp                              |
| 46  | DMTF Redfish DSP0266                                                    | redfish                          |
