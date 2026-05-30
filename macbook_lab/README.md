# MacBook lab

A lightweight Docker Compose orchestration that spins up the whole harness platform on a
MacBook with one command. No Red Hat OpenShift, no vendor hardware, no remote SMO. Just
Docker Desktop and (optionally) an Anthropic or OpenAI API key.

The goal is accessibility. Clone the repo, drop a key in `.env` if you have one, run
`./run.sh`, open the dashboard in a browser, watch the harness move.

## Prereqs

- macOS with Docker Desktop running (or any Docker-supporting OS; Linux works the same way)
- That's it.

## Quick start

```bash
cd macbook_lab
cp .env.example .env       # optional, run.sh does this for you on first call
./run.sh                   # builds and starts all containers
```

First run takes a few minutes (downloads python:3.11-slim, builds 7 small images).
Subsequent runs reuse the layers.

When the lab is up, open any of these in your browser:

| URL                                                            | What it is                                          |
|----------------------------------------------------------------|-----------------------------------------------------|
| http://localhost:8097                                          | React dashboard (when Issue #57 is built)           |
| http://localhost:8095/dashboard/trace_view/index.html          | Static HTML trace timeline viewer                   |
| http://localhost:8096/health                                   | Harness walker HTTP API                             |
| http://localhost:8091/health                                   | PTP operator alarm publisher                        |
| http://localhost:8092/health                                   | Metal3 BMO firmware push                            |
| http://localhost:8093/health                                   | Redfish BMC SimpleUpdate                            |
| http://localhost:8094/health                                   | TMF921 SMO companion intent emitter                 |
| http://localhost:8090/                                         | Fake OpenShift AI vLLM mock                         |

## What's in the lab

Eight services, glued together by `docker-compose.yml`:

| Container             | Port | What it is                                                            |
|-----------------------|------|-----------------------------------------------------------------------|
| `fake-vllm`           | 8090 | OpenShift AI vLLM mock returning canned disambiguation responses      |
| `ptp-operator-stub`   | 8091 | Publishes CloudEvents matching O-RAN.WG6 O-Cloud Notification API     |
| `metal3-bmo-stub`     | 8092 | Firmware push phase sequence (Preparing through Updated)              |
| `redfish-bmc-stub`    | 8093 | DMTF Redfish DSP0266 SimpleUpdate task lifecycle                      |
| `tmf921-smo-stub`     | 8094 | TMF921 Intent envelope builder                                        |
| `trace-viewer`        | 8095 | Static HTML timeline viewer over the per-scenario JSONL traces        |
| `harness-walker`      | 8096 | HTTP API around the deterministic Router and Guardrail walker         |
| `dashboard` (#57)     | 8097 | React + shadcn UI, 6 tabs (only built when `--profile dashboard`)     |

## What you can do once it's running

Run all 4 scenarios end-to-end via the bench:

```bash
curl http://localhost:8096/bench/all | jq
```

Walk one scenario:

```bash
curl http://localhost:8096/run/E_nic_firmware_update | jq
```

Trigger a PTP alarm publish:

```bash
curl -X POST 'http://localhost:8091/publish?scenario_id=D_phc_drift_hw_only'
```

Trigger a Metal3 firmware apply:

```bash
curl -X POST 'http://localhost:8092/apply?scenario_id=E_nic_firmware_update'
```

Emit a TMF921 SMO companion intent:

```bash
curl -X POST 'http://localhost:8094/emit?scenario_id=E_nic_firmware_update'
```

Get the per-scenario JSONL trace:

```bash
curl http://localhost:8096/traces/E_nic_firmware_update | jq
```

## Stop everything

```bash
./stop.sh
```

## What you're seeing

The lab demonstrates the three loops of the harness pattern:

- **Left loop (observe)**: the PTP operator stub publishes alarms in O-RAN WG6 O-Cloud
  Notification API format. The harness walker ingests them and runs the deterministic Router.
- **Middle (decide)**: the Router does a taxonomy lookup; the Guardrail engine evaluates four
  rules; the LLM substrate (via fake vLLM) handles ambiguous classifications.
- **Right loop (apply)**: the Metal3 BMO and Redfish BMC stubs show the firmware push phases.
  For Scenario E, the TMF921 SMO emitter fires a companion intent in parallel (the dual-route
  pattern).

Each pipeline stage writes one record to the per-scenario JSONL trace file. The trace viewer
renders them as a color-coded timeline so you can see the flow visually.

## Customizing the lab

- Add your real Anthropic or OpenAI API key to `.env`, set `LLM_PROVIDER=anthropic` or
  `openai`, and the harness Router will route through the real provider on ambiguous_path
  when `ORAN_LLM_MODE=live` is set.
- Edit the platform stubs at `5G_O-RAN_SIM/oam/*.py` and `5G_O-RAN_SIM/smo/*.py` and rebuild.
  The HTTP wrappers in `macbook_lab/http_wrappers/` are thin layers over the stub functions.
- Add a new scenario under `scenarios/<name>/` with the 5-fixture pattern, add a row to
  `harness/conformance.md`, add a stub block to `harness/runtime/scenario_stubs.json`. Then
  the walker, the bench, the trace viewer, and the dashboard all pick it up automatically.

## Honest scope

This is a research lab, not a production deployment. Every platform stub returns canned data;
the fake vLLM does not load a model; Metal3 and Redfish stubs do not actually push firmware;
the SMO emitter writes envelopes nobody consumes. The point is to make the harness pattern
visible and explorable on a single MacBook.

For the full-fledged environment with Red Hat OpenShift, vendor hardware (Dell + Intel), and a
real partner SMO, see the offline notes; the MacBook lab is the accessible-first-step path.

## Layout

```
macbook_lab/
├── README.md                     this file
├── docker-compose.yml            8 services
├── .env.example                  key template
├── run.sh                        one-command launcher
├── stop.sh                       teardown
├── Dockerfile.harness-walker     python:3.11-slim + harness + bench + http_wrappers
├── Dockerfile.platform-stub      shared image for the 4 stubs (build-arg per service)
├── Dockerfile.fake-vllm          python:3.11-slim + fake vLLM mock
├── Dockerfile.trace-viewer       python:3.11-slim + static HTML server
├── Dockerfile.dashboard          node:20-alpine + Vite dev server (Issue #57)
├── http_wrappers/
│   ├── ptp_operator_service.py
│   ├── metal3_bmo_service.py
│   ├── redfish_bmc_service.py
│   ├── tmf921_smo_service.py
│   └── harness_walker_service.py
├── scripts/
│   ├── bench_run.sh
│   └── tail_traces.sh
└── dashboard/                    React + shadcn UI (Issue #57)
```
