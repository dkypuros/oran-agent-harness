# Shared trace layer

File-based JSON persistence for cross-stage replay analysis. Every pipeline
stage (PTP operator, gateway, MCP server, domain agent, router, guardrail,
Metal3 BMO, Redfish BMC, SMO intent emitter, audit emitter) calls
`append_trace()` to record what it did. The result is a per-scenario timeline
that the talk can replay offline.

## Why JSON files, not a database

This is replay and diagnostic data, not transactional state. A database adds
operational complexity (deploy, schema migrations, connection management,
backup, restore) for zero benefit at the demo and post-talk-analysis scale.
JSONL is grep-able, diff-able, version-controllable for committed examples,
and the python stdlib reads it in one line.

## File layout

```
shared_trace/
├── README.md                                  this file
├── {scenario_id}.jsonl                        runtime traces (gitignored)
└── {scenario_id}.example.jsonl                committed example traces (checked in)
```

The runtime files (no suffix variant) accumulate as the harness runs. They are
gitignored at the repo root so each developer's local runs do not collide.
Committed example traces use the `.example.jsonl` suffix; those are demo
artifacts that show what the trace looks like for a given scenario.

## Record shape

Each line is a single JSON object:

```json
{"ts": "2026-05-30T11:00:00.123456+00:00",
 "scenario_id": "D_phc_drift_hw_only",
 "stage": "ptp_operator",
 "ptp4l_state": "SYNCHRONIZED",
 "tx_hwtstamp_timeouts": 1241,
 "verdict": "anomaly"}
```

Required fields: `ts`, `scenario_id`, `stage`. Everything else is stage-specific
payload. The writer adds `ts` and `scenario_id` automatically; callers pass
`stage` and the rest of the dict.

## Usage

```python
from shared_trace import append_trace

append_trace(
    scenario_id="D_phc_drift_hw_only",
    stage="ptp_operator",
    payload={"ptp4l_state": "SYNCHRONIZED", "verdict": "software_ok"},
)
```

To view a trace:

```bash
python -m shared_trace.viewer D_phc_drift_hw_only
python -m shared_trace.viewer D_phc_drift_hw_only --json
python -m shared_trace.viewer E_nic_firmware_update --example   # committed example
```

## Honest scope

Best-effort append. The writer swallows filesystem errors so the demo path
stays clean even when the trace volume is unwritable. The trace is for
diagnostic analysis, not for guarantees about completeness. If you need
durable persistence later, swap `writer.py` for a real backend; the
`append_trace()` signature stays the same.
