# O-RAN Enhancement Architecture (WG1-WG11)

## Overview

This document describes the O-RAN enhancement layer added on top of the existing 5G core and
RAN emulator. It extends the platform from a RIC-only O-RAN footprint (Near-RT RIC, Non-RT RIC,
E2AP, A1) into a broad, spec-cited realization spanning O-RAN Alliance working groups WG1 through
WG11. Every component is a runnable FastAPI service that registers with the NRF, exposes a
`/health` endpoint, and cites the exact O-RAN specification document it implements.

The authoritative spec-to-code map lives in
`open-digital-platform-2_0/5G_Emulator_API/oran/o_ran_spec_map.py` and is served live by the
aggregation gateway at `GET /api/oran/spec-coverage`. See
[oran-compliance.md](oran-compliance.md) for the full coverage matrix and
[oran-fronthaul.md](oran-fronthaul.md) for the WG4 Open Fronthaul detail.

## What was added

| Working group | Capability | Module(s) | Port |
|---|---|---|---|
| WG1 | Overall architecture / SMO coordinator | `smo/smo_framework.py` | 8122 |
| WG1 | RAN slicing (NSI/NSSI, S-NSSAI, slice SLA, RRM) | `ran/slicing/oran_slicing.py` | 8129 |
| WG1 | Network Energy Savings (sleep modes, energy KPIs) | `ran/energy/nes.py` | 8130 |
| WG2 | R1 interface (SME + DME) for rApps | `smo/r1.py` | 8124 |
| WG2 | AI/ML workflow + model registry | `smo/aiml.py` | (library) |
| WG3 | E2SM-CCC, E2SM-NI, E2SM-LLC service models | `ran/ric/e2sm_*.py` | (registered into E2AP) |
| WG3 | Y1 interface (RAN Analytics exposure) | `ran/ric/y1.py` | 8123 |
| WG4 | Open Fronthaul O-RU (M-Plane + CUS-Plane) | `ran/fronthaul/` | 8120 |
| WG6 | O-Cloud Notification API | `etsi/o2/o_cloud_notification.py` | 8127 |
| WG9 | xHaul transport + PTP/SyncE synchronization | `transport/xhaul.py` | 8131 |
| WG10 | O1 interface (NRM, FCAPS, PM, VES) | `oam/o1.py` | 8125 |
| WG10 | Topology Exposure & Inventory (TE&IV) | `oam/teiv.py` | 8126 |
| WG11 | Security (OAuth2, Zero-Trust, PQC, cert mgmt) | `security/` | 8128 |
| - | Front-end aggregation gateway (:8088) | `api_gateway/oran_gateway.py` | 8088 |

These join the pre-existing Near-RT RIC (8095), Non-RT RIC (8096), O2-IMS (8098), O2-DMS (8099),
SMO O2 facade (8097), RNIS (8092), VNFM (8093), and ZSM (8094).

## System view

```
                     ┌──────────────────────── SMO (WG1 OAD / WG2 Non-RT-RIC-ARCH) ────────────────────────┐
                     │  smo_framework :8122   Non-RT RIC :8096   O1 :8125   O2-IMS/DMS :8098/8099   R1 :8124 │
                     │      (rApps, A1 policy, AI/ML registry, NRM/FCAPS, O-Cloud, R1 SME+DME)               │
                     └───────┬──────────────┬──────────────┬───────────────┬──────────────────┬─────────────┘
                          A1 │           O1 │           O2 │            R1  │           O-Cloud │ Notification :8127
                     ┌───────▼──────────────▼──────────────▼───────────────▼──────────────────▼─────────────┐
                     │                          Near-RT RIC :8095  (xApps)                                   │
                     │     E2AP + E2SM-KPM / E2SM-RC / E2SM-CCC / E2SM-NI / E2SM-LLC          Y1 :8123        │
                     └───────────────────────────────────┬──────────────────────────────────────────────────┘
                                                       E2 │
                     ┌───────────────────────────────────▼──────────────────────────────────────────────────┐
                     │   O-CU  ──F1──►  O-DU  ──Open Fronthaul (eCPRI / C,U,S-Plane / M-Plane)──►  O-RU :8120 │
                     │                              xHaul transport + PTP/SyncE sync :8131                    │
                     └──────────────────────────────────────────────────────────────────────────────────────┘

  Cross-cutting:  WG11 Security :8128 (OAuth2 / Zero-Trust PDP / PQC / cert)   WG1 Slicing :8129   WG1 NES :8130
  Front-end:      gateway :8088  aggregates every function and serves /api/nf/status + /api/oran/*
```

## How it runs

Launch everything (5G core + RAN + O-RAN + gateway) with the platform launcher:

```bash
cd open-digital-platform-2_0
python 5G_Emulator_API/main.py
```

Or bring up just the O-RAN layer + gateway:

```bash
cd open-digital-platform-2_0
./start_oran_services.sh
```

Then point the dashboard at the gateway (default `http://localhost:8088`) and open the new
"O-RAN" view, or query the API directly:

```bash
curl http://localhost:8088/api/oran/overview
curl http://localhost:8088/api/oran/spec-coverage
curl http://localhost:8088/api/oran/fronthaul
```

## Design conventions

- Every service follows the same skeleton: pydantic models for all messages/IEs, enums for code
  points, a core class wrapping the logic, a thin FastAPI app, `CORSMiddleware`, an optional
  OpenTelemetry tracer (no-op fallback so services boot without the OTel SDK), best-effort NRF
  registration in the lifespan, and a `/health` route that returns the implemented spec id.
- Transports are simulated at the message/model layer (REST), consistent with the rest of the
  emulator. Real eCPRI/NETCONF/SCTP wire transport and a real PKI are out of scope.

## Verification

In-process compliance suite (no ports needed):

```bash
cd open-digital-platform-2_0/5G_Emulator_API
python test_oran_compliance.py
```

It boots each interface via FastAPI's TestClient, exercises a key procedure per working group, and
prints the spec-coverage summary (39 implemented + 8 referenced = 47 specs mapped across 8 working
groups, of 167 documents in the O-RAN catalog).
