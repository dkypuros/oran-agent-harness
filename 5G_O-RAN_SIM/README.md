# 5G_O-RAN_SIM (platform substrate for the agentic harness)

## About this subtree

This directory carries a wholesale copy of the **BF3-5G-Demo** project authored by David Kypuros
and originally maintained in the offline workspace at
`/Users/davidkypuros/Documents/Git_Offline/active/9.LABS_5G_lab_simulator/BF3-5G-Demo/`.
It is included in the public oran-agent-harness repository as the **platform substrate** that
the agentic harness operates on top of: SMO, CU/DU, O-Cloud, Open Fronthaul O-RU, Near-RT RIC,
Non-RT RIC, OAM, Security. Together with the harness, it forms the full closed-loop demo
stack for the O-RAN nGRG Workshop on 4th [THU] JUN 2026.

## License

Re-licensed from **GPL v3** (original BF3-5G-Demo LICENSE) to **Apache License 2.0** by the
author, David Kypuros, who holds copyright on both projects. The parent repository's
`LICENSE` file at the repo root governs this subtree. No separate LICENSE file is included
inside this directory.

## How this fits the harness

The agentic harness at `harness/` is a stub-only declarative artifact set. The wholesale-copied
5G simulator here is a runnable platform layer that the harness can target. The integration
seam is at `harness/runtime/router.py` `ambiguous_path`: when the `ORAN_LLM_MODE=live`
environment variable is set, the router calls into `5G_O-RAN_SIM/llm/inference_client.py`
which routes to Anthropic, OpenAI, or a local OpenShift AI vLLM mock per the configured
provider in `5G_O-RAN_SIM/.env` (see `.env.example`).

The 13 O-RAN service implementations span WG1 (Architecture, Decoupled SMO, Slicing,
Energy), WG2 (Non-RT RIC, A1, R1), WG3 (Near-RT RIC, E2 service models), WG4 (Open Fronthaul
M-Plane and CUS-Plane), WG6 (O-Cloud, O2 IMS, Cloud Notifications), WG9 (xHaul transport,
PTP/SyncE), WG10 (O1, TE&IV, OAM), and WG11 (security: OAuth2, ZTA PDP, certs, PQC).

## Quick start

```bash
cd 5G_O-RAN_SIM/open-digital-platform-2_0
python 5G_Emulator_API/main.py          # full stack including O-RAN + gateway :8088
# or just the O-RAN layer:
./start_oran_services.sh
# in-process compliance suite:
cd 5G_Emulator_API && python test_oran_compliance.py
# live spec coverage:
curl http://localhost:8088/api/oran/spec-coverage
```

## Verify gate scope

The harness verify gate at `scripts/verify.py` does **not** apply to this subtree. The
existing 10/10 checks run only against `harness/` and `scenarios/`. This directory has its
own test suite (`open-digital-platform-2_0/test_oran_compliance.py`, 14/14 passing in
source) and is validated independently.

---

The original BF3-5G-Demo README content follows below.

---

# BF3-5G-Demo

