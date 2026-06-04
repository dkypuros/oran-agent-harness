# O-RAN Agent Harness

Research bench for closed-loop O-RAN remediation in multivendor Cloud RAN day-2 operations. The
bench is the durable artifact: citation-anchored declarative contracts under `harness/`, a runnable
platform substrate under `5G_O-RAN_SIM/`, five walkthrough scenarios under `scenarios/`, two OMC
skill bundles under `omc-skills/`, a Mac-local lab under `macbook_lab/`, and a Fedora + podman
sibling under `linux_lab/` (verified end-to-end on Fedora 42 + podman 5.4.1; see
`linux_lab/verified_runs/`). One appearance of the
bench is the talk *From Multivendor Diagnosis to Closed-Loop Remediation: An Agent Harness for
Cloud RAN Day-2* at the O-RAN nGRG Workshop, Seattle, 4th [THU] JUN 2026, with submission
artifacts under `talk/`. Long-form per-audience narratives that draw on the bench live under
`narratives/`. The talk is one moment; the bench is durable.

**Two front doors.** Coming from the nGRG talk and want the box-check walk? Start at
`talk/runsheet_25min.md` or the public conference handoff page at
`https://dkypuros.github.io/oran-agent-harness/`. Trying to use this as a research substrate
for your own closed-loop work? Start at `narratives/README.md`.

**Empirical MacBook two-loop demo.** The Mac-local dashboard also exposes a reviewer-operable
slice of the harness: open `http://localhost:8097`, use `/commands` to show the scoped
slash-command surface, run `/oran-discover:plan` for a read-only pre-flight survey, switch among
the D/E/E-reject remediation slices, run the `harness-walker` sidecar to attach the live
`AuditEvent`, and then ask the assistant to explain what the run proved and what remains blocked
behind the operator. The endpoints are stubs; the routing decision, guardrail result, sandbox
verdict, `AuditEvent`, chat wiring, and sidecar wiring are real harness behavior. The assistant
explains evidence; it does not route, authorize, or execute production remediation.

## What is novel

