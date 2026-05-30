# O-RAN Specification Coverage Matrix

This matrix links every O-RAN-enhanced module in the emulator back to the exact O-RAN Alliance
specification document it realizes. It is generated from the single source of truth at
`open-digital-platform-2_0/5G_Emulator_API/oran/o_ran_spec_map.py` and served live by the gateway
at `GET /api/oran/spec-coverage`.

Status legend: **OK** = a runnable module realizes the spec's key procedures/data models;
**ref** = the spec's concepts are modeled inside another module (no standalone service).

Source documents live in the O-RAN catalog at
`4Public_Networking_Public_Data/53_O-RAN/O-RAN_Specifications_Bulk/Latest_Versions/`.

## Summary

- **39 implemented + 8 referenced = 47 specifications mapped**
- Spanning **8 working groups**: WG1, WG2, WG3, WG4, WG6, WG9, WG10, WG11
- Out of **167 documents** in the O-RAN specification catalog

| Working group | Implemented | Referenced | Total |
|---|---|---|---|
| WG1 (Use cases / Architecture / Slicing / Energy) | 3 | 2 | 5 |
| WG2 (Non-RT RIC / A1 / R1 / AI-ML) | 6 | 0 | 6 |
| WG3 (Near-RT RIC / E2 / Y1) | 10 | 0 | 10 |
| WG4 (Open Fronthaul) | 2 | 2 | 4 |
| WG6 (O-Cloud / O2) | 3 | 2 | 5 |
| WG9 (xHaul Transport / Sync) | 2 | 1 | 3 |
| WG10 (O1 / OAM / TE&IV) | 6 | 0 | 6 |
| WG11 (Security) | 7 | 1 | 8 |

## WG1 - Use Cases, Architecture, Slicing, Energy

| Spec document | Title | Module | Status |
|---|---|---|---|
| `O-RAN.WG1.TS.OAD-R005-v16.00` | Overall Architecture Description | `smo/smo_framework.py` | OK |
| `O-RAN.WG1.TS.Slicing-Architecture-R004-v14.01` | Slicing Architecture | `ran/slicing/oran_slicing.py` | OK |
| `O-RAN.WG1.Study-on-O-RAN-Slicing-v02.00` | Study on O-RAN Slicing | `ran/slicing/oran_slicing.py` | ref |
| `O-RAN.WG1.Network-Energy-Savings-Technical-Report-R003-v02.00` | Network Energy Savings | `ran/energy/nes.py` | OK |
| `O-RAN.WG1.mMIMO-Use-Cases-TR-v01.00` | mMIMO Use Cases | `ran/energy/nes.py` | ref |

## WG2 - Non-RT RIC, A1, R1, AI/ML

| Spec document | Title | Module | Status |
|---|---|---|---|
| `O-RAN.WG2.TS.Non-RT-RIC-ARCH-R004-v07.00` | Non-RT RIC Architecture | `ran/ric/non_rt_ric.py` | OK |
| `O-RAN.WG2.TS.A1AP-R005-v06.00` | A1 Application Protocol | `ran/ric/a1_interface.py` | OK |
| `O-RAN.WG2.TS.A1TD-R005-v11.01` | A1 Type Definitions | `ran/ric/non_rt_ric.py` | OK |
| `O-RAN.WG2.TS.R1AP-R005-v10.00` | R1 Application Protocol | `smo/r1.py` | OK |
| `O-RAN.WG2.TS.R1GAP-R005-v13.00` | R1 General Aspects & Principles | `smo/r1.py` | OK |
| `O-RAN.WG2.AIML-v01.03` | AI/ML Workflow | `smo/aiml.py` | OK |

## WG3 - Near-RT RIC, E2, Y1

| Spec document | Title | Module | Status |
|---|---|---|---|
| `O-RAN.WG3.TS.E2AP-R004-v08.00` | E2 Application Protocol | `ran/ric/e2ap.py` | OK |
| `O-RAN.WG3.TS.E2GAP-R004-v08.00` | E2 General Aspects & Principles | `ran/ric/near_rt_ric.py` | OK |
| `O-RAN.WG3.TS.RICARCH-R005-v08.00` | Near-RT RIC Architecture | `ran/ric/near_rt_ric.py` | OK |
| `O-RAN.WG3.TS.E2SM-KPM-R004-v07.00` | E2SM Key Performance Measurement | `ran/ric/e2ap.py` | OK |
| `O-RAN.WG3.TS.E2SM-RC-R004-v09.00` | E2SM RAN Control | `ran/ric/e2ap.py` | OK |
| `O-RAN.WG3.TS.E2SM-CCC-R004-v06.00` | E2SM Cell Configuration & Control | `ran/ric/e2sm_ccc.py` | OK |
| `ORAN-WG3.E2SM-NI-v01.00` | E2SM Network Interface | `ran/ric/e2sm_ni.py` | OK |
| `O-RAN.WG3.TS.E2SM-LLC-R004-v01.00` | E2SM Lower Layer Control | `ran/ric/e2sm_llc.py` | OK |
| `O-RAN.WG3.TS.Y1AP-R005-v01.02` | Y1 Application Protocol | `ran/ric/y1.py` | OK |
| `O-RAN.WG3.TS.Y1GAP-R005-v01.02` | Y1 General Aspects & Principles | `ran/ric/y1.py` | OK |

