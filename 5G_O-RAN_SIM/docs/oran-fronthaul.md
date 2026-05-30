# O-RAN WG4 Open Fronthaul

## Overview

The Open Fronthaul layer realizes the O-DU to O-RU split defined by O-RAN Alliance WG4. It replaces
the previous 11-line RRU stub (`ran/rru/rru.py`) with a runnable O-RU managed element that models
both planes of the fronthaul interface:

- **M-Plane** (Management Plane) per `O-RAN.WG4.TS.MP.0-R005-v20.00`
- **CUS-Plane** (Control, User, Synchronization) per `O-RAN.WG4.TS.CUS.0-R005-v20.00`

Module layout (`open-digital-platform-2_0/5G_Emulator_API/ran/fronthaul/`):

| File | Role |
|---|---|
| `o_ru.py` | FastAPI O-RU service on port 8120 (M-Plane + CUS-Plane endpoints) |
| `m_plane.py` | YANG-modeled M-Plane datastore (library) |
| `cus_plane.py` | eCPRI / C-Plane / U-Plane / S-Plane data structures + stats (library) |

## M-Plane (Management Plane)

The O-RU is modeled as a NETCONF/YANG managed element. The datastore (`MPlaneDatastore`) carries the
core O-RAN YANG modules:

| YANG module | Content |
|---|---|
| `o-ran-uplane-conf` | low-level tx/rx endpoints, carriers, array-carriers |
| `o-ran-module-cap` | band capabilities, compression capabilities, supported section types |
| `o-ran-supervision` | CU-plane monitoring + supervision watchdog (interval / guard timer) |
| `o-ran-fan` | fan state |
| `o-ran-software-management` | software slots (running / inactive) |
| `o-ran-performance-management` | RSSI / RX-window measurements |
| `o-ran-fm` | active alarm list |

Both the hierarchical and hybrid M-Plane architecture models are represented. The supervision
watchdog can be queried and "pet" (reset) to model the O-DU to O-RU keep-alive.

### Key M-Plane routes (port 8120)

```
GET  /o-ran/hw                  hardware / component inventory
GET  /o-ran/uplane-conf         user-plane configuration (NETCONF get)
PUT  /o-ran/uplane-conf         edit-config (deep merge)
GET  /o-ran/module-cap          module capabilities
GET  /o-ran/supervision         watchdog status
POST /o-ran/supervision/reset   pet the watchdog
POST /o-ran/sw-management/activate   activate a software slot
GET  /o-ran/performance         RSSI / RX-window performance
GET  /o-ran/fm/alarms           active alarms
```

## CUS-Plane (Control, User, Synchronization)

### C-Plane and U-Plane

`cus_plane.py` models the eCPRI transport and the radio data planes:

- **eCPRI message types**: IQ_DATA(0), BIT_SEQUENCE(1), RT_CONTROL_DATA(2), GENERIC_DATA_TRANSFER(3),
  REMOTE_MEM_ACCESS(4), ONE_WAY_DELAY(5), REMOTE_RESET(6), EVENT_INDICATION(7).
- **C-Plane section types**: 0, 1, 3, 5, 6, 7 (idle/guard, most DL/UL beamforming, PRACH, UE
  scheduling, channel info, sounding).
- **U-Plane** IQ frame header: frameId, subframeId, slotId, symbolId, PRB ranges.
- **Compression**: NO_COMPRESSION, BLOCK_FLOATING_POINT, BLOCK_SCALING, U_LAW, MODULATION with the
  on-wire `udCompMeth` code map.
- **Beamforming**: beamId + beam weights.

### S-Plane (Synchronization)

The Synchronization Plane models timing alignment between O-DU and O-RU:

- **PTP profiles**: G.8275.1 (full timing support) and G.8275.2 (partial), plus SyncE / eSyncE.
- **LLS sync topologies**: LLS-C1, LLS-C2, LLS-C3, LLS-C4.
- **Sync states**: LOCKED, HOLDOVER, FREERUN, with clock class, clock accuracy, and a time-error
  budget (the O-RU reports time error against `max_te_budget_ns`).

### Key CUS-Plane routes (port 8120)

```
GET /cus/c-plane/stats     C-Plane section statistics
GET /cus/u-plane/stats     U-Plane IQ statistics
GET /cus/s-plane/sync      PTP/SyncE lock state, clock class, time error
GET /cus/beamforming       beamforming configuration
```

Example `GET /cus/s-plane/sync` response:

```json
{
  "spec": "O-RAN.WG4.TS.CUS.0-R005-v20.00 / O-RAN.WG4.CTI-TMP.0-R003-v04.00",
  "sync_state": "LOCKED",
  "ptp_profile": "G.8275.1",
  "synce_mode": "SYNCE_ENABLED",
  "lls_topology": "LLS-C3",
  "clock_class": 6,
  "clock_accuracy": 33,
  "time_error_ns": 12,
  "max_te_budget_ns": 1100
}
```

## Transport and synchronization context

The fronthaul timing sits inside the broader xHaul transport and synchronization network modeled by
WG9 (`transport/xhaul.py`, port 8131): T-GM / T-BC / T-TSC clock nodes, clock classes, holdover, and
the timing distribution tree. The aggregation gateway surfaces both at
`GET /api/oran/fronthaul` and `GET /api/oran/transport`.

## Scope note

This is a control-and-management-plane realization. Real IQ sample transport, eCPRI on the wire, and
hardware PTP are simulated at the message/model layer, consistent with the rest of the emulator.
