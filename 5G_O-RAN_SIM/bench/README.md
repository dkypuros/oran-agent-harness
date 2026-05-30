# 5G_O-RAN_SIM research bench

Orchestrator that walks all four scenarios end to end, fires the platform stubs
(PTP operator, Metal3 BMO, Redfish BMC, SMO intent emitter), captures per-stage
records to the shared JSONL trace layer, and produces a comparative summary.

## Quick start

```bash
cd /path/to/oran-agent-harness
python 5G_O-RAN_SIM/bench/runner.py all
```

The directory name `5G_O-RAN_SIM` is not a valid Python module identifier (starts with
a digit and contains a hyphen), so the bench is invoked via direct script path rather
than `python -m`. The script self-adjusts sys.path to make the inner packages
(`bench`, `oam`, `smo`, `shared_trace`, `llm`) importable.

Outputs:

- `5G_O-RAN_SIM/shared_trace/{A_fw_lldp_agent,A_prime_ice_driver,D_phc_drift_hw_only,E_nic_firmware_update}.jsonl`
  (per-scenario traces, gitignored as runtime artifacts)
- `5G_O-RAN_SIM/bench/last_run_summary.md` (markdown summary table, gitignored)
- The same markdown is also printed to stdout

To run a single scenario:

```bash
python 5G_O-RAN_SIM/bench/runner.py E_nic_firmware_update
```

## What each scenario exercises

| Scenario | Alarm pattern | Action | Companion intent |
|---|---|---|---|
| A_fw_lldp_agent | fw-lldp-agent host service contends for PHC | apply_machine_config (MCO) | no |
| A_prime_ice_driver | ice 1.11.17 monotonic PHC drift | apply_kmm_module (KMM) | no |
| D_phc_drift_hw_only | ptp4l SYNCHRONIZED but phc2sys + NIC report drift | apply_kmm_module (KMM) | no |
| E_nic_firmware_update | PHC drift persists after KMM swap, NIC firmware root cause | apply_metal3_firmware (Metal3) | yes (TMF921) |

Only Scenario E exercises the Metal3 BMO + Redfish BMC + TMF921 SMO emitter stubs;
the other three route DOWN through O2 IMS only.

## How it reads

Open `5G_O-RAN_SIM/dashboard/trace_view/` after a bench run to see the per-scenario
timelines side by side.

## Honest scope

The bench is a deterministic harness orchestrator. It does not call out to live
LLM providers (the harness Router uses the deterministic taxonomy lookup, not LLM,
on all four scenarios). It does not push real firmware via Metal3 or Redfish; those
are stubs that simulate the canonical phase sequences. The point is to produce
realistic JSON traces the talk and post-talk analysis can replay.