## WG4 - Open Fronthaul

| Spec document | Title | Module | Status |
|---|---|---|---|
| `O-RAN.WG4.TS.CUS.0-R005-v20.00` | Control/User/Synchronization Plane | `ran/fronthaul/cus_plane.py` | OK |
| `O-RAN.WG4.TS.MP.0-R005-v20.00` | Management Plane | `ran/fronthaul/m_plane.py` | OK |
| `O-RAN.WG4.TS.CONF.0-R005-v15.00` | Conformance Test | `ran/fronthaul/o_ru.py` | ref |
| `O-RAN.WG4.CTI-TMP.0-R003-v04.00` | Cooperative Transport Interface (timing) | `ran/fronthaul/cus_plane.py` | ref |

## WG6 - O-Cloud / O2

| Spec document | Title | Module | Status |
|---|---|---|---|
| `O-RAN.WG6.TS.O2IMS-INTERFACE-R005-v11.00` | O2 IMS Interface | `etsi/o2/o2_ims.py` | OK |
| `O-RAN.WG6.TS.O2DMS-INTERFACE-K8S-PROFILE-R005-v07.00` | O2 DMS K8s Profile | `etsi/o2/o2_dms.py` | OK |
| `O-RAN.WG6.O-Cloud Notification API-v04.00` | O-Cloud Notification API | `etsi/o2/o_cloud_notification.py` | OK |
| `O-RAN.WG6.CADS-v08.01` | Cloud Architecture & Deployment Scenarios | `etsi/o2/o2_ims.py` | ref |
| `O-RAN.WG6.ASD-R004-v02.00` | Application Service Descriptor | `etsi/o2/o2_dms.py` | ref |

## WG9 - xHaul Transport / Synchronization

| Spec document | Title | Module | Status |
|---|---|---|---|
| `O-RAN.WG9.XTRP-MGT.0-R004-v10.00` | xHaul Transport Management | `transport/xhaul.py` | OK |
| `O-RAN.WG9.XTRP-SYN.0-R004-v07.00` | xHaul Synchronization | `transport/xhaul.py` | OK |
| `O-RAN.WG9.XPSAAS.0-R005-v10.00` | Packet Switched Architecture | `transport/xhaul.py` | ref |

## WG10 - O1 / OAM / TE&IV

| Spec document | Title | Module | Status |
|---|---|---|---|
| `O-RAN.WG10.TS.O1-Interface.0-R005-v18.00` | O1 Interface | `oam/o1.py` | OK |
| `O-RAN.WG10.TS.O1NRM.0-R004-v04.00` | O1 Network Resource Model | `oam/o1.py` | OK |
| `O-RAN.WG10.TS.O1PMeas-R005-v05.00` | O1 Performance Measurements | `oam/pm.py` | OK |
| `O-RAN.WG10.TS.OAM-Architecture-R005-v17.00` | OAM Architecture | `oam/o1.py` | OK |
| `O-RAN.WG10.TS.TE&IV-API.0-R005-v04.00` | Topology Exposure & Inventory API | `oam/teiv.py` | OK |
| `O-RAN.WG10.TS.TE&IV-DM.0-R005-v04.00` | TE&IV Data Model | `oam/teiv.py` | OK |

## WG11 - Security

| Spec document | Title | Module | Status |
|---|---|---|---|
| `O-RAN.WG11.TS.SecProtSpec.0-R005-v14.00` | Security Protocols Specification | `security/security_service.py` | OK |
| `O-RAN.WG11.TS.SRCS.0-R005-v14.00` | Security Requirements & Controls | `security/security_service.py` | OK |
| `O-RAN.WG11.TS.STS-R005-v12.00` | Security Test Specification | `test_oran_compliance.py` | ref |
| `O-RAN.WG11.TR.ZTA-R005-v05.00` | Zero Trust Architecture | `security/zero_trust.py` | OK |
| `O-RAN.WG11.TR.Threat-Modeling-R005-v08.00` | Threat Modeling & Risk Assessment | `security/zero_trust.py` | OK |
| `O-RAN.WG11.TR.Certficate-Management-Framework.0-R005-v06.00` | Certificate Management Framework | `security/cert_manager.py` | OK |
| `O-RAN.WG11.TR.OAuth2.0-Security.0-R005-v07.00` | OAuth2.0 Security | `security/security_service.py` | OK |
| `O-RAN.WG11.TR.PQC-Security.0-R005-v02.00` | Post-Quantum Cryptography Security | `security/pqc.py` | OK |

## Regenerating this matrix

```bash
cd open-digital-platform-2_0/5G_Emulator_API
python oran/o_ran_spec_map.py        # prints the summary, writes oran/oran_spec_coverage.json
python test_oran_compliance.py       # boots each interface and validates a key procedure
```