![5G](https://img.shields.io/badge/5G%20Core-Network%20Emulator-blue.svg)
![Platform](https://img.shields.io/badge/platform-BlueField--3%20DPU-green.svg)
![Status](https://img.shields.io/badge/status-100%25%203GPP%20Compliant-gold.svg)
![DOCA](https://img.shields.io/badge/DOCA%20SDK-2.6.0+-orange.svg)

> **🎉 [100% 3GPP Release 16](docs/3gpp-compliance.md) compliant [5G network emulation](docs/README.md) with [NVIDIA BlueField-3 DPU](BF-Emulator.md) integration**

A **world-class [5G network simulation platform](docs/README.md)** achieving **[100% 3GPP Release 16 compliance](docs/3gpp-compliance.md)** with complete [core network emulation](docs/core-network.md), full [RAN implementation](docs/ran-components.md), and **production-grade [N6 interface firewall](N6.md)** powered by [NVIDIA BlueField-3 DPUs](BF-Emulator.md) with [DOCA SDK](open-digital-platform-2_0/n6-interface-simulation/README.md).

## 🏗️ Architecture Integration with DOCA SDK

The platform leverages [NVIDIA's DOCA SDK](BF-Emulator.md) and [BlueField-3 DPU emulation](open-digital-platform-2_0/n6-interface-simulation/README.md) to create a unique hybrid architecture where the 5G core network simulation interfaces directly with hardware-accelerated packet processing. The [UPF-Enhanced](open-digital-platform-2_0/5G_Emulator_API/core_network/upf_enhanced.py) component implements real [GTP-U packet processing](docs/core-network.md#gtp-u) that seamlessly integrates with the [DOCA Flow API](open-digital-platform-2_0/n6-interface-simulation/README.md#doca-flow), enabling the N6 interface firewall to process 5G user plane traffic at line-rate speeds up to 400 Gbps. This integration allows the platform to bridge the gap between software-based 5G network simulation and hardware-accelerated security processing, providing a realistic environment for testing 5G network behavior under real-world traffic conditions with production-grade firewall capabilities.

---

## 🚀 Key Features

- **🏗️ [100% Compliant 5G Core Network](docs/core-network.md)**: [AMF-NAS](open-digital-platform-2_0/5G_Emulator_API/core_network/amf_nas.py), [SMF](open-digital-platform-2_0/5G_Emulator_API/core_network/smf.py), [UPF-Enhanced](open-digital-platform-2_0/5G_Emulator_API/core_network/upf_enhanced.py), [NRF](open-digital-platform-2_0/5G_Emulator_API/core_network/nrf.py), [AUSF](open-digital-platform-2_0/5G_Emulator_API/core_network/ausf.py), [UDM](open-digital-platform-2_0/5G_Emulator_API/core_network/udm.py), [PCF](open-digital-platform-2_0/5G_Emulator_API/core_network/pcf.py) with complete [3GPP protocols](docs/3gpp-compliance.md)
- **📡 [100% Compliant RAN](docs/ran-components.md)**: Complete [CU](open-digital-platform-2_0/5G_Emulator_API/ran/cu.py)/[DU](open-digital-platform-2_0/5G_Emulator_API/ran/du.py) split, [F1AP](docs/ran-components.md#f1ap), [RRC](docs/ran-components.md#rrc), and full [protocol stack](docs/ran-components.md#protocol-stack) ([PDCP](docs/ran-components.md#pdcp)/[RLC](docs/ran-components.md#rlc)/[MAC](docs/ran-components.md#mac)/[PHY](docs/ran-components.md#phy))
- **🛡️ [N6 Interface Firewall](N6.md)**: Production-grade [BlueField-3 DPU firewall](open-digital-platform-2_0/n6-interface-simulation/README.md) with [DOCA SDK](BF-Emulator.md)
- **🔄 Hardware Acceleration**: Line-rate packet processing up to 400 Gbps
- **📊 [Real-time Monitoring](docs/testing.md#monitoring)**: [OpenTelemetry](open-digital-platform-2_0/Dashboard/README.md) integration with comprehensive [dashboards](open-digital-platform-2_0/Dashboard/)
- **🧪 [Testing Framework](docs/testing.md)**: [Automated testing](open-digital-platform-2_0/test_100_compliance.py) for all network components
- **⏱️ PTP Synchronization**: Precision Time Protocol for network synchronization
- **🛰️ [O-RAN Enhanced (WG1-WG11)](docs/oran-architecture.md)**: Broad O-RAN Alliance realization across every working group (see below)

---

## 🛰️ O-RAN Enhancement (WG1-WG11)

The platform is **O-RAN enhanced** with runnable, spec-cited FastAPI services spanning every O-RAN
Alliance working group. **47 O-RAN specification documents** are mapped to code (39 implemented + 8
referenced) across **8 working groups**, drawn from the 167-document O-RAN catalog. Each service
registers with the NRF, exposes `/health`, and cites the exact spec it realizes.

| WG | Capability | Module(s) | Port |
|----|-----------|-----------|------|
| **WG4** | [Open Fronthaul O-RU](docs/oran-fronthaul.md): M-Plane (YANG) + CUS-Plane (eCPRI, C/U/S-plane, BFP, PTP/SyncE, LLS-C1..C4) | `ran/fronthaul/` | 8120 |
| **WG3** | E2 service models **CCC / NI / LLC** (added to KPM/RC) + **Y1** RAN Analytics | `ran/ric/e2sm_*.py`, `ran/ric/y1.py` | 8123 |
| **WG2** | **R1** interface (SME + DME) for rApps + AI/ML workflow registry | `smo/r1.py`, `smo/aiml.py` | 8124 |
| **WG1** | SMO framework, **RAN slicing** (NSI/NSSI/SLA), **Network Energy Savings** | `smo/smo_framework.py`, `ran/slicing/`, `ran/energy/` | 8122 / 8129 / 8130 |
| **WG10** | **O1** interface (NRM, FCAPS, PM, VES) + **TE&IV** topology/inventory | `oam/` | 8125 / 8126 |
| **WG6** | **O-Cloud** O2-IMS/DMS enhancement + Notification API | `etsi/o2/` | 8127 |
| **WG11** | **Security**: OAuth2, Zero-Trust PDP, cert management, PQC readiness | `security/` | 8128 |
| **WG9** | **xHaul** transport + PTP/SyncE sync (T-GM/T-BC/T-TSC) | `transport/xhaul.py` | 8131 |

A front-end **aggregation gateway on `:8088`** (`api_gateway/oran_gateway.py`) aggregates every
function and serves the new `/api/oran/*` surface plus the live spec-coverage matrix; the dashboard
gains a dedicated **O-RAN** view.

```bash
# Bring up the O-RAN layer + gateway
cd open-digital-platform-2_0
./start_oran_services.sh

# Validate (in-process, no ports needed)
cd 5G_Emulator_API && python test_oran_compliance.py

# Live coverage
curl http://localhost:8088/api/oran/spec-coverage
```

**Docs:** [O-RAN Architecture](docs/oran-architecture.md) | [Open Fronthaul (WG4)](docs/oran-fronthaul.md) | [Spec Coverage Matrix](docs/oran-compliance.md)

---

## 🛡️ N6 Interface Firewall

### NEW: Production-Grade BlueField-3 DPU Integration
- **[Hardware Acceleration](BF-Emulator.md#hardware-acceleration)**: [DOCA Flow API](open-digital-platform-2_0/n6-interface-simulation/README.md#doca-flow) integration
- **Line-Rate Processing**: Up to 400 Gbps throughput  
- **Real-time Security**: Advanced packet filtering and blocking
- **[DevEmu Testing](open-digital-platform-2_0/n6-interface-simulation/scripts/test_with_devemu.sh)**: Complete hardware emulation for development

[📖 **Detailed N6 Firewall Documentation**](open-digital-platform-2_0/n6-interface-simulation/README.md)

### Demo Execution
```bash
# Complete N6 firewall validation
cd open-digital-platform-2_0/n6-interface-simulation
./scripts/test_with_devemu.sh     # See N6.md for details
```

**Quick Navigation:**
- 🗺️ **[Architecture Overview](docs/README.md#architecture-overview)** - System architecture diagrams
- 🏗️ **[Core Network Setup](docs/core-network.md#quick-start)** - AMF, SMF, UPF, NRF, AUSF, UDM, PCF
- 📡 **[RAN Setup](docs/ran-components.md#quick-start)** - gNodeB, CU, DU configuration
- 🧪 **[Testing Guide](docs/testing.md#running-tests)** - Comprehensive test execution
- 🛡️ **[Firewall Demo](open-digital-platform-2_0/n6-interface-simulation/README.md#demo)** - N6 interface security

**Expected Results:**
- ✅ Baseline N6 connectivity validation
- 🔥 Firewall blocking demonstration  
- 📊 Real-time packet processing statistics

---

## 📊 Enterprise Features

### [5G Core Network Simulation](docs/core-network.md) ([100% 3GPP Compliant](docs/3gpp-compliance.md))
- **[AMF-NAS](open-digital-platform-2_0/5G_Emulator_API/core_network/amf_nas.py)**: Complete [NAS protocol](docs/core-network.md#amf-nas) support ([TS 24.501](docs/3gpp-compliance.md#ts-24501))
- **[SMF](open-digital-platform-2_0/5G_Emulator_API/core_network/smf.py)**: [Session Management](docs/core-network.md#smf) with [IPv6 support](docs/core-network.md#ipv6) ([TS 29.502](docs/3gpp-compliance.md#ts-29502))  
- **[UPF-Enhanced](open-digital-platform-2_0/5G_Emulator_API/core_network/upf_enhanced.py)**: Real [GTP-U processing](docs/core-network.md#gtp-u) with advanced [QoS](docs/core-network.md#qos) ([TS 29.281](docs/3gpp-compliance.md#ts-29281))
- **[PCF](open-digital-platform-2_0/5G_Emulator_API/core_network/pcf.py)**: Complete [policy control](docs/core-network.md#pcf) with dynamic [QoS](docs/core-network.md#qos) ([TS 29.507](docs/3gpp-compliance.md#ts-29507))
- **[NRF](open-digital-platform-2_0/5G_Emulator_API/core_network/nrf.py)**: Full [service registry](docs/core-network.md#nrf) with [OAuth2](docs/core-network.md#oauth2) ([TS 29.510](docs/3gpp-compliance.md#ts-29510))
- **[AUSF](open-digital-platform-2_0/5G_Emulator_API/core_network/ausf.py)**: [5G-AKA authentication](docs/core-network.md#ausf) ([TS 29.509](docs/3gpp-compliance.md#ts-29509))
- **[UDM](open-digital-platform-2_0/5G_Emulator_API/core_network/udm.py)**: Complete [data management](docs/core-network.md#udm) ([TS 29.503](docs/3gpp-compliance.md#ts-29503))

### [RAN Simulation](docs/ran-components.md) ([100% 3GPP Compliant](docs/3gpp-compliance.md))
- **[CU](open-digital-platform-2_0/5G_Emulator_API/ran/cu.py)**: [F1AP](docs/ran-components.md#f1ap) and [RRC protocol](docs/ran-components.md#rrc) implementation ([TS 38.463](docs/3gpp-compliance.md#ts-38463), [TS 38.331](docs/3gpp-compliance.md#ts-38331))
- **[DU](open-digital-platform-2_0/5G_Emulator_API/ran/du.py)**: Complete [protocol stack](docs/ran-components.md#protocol-stack) - [MAC](docs/ran-components.md#mac)/[RLC](docs/ran-components.md#rlc)/[PDCP](docs/ran-components.md#pdcp)/[PHY](docs/ran-components.md#phy) ([TS 38.321-323](docs/3gpp-compliance.md#ts-38321), [TS 38.201](docs/3gpp-compliance.md#ts-38201))
- **[gNodeB](open-digital-platform-2_0/5G_Emulator_API/ran/gnb.py)**: Full [NGAP implementation](docs/ran-components.md#ngap) ([TS 38.413](docs/3gpp-compliance.md#ts-38413))

### [Monitoring & Observability](docs/testing.md#monitoring)
- **[Real-time Dashboards](open-digital-platform-2_0/Dashboard/)**: System performance and metrics
- **[OpenTelemetry Integration](docs/testing.md#telemetry)**: Comprehensive telemetry data
- **[Performance Monitoring](docs/testing.md#performance)**: Throughput and latency analysis
- **[Security Analytics](open-digital-platform-2_0/n6-interface-simulation/README.md#monitoring)**: Firewall events and blocked traffic

---

## ⚡ Quick Start

### Prerequisites
![Fedora](https://img.shields.io/badge/Fedora-39+-orange.svg)
![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)
![DOCA](https://img.shields.io/badge/DOCA%20SDK-2.6.0+-green.svg)

### Installation & Launch
```bash
# 1. Clone repository
git clone https://github.com/drcoopertbbt/BF3-5G-Demo.git
cd BF3-5G-Demo

# 2. Start 5G network emulation
cd open-digital-platform-2_0
pip install -r requirements.txt
python main.py                    # Platform launcher

# 3. Run comprehensive 100% compliance tests
python test_100_compliance.py    # Full 3GPP validation

# 4. Test N6 interface firewall (BlueField-3 DPU)
cd n6-interface-simulation
./scripts/test_with_devemu.sh     # Hardware firewall demo
```

---

## 📁 Project Structure

```bash
BF3-5G-Demo/
├── 🏗️ open-digital-platform-2_0/      # Complete 5G network simulation
│   ├── 5G_Emulator_API/              # Core 5G network functions
│   │   ├── core_network/             # AMF-NAS, SMF, UPF, NRF, AUSF, UDM, PCF
│   │   └── ran/                      # gNodeB, CU, DU
│   ├── n6-interface-simulation/      # BlueField-3 DPU firewall
│   ├── Dashboard/                    # Monitoring dashboards
│   ├── test_100_compliance.py       # Comprehensive test suite
│   └── main.py                       # Platform launcher
├── 📚 docs/                          # Complete documentation
│   ├── README.md                     # Main documentation
│   ├── 3gpp-compliance.md           # 100% compliance details
│   ├── core-network.md              # Core network components
│   ├── ran-components.md            # RAN implementation
│   └── testing.md                   # Testing framework
├── 📚 N6.md                          # N6 interface documentation
├── 🛡️ BF-Emulator.md                 # BlueField emulator guide
└── 📋 README.md                      # This file
```

---

## 🏷️ Version Information

![Version](https://img.shields.io/badge/version-2.0-blue.svg)
![Build](https://img.shields.io/badge/build-August%202024-green.svg)
![Platform](https://img.shields.io/badge/platform-Multi--Platform-orange.svg)

- **Version**: 2.0  
- **Build Date**: August 2024
- **[5G Core](docs/core-network.md)**: [100% Release 16 compliant](docs/3gpp-compliance.md)
- **[DOCA SDK](BF-Emulator.md)**: 2.6.0+
- **Target Platforms**: x86_64, ARM64 (BlueField-3)
- **Supported OS**: Fedora 39+, RHEL 9+

---

<div align="center">

**🌟 BF3-5G-Demo - Enterprise 5G Network Simulation with BlueField-3 DPU 🌟**

![5G](https://img.shields.io/badge/5G%20Core-Network%20Simulation-blue.svg)
![BlueField](https://img.shields.io/badge/BlueField--3-DPU%20Ready-green.svg)
![Enterprise](https://img.shields.io/badge/Enterprise-Grade-gold.svg)

**[📖 Complete Documentation](docs/README.md)** | **[🎉 100% Compliance Details](docs/3gpp-compliance.md)** | **[🏗️ Core Network Guide](docs/core-network.md)** | **[📡 RAN Components](docs/ran-components.md)** | **[🧪 Testing Framework](docs/testing.md)** | **[🛡️ N6 Firewall Guide](open-digital-platform-2_0/n6-interface-simulation/README.md)** | **[📋 N6 Interface Spec](N6.md)** | **[🔧 BlueField Guide](BF-Emulator.md)** | **[📝 Changelog](CHANGELOG.md)**

</div>
