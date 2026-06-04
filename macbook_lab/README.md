# MacBook lab

A lightweight Docker Compose orchestration that spins up the whole harness platform on a
MacBook with one command. No Red Hat OpenShift cluster, no vendor hardware, no remote
SMO. Just Docker Desktop and, for live chat/LLM-assist, a provider key or an on-prem
OpenAI-compatible vLLM endpoint.

The goal is accessibility. Clone the repo, drop your Anthropic key in `anthropic.env`
for the dashboard chat service, optionally configure OpenAI API or OpenShift AI vLLM
in `.env` for the Router's ambiguous-path LLM seam, run `./run.sh`, open the dashboard
in a browser, and watch the harness move.

## Prereqs

- macOS with Docker Desktop running (or any Docker-supporting OS; Linux works the same way)
- That's it.

## Quick start

```bash
cd macbook_lab
cp .env.example .env       # optional, run.sh does this for you on first call
cp anthropic.env.example anthropic.env  # optional, needed for oh-my-tiny-oran chat
./run.sh                   # builds and starts all containers
```

First run takes a few minutes (downloads base images and builds the lab images).
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
| http://localhost:8098/health                                   | oh-my-tiny-oran chat service                        |

## What's in the lab

Eight services, glued together by `docker-compose.yml` when the dashboard profile is
enabled:

| Container             | Port | What it is                                                            |
|-----------------------|------|-----------------------------------------------------------------------|
| `ptp-operator-stub`   | 8091 | Publishes CloudEvents matching O-RAN.WG6 O-Cloud Notification API     |
| `metal3-bmo-stub`     | 8092 | Firmware push phase sequence (Preparing through Updated)              |
| `redfish-bmc-stub`    | 8093 | DMTF Redfish DSP0266 SimpleUpdate task lifecycle                      |
| `tmf921-smo-stub`     | 8094 | TMF921 Intent envelope builder                                        |
| `trace-viewer`        | 8095 | Static HTML timeline viewer over the per-scenario JSONL traces        |
| `harness-walker`      | 8096 | HTTP API around the deterministic Router and Guardrail walker         |
| `dashboard`           | 8097 | React + shadcn UI, including the chat tab                             |
| `harness-chat`        | 8098 | oh-my-tiny-oran agent loop using `ANTHROPIC_API_KEY`                  |

## What you can do once it's running

Run all 5 scenarios end-to-end via the bench:

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
  rules; when `ORAN_LLM_MODE=live`, the LLM substrate can call Anthropic, the OpenAI API,
  or an OpenAI-compatible on-prem vLLM endpoint such as Red Hat OpenShift AI for ambiguous
  classifications.
- **Right loop (apply)**: the Metal3 BMO and Redfish BMC stubs show the firmware push phases.
  For Scenario E, the TMF921 SMO emitter fires a companion intent in parallel (the dual-route
  pattern).

Each pipeline stage writes one record to the per-scenario JSONL trace file. The trace viewer
renders them as a color-coded timeline so you can see the flow visually.

## Dashboard modes

The React dashboard has two modes:

- **Simple demo**: a focused left-loop/right-loop story for presentations. The canonical
  entry condition is a PTP sync drift / timing alarm. The left loop shows the alert and
  its harness together: evidence gathering, correlation, and recommendation toward a likely
  NIC timestamp / PHC hardware issue. The right loop shows remediation and its harness
  together as a real oh-my-tiny-oran chat experience: the operator approves the chat
  harness, chooses or edits a slash-command prompt such as `/oran-discover:guardrail`,
  presses Enter, and the assistant inspects live harness-walker output. Human approval is
  required before the right-loop chat runs, and production remediation remains blocked.
- **Advanced**: the original full inspection surface with Overview, oh-my-tiny-oran, SMO,
  Hardware Manager, O-Cloud, Alerts, and PTP sync logs.

The LLM is intentionally not load-bearing in the simple demo. It explains and summarizes;
evidence, standards-backed interfaces, harness-walker output, sandboxing, and human approval
carry the workflow.

## Customizing the lab

- Add your real Anthropic key to `anthropic.env` for the dashboard chat service.
  `run.sh` loads `.env` first, then `anthropic.env` as an Anthropic-only override.
- For the harness Router's ambiguous path, set `LLM_PROVIDER=anthropic`, `openai`, or
  `vllm`. Use `OPENAI_API_KEY` for the OpenAI API. Use `VLLM_BASE_URL` for an on-prem
  OpenAI-compatible vLLM endpoint, for example a Red Hat OpenShift AI route.
- Edit the platform stubs at `5G_O-RAN_SIM/oam/*.py` and `5G_O-RAN_SIM/smo/*.py` and rebuild.
  The HTTP wrappers in `macbook_lab/http_wrappers/` are thin layers over the stub functions.
- Add a new scenario under `scenarios/<name>/` with the 5-fixture pattern, add a row to
  `harness/conformance.md`, add a stub block to `harness/runtime/scenario_stubs.json`. Then
  the walker, the bench, the trace viewer, and the dashboard all pick it up automatically.

## Honest scope

This is a research lab, not a production deployment. Every platform stub returns canned data;
Metal3 and Redfish stubs do not actually push firmware; the SMO emitter writes envelopes nobody
consumes. The LLM path is real only when you provide a real provider configuration. The point is
to make the harness pattern visible and explorable on a single MacBook without pretending the
stubs are production systems.

For the full-fledged environment with Red Hat OpenShift, vendor hardware (Dell + Intel), and a
real partner SMO, see the offline notes; the MacBook lab is the accessible-first-step path.

## Layout

```
macbook_lab/
├── README.md                     this file
├── docker-compose.yml            lab services
├── .env.example                  key template
├── run.sh                        one-command launcher
├── stop.sh                       teardown
├── Dockerfile.harness-walker     python:3.11-slim + harness + bench + http_wrappers
├── Dockerfile.platform-stub      shared image for the 4 stubs (build-arg per service)
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