The right-side execution path grounds infrastructure remediation in two standardized contracts at
once: the O-RAN O2 IMS interface ([ref 2](docs/references.md#ref-2),
[ref 3](docs/references.md#ref-3)) above, and the CRD-shaped delivery contracts inside the O-Cloud
(Metal3 BareMetalHost / HostFirmwareComponents at [ref 8](docs/references.md#ref-8); Machine Config
Operator at [ref 9](docs/references.md#ref-9)) below. The 2+3+8+9 conjunction is what lets a single
RemediationProposal travel from the cognitive layer, through a standardized O-RAN interface, into
a concrete Kubernetes-native contract that already runs in production O-Cloud deployments. Most
prior agentic-RAN work either stops at the SMO boundary without a delivery story, or proposes a
custom controller plane that side-steps O-RAN's own resource layering. Layered on top, the
Remediation Router classifies first by deterministic taxonomy lookup against the O-RAN WG6
O-Cloud resource model and invokes LLM reasoning only on the residual `ambiguous` class. Full
walkthrough at `talk/architecture_narrative.md`.

## Quick start

```bash
cd macbook_lab && ./run.sh
# then open http://localhost:8097 in a browser
```

Requires Docker Desktop on a Mac. No other dependencies for the deterministic bench.
For the dashboard chat service, copy `macbook_lab/anthropic.env.example` to
`macbook_lab/anthropic.env` and set `ANTHROPIC_API_KEY`. The Router's live LLM seam can use
Anthropic, the OpenAI API, or an OpenAI-compatible on-prem vLLM endpoint such as Red Hat
OpenShift AI.

Three goals for this repository, in the author's words:

1. **Here is my presentation to the O-RAN community.** The submission abstract, the architecture
   diagram, the closing trust-loop content, and the ODA Canvas reference mapping all live under `talk/`.
2. **Here is the example work, you can go take a look at it.** The harness pattern's contracts (taxonomy,
   guardrails, schemas, routing rules, MCP tool surfaces, upstream pointers) live under `harness/`.
   Every authored file carries a citation header tying it to an O-RAN, ETSI, IEEE, 3GPP, or TM Forum
   section. The central index is `harness/conformance.md`.
3. **Here is where I actually test the use case.** Five walkthrough scenarios under `scenarios/`
   exercise the harness against host-platform PTP faults (A, A-prime, D, E, and the dual-route
   rejection variant E_with_smo_reject). A research bench at `5G_O-RAN_SIM/bench/` runs them
   all end to end with platform stubs firing and trace files accumulating. A static HTML trace
   viewer at `5G_O-RAN_SIM/dashboard/trace_view/` shows the per-scenario timelines side by
   side. Two OMC skill bundles complement the harness: the action-oriented bundle at
   `omc-skills/o-ran/` (troubleshoot, remediate, sandbox-validation, plan) and the
   discovery-oriented bundle at `omc-skills/oran-discover/` (`:ptp`, `:metal3`, `:redfish`,
   `:smo`, `:taxonomy`, `:guardrail`, `:plan` for pre-flight survey).

## What this repository is

A citation-grounded declarative artifact set (harness pattern) with a runnable platform substrate
(`5G_O-RAN_SIM/`) underneath. The harness pattern itself stays declarative (taxonomy, guardrails,
schemas, routing rules, MCP tool surfaces); the platform substrate provides 13 O-RAN service
implementations across WG1 to WG11, stub publishers for PTP alarms / Metal3 firmware / Redfish BMC
/ TMF921 SMO companion intents, and a unified LLM inference client routable across Anthropic, the
OpenAI API, and OpenAI-compatible on-prem vLLM endpoints such as Red Hat OpenShift AI. The
architectural pattern is operationalization-agnostic; the
contracts are portable to LangGraph, OpenAI Agents SDK, Microsoft Semantic Kernel, or any agent
framework that can read JSON Schema and YAML.

The reference O2 IMS implementation cited throughout is Red Hat's open-source O-Cloud Manager
(openshift-kni/oran-o2ims, bibliography ref 6 in `docs/references.md`).

## How the system works (one paragraph)

An observation loop on the edge (Intel NIC PHC, the linuxptp daemon, and cloud-event-proxy publishing
O-RAN CloudEvents) captures PTP drift evidence. The agent harness in the middle (an Agentic Gateway
over MCP, three domain agents for Platform, RAN, and Hardware, and a deterministic taxonomy with
LLM-assist on ambiguous edges) classifies the fault. A routing rule then splits actions by O-RAN
resource layer: service-layer fixes route UP to the partner SMO as a TMF921 intent (with the SMO's
acceptance or rejection captured as a `dispatch_result` field on the AuditEvent); infrastructure
fixes route DOWN to the O-Cloud via the O-RAN O2 IMS API, where the Machine Config Operator or the
Kernel Module Management Operator delivers the artifact. Before any live action, the proposal runs
through a Sandbox stage (`harness/runtime/walker.py sandbox_simulation()`) against a digital-twin
verdict; the Guardrail engine blocks the apply if `sandbox_verdict.apply_allowed` is False. Only
sandbox-passing proposals reach the human operator with a populated reversibility profile, and
the operator sees both the Sandbox verdict and the SMO dispatch_result before signing. Full
walkthrough at `talk/architecture_narrative.md`.

## Repository map

```
oran-agent-harness/
|-- README.md            this file
|-- LICENSE              Apache-2.0
|-- CONTRIBUTING.md      four extensible surfaces, hard rules, citation discipline
|-- pyproject.toml       packaging metadata, pip install -e . enables module imports
|-- Makefile             canonical entry points: make install / verify / demo
|-- .editorconfig        UTF-8, LF, indent rules per file type
|-- .gitignore           defense-in-depth against .local/, python_demo/, .pdf, .env
|-- .github/
|   |-- workflows/
|   |   `-- verify.yml             CI runs the 10-check verify gate on push and PR
|   |-- ISSUE_TEMPLATE/
|   |   `-- new-scenario.md        structured fields for a new walkthrough scenario
|   `-- PULL_REQUEST_TEMPLATE.md   verify-gate checklist for every PR
|-- docs/
|   `-- references.md    public bibliography, 52 numbered AMA refs, URLs only, HTML id anchors
|-- talk/                presentation artifacts
|   |-- abstract.md             canonical nGRG submission
|   |-- architecture.mmd        macro / billboard, 7 boxes, the mental map (the entry point)
|   |-- architecture.png        rendered macro diagram
|   |-- architecture_full.mmd   comprehensive 30+ component detail reference (former v3)
|   |-- architecture_full.png   12K-wide rendered detail diagram
|   |-- architecture_narrative.md   prose walkthrough of the diagrams
|   |-- architecture_zoom_governance.mmd  zoom diagram: TM Forum, audit, Killswitch
|   |-- architecture_zoom_cognitive.mmd   zoom diagram: Gateway, agents, Digital Twin substrate
|   |-- architecture_zoom_ocloud.mmd      zoom diagram: O-Cloud, spoke operators, worker
|   |-- sequence_anomaly_lifecycle.mmd    behavioral: anomaly to apply, temporal flow
|   |-- sequence_agentic_recovery.mmd     behavioral: rollback sequence, per-action undo
|   |-- state_crisis_mode.mmd             behavioral: Killswitch state transitions
|   |-- trust_loop.md           Digital Twin substrate, EvalOps, Sandbox, Agentic Recoverability, IA
|   |-- killswitch.md           crisis_mode global override, AT&T-reviewed
|   |-- oda_mapping.md          15-element ODA Canvas reference mapping
|   `-- slides.md               slide-deck pointer (deck out of scope here)
|-- harness/             20 authored stub artifacts (the contract set)
|   |-- taxonomy.yaml    20 entries grounded in O-RAN WG6 resource model
|   |-- guardrails.yaml  LLM-free policy contract, TMF688-shaped audit
|   |-- conformance.md   central citation index
|   |-- schemas/         5 JSON Schemas, draft-07
|   |-- routing-rules/   3 YAMLs, one per talk contribution
|   |-- mcp-tool-schemas/ 4 FastMCP tool surfaces
|   `-- references/      5 upstream contract pointers, commit-SHA pinnable
|-- scenarios/           5 PTP host-platform walkthroughs
|   |-- README.md             walkthrough narrative, what is stubbed vs real
|   |-- A_fw_lldp_agent/      fw-lldp-agent service interferes with PTP (5 fixtures)
|   |-- A_prime_ice_driver/   ice driver 1.11.x causes PHC drift (5 fixtures)
|   |-- D_phc_drift_hw_only/  software-LOCKED vs hardware-NOT-OK divergence (5 fixtures)
|   |-- E_nic_firmware_update/ NIC firmware update via Metal3 + TMF921 companion intent (6 fixtures)
|   `-- E_with_smo_reject/    Same firmware push, SMO rejects companion intent (6 fixtures)
|-- harness/runtime/     deterministic Python runtime (stubs + real Router + real Guardrail)
|   |-- router.py             real deterministic Router (taxonomy lookup)
|   |-- guardrail.py          real deterministic Guardrail engine (audit emission)
|   `-- walker.py             orchestrator with CLI entry point
|-- omc-skills/          reference operationalization (OMC)
|   `-- o-ran/                4 skills + README + conformance index
|-- scripts/             executable verify gate and demo runner
|   |-- verify.py             10 deterministic checks, exits non-zero on any failure
|   `-- demo.sh               walks all scenarios end to end with --verbose
|-- tests/               runtime unit tests for the harness Router and Guardrail
|   |-- __init__.py
|   `-- test_runtime.py       9 tests covering service / ambiguous / unknown layer / empty / crisis_mode / LLM-mode / sandbox-block / dispatch-result branches
`-- 5G_O-RAN_SIM/        platform substrate (BF3-5G-Demo, Apache 2.0 re-licensed by the author)
    |-- open-digital-platform-2_0/   13 O-RAN service implementations across WG1-WG11
    |-- demo_front-end/              React dashboard
    |-- docs/                        O-RAN architecture and compliance docs
    |-- oam/                         platform stubs the harness consumes
    |   |-- ptp_operator_stub.py        emits CloudEvents matching O-RAN WG6 Cloud Notification API
    |   |-- metal3_bmo_stub.py          firmware push phases (Preparing/Pushing/Rebooting/Verifying/Updated)
    |   `-- redfish_bmc_stub.py         DMTF Redfish SimpleUpdate task lifecycle
    |-- smo/
    |   `-- tmf921_intent_emitter.py    TMF921 SMO companion intent envelope builder
    |-- llm/                         LLM inference layer (Issue #48)
    |   |-- inference_client.py         unified completion() across Anthropic / OpenAI / vLLM
    |   `-- .env.example                template, copy to .env to configure providers
    |-- shared_trace/                file-based JSONL trace layer for cross-stage replay
    |   |-- writer.py                   append_trace(scenario_id, stage, payload)
    |   |-- viewer.py                   CLI timeline reader
    |   `-- E_nic_firmware_update.example.jsonl   committed dual-route example trace
    |-- bench/                       research bench runner
    |   |-- runner.py                   orchestrates all 5 scenarios end to end
    |   `-- summary.py                  comparative markdown table
    `-- dashboard/trace_view/        static HTML trace viewer (vanilla JS, no build step)
        |-- index.html                  4-up compare + per-scenario zoom
        `-- serve.py                    python http.server on port 8095
```

## Citation discipline

Every authored YAML opens with `# Conforms to:` and `# Bibliography ref:` headers. Every authored JSON
carries a top-level `_conforms_to` key. The central index `harness/conformance.md` maps every file to its
upstream spec, section, version, and bibliography reference number. A file in `harness/` or `scenarios/`
that lacks a citation header is incomplete metadata; a row in the index that points to a non-existent
file is stale documentation. The verify gate runs the cross-check in both directions before publication.

Run the gate locally with:

```
pip install pyyaml jsonschema
python3 scripts/verify.py
```

It runs 10 deterministic checks (citation headers, JSON parse, YAML parse, conformance.md
bidirectional completeness, em dash audit, leakage guard, README structure, file counts, schema
validation of scenario data against the declared harness schemas, and end-to-end walker output
matching committed audit_event.json on material fields) and exits non-zero on any failure. Check 9
(schema validation) is optional and skipped with a warning if `jsonschema` is not installed.
Check 10 (walker end to end) requires PyYAML and runs the walker as a subprocess. See the script
header for the full list.

### Replicating the test locally

The complete reproducible test sequence from a fresh clone:

```bash
git clone https://github.com/dkypuros/oran-agent-harness.git
cd oran-agent-harness
pip install pyyaml jsonschema       # PyYAML for parse + runtime, jsonschema for check 9

# Walk all scenarios end to end (real Router + Guardrail, stubbed Gateway/MCP/Agents/Twin)
./scripts/demo.sh

# Full verify gate (10 checks)
python3 scripts/verify.py
```

Expected output of `python3 scripts/verify.py`:

```
SUMMARY: 10/10 checks passed
OVERALL: PASS
```

Expected output of `./scripts/demo.sh` (truncated): each scenario prints four pipeline stages
(FaultPayload, RCA, RemediationProposal, AuditEvent) and the final AuditEvent shows
`targetLayer: infra`, `dryRun: true`, `requiresHumanApproval: true`, and a populated
`reversibility_profile` with the expected `confidence_in_reversibility` value (`high` for Scenario
A, `medium` for A-prime, `medium` for D, `medium` for E). Scenario E additionally carries a
`companion_intent` (TMF921 envelope) in the remediation block reflecting the dual-route case.

The verify gate's walker_e2e check enforces matching output for all 5 committed scenarios.

See `scenarios/README.md` for the walkthrough narrative and the table of what is stubbed vs real.

## Running the walkthroughs

There are two ways to walk a scenario end to end.

### Deterministic Python runtime (recommended for demos)

Real Router and Guardrail engine. Stubbed Gateway, MCP servers, Domain Agents, and Digital Twin.
Output is fully reproducible across runs. Verify gate check 10 enforces match against the committed
audit_event.json on material fields.

```
./scripts/demo.sh
```

Or a single scenario (A, A_prime, D, or E):

```
python3 -m harness.runtime.walker scenarios/A_fw_lldp_agent/fault_payload.json --verbose
python3 -m harness.runtime.walker scenarios/E_nic_firmware_update/fault_payload.json --verbose
```

See `scenarios/README.md` for the walkthrough narrative, what is stubbed vs real, and how to swap a
stub for a real component when moving to a bigger environment.

### Research bench and trace viewer

The research bench at `5G_O-RAN_SIM/bench/` runs all 5 scenarios end to end (A_fw_lldp_agent,
A_prime_ice_driver, D_phc_drift_hw_only, E_nic_firmware_update, E_with_smo_reject), firing the
platform stubs (PTP operator publisher, Metal3 BMO, Redfish BMC, TMF921 SMO emitter for the two
Scenario E variants) and capturing per-stage records to JSONL files at
`5G_O-RAN_SIM/shared_trace/`.

```bash
# Run the bench (produces shared_trace/*.jsonl + bench/last_run_summary.md)
python 5G_O-RAN_SIM/bench/runner.py all

# Or a single scenario
python 5G_O-RAN_SIM/bench/runner.py E_nic_firmware_update
```

The static HTML trace viewer renders the resulting JSONL files as color-coded timelines with a
4-up comparison view:

```bash
python 5G_O-RAN_SIM/dashboard/trace_view/serve.py
# open http://localhost:8095/dashboard/trace_view/index.html
```

### LLM substrate (Contribution 3 realized live)

The harness Router's `ambiguous_path` is wired through a unified LLM inference client at
`5G_O-RAN_SIM/llm/inference_client.py`. By default the seam is dormant (`ORAN_LLM_MODE` unset, the
existing `NotImplementedError` raises so the verify gate stays clean). When `ORAN_LLM_MODE=live`,
the router routes through Anthropic, the OpenAI API, or an OpenAI-compatible vLLM endpoint per the configured
`LLM_PROVIDER` env var:

```bash
# Copy the template and configure provider keys
cd 5G_O-RAN_SIM && cp .env.example .env
# Choose LLM_PROVIDER=anthropic, openai, or vllm.
# For vLLM, set VLLM_BASE_URL to your OpenShift AI route.

# Drive the harness with the LLM seam live
ORAN_LLM_MODE=live python3 -m harness.runtime.walker scenarios/A_fw_lldp_agent/fault_payload.json
```

Provider-safety: if the selected provider is not configured, the client returns a clear
unavailable message instead of synthesizing a model answer. The v0 router records the
hint but does not auto-apply it.

### OMC reference operationalization (Claude Code skills)

Prose-driven invocation via the OMC skill bundle. LLM provider in the loop, behavioral
reproducibility bounded by provider determinism settings.

```
# Scenario A, fw-lldp-agent host service interfering with PTP
/o-ran:plan scenarios/A_fw_lldp_agent/fault_payload.json

# Scenario A-prime, outdated ice driver causing PHC drift
/o-ran:plan scenarios/A_prime_ice_driver/fault_payload.json
```

See `omc-skills/o-ran/README.md` (action-oriented) and `omc-skills/oran-discover/README.md`
(read-only platform survey) for installation and the per-skill input / output contracts.
Discovery walks: `/oran-discover:plan` invokes the seven-step pre-flight; individual surfaces are
reachable via `/oran-discover:ptp`, `/oran-discover:metal3`, `/oran-discover:redfish`,
`/oran-discover:smo`, `/oran-discover:taxonomy`, `/oran-discover:guardrail`.
Those slash commands are inspection surfaces. The separate `harness-walker /run/<scenario>`
sidecar attaches the live `AuditEvent` evidence used by the right-loop demo, including the
`D_phc_drift_hw_only`, `E_nic_firmware_update`, and `E_with_smo_reject` branches.

Each end-to-end run reads a FaultPayload, walks the evidence chain across three domain agents (Platform,
RAN, Hardware), picks a routing direction via the deterministic taxonomy lookup (with LLM-assist on
ambiguous edges only), evaluates against the guardrail engine, and emits a TMF688 AuditEvent with a
populated ReversibilityProfile.

## Three contributions exercised end-to-end

| Contribution                            | Declarative form                                            | Reference operationalization                |
|------------------------------------------|--------------------------------------------------------------|----------------------------------------------|
| Remediation routing rule                 | harness/routing-rules/contribution-1-routing-rule.yaml      | omc-skills/o-ran/remediate.md                |
| Guardrail contract layer                 | harness/routing-rules/contribution-2-guardrail-contract.yaml plus harness/guardrails.yaml | omc-skills/o-ran/sandbox-validation.md       |
| LLM-neutral substrate                    | harness/routing-rules/contribution-3-llm-neutrality.yaml    | 5G_O-RAN_SIM/llm/inference_client.py routing across Anthropic / OpenAI / on-prem vLLM |

## License

Apache-2.0. See `LICENSE`.

## Acknowledgements

The diagnostic substrate this work builds on (MCP-coordinated multivendor domain agents) is the published
output of a joint Ericsson, Red Hat, and Intel effort. See bibliography ref 35 in `docs/references.md`. The
closed-loop remediation extension presented here is solo work by the author for the nGRG workshop.
