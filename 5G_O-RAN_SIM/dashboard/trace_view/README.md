# Trace timeline viewer

Static HTML dashboard that reads the per-scenario JSONL traces produced by the bench
(`5G_O-RAN_SIM/bench/runner.py`) and renders them as color-coded timelines, with a 4-up
comparison view and per-scenario zoom.

## Quick start

```bash
cd /path/to/oran-agent-harness
# Step 1: run the bench to produce the JSONL trace files
python 5G_O-RAN_SIM/bench/runner.py all
# Step 2: serve the dashboard
python 5G_O-RAN_SIM/dashboard/trace_view/serve.py
# Step 3: open in browser
open http://localhost:8095/dashboard/trace_view/index.html
```

The server's port can be overridden with `TRACE_VIEWER_PORT=9000`.

## What the dashboard shows

- **4-up compare** (default): all 4 scenarios side by side in a grid. Each column is
  one scenario's timeline. Useful for talking through the harness arc and showing how
  the routing rule produces different action types for different fault classes.
- **Per-scenario zoom**: A only, A-prime only, D only, E only. Single column view for
  deep dives on one scenario's pipeline.
- **Reload traces**: re-fetches the JSONL files from disk. Useful after re-running the
  bench.

## Stage color coding

Pipeline stages are color-coded so the timeline reads at a glance:

| Color | Stage |
|---|---|
| Blue | ptp_operator (PTP alarm publish) |
| Green | gateway (CloudEvent ingestion) |
| Light blue | mcp_platform / mcp_ran / mcp_hardware / mcp_ocloud (MCP servers) |
| Purple | domain_agent_platform / domain_agent_ran / domain_agent_hardware (Domain Agents) |
| Orange | router (taxonomy lookup, routing rule, dual-route attach) |
| Red | smo_intent (TMF921 companion intent) |
| Yellow | guardrail (rule evaluation, blast radius check) |
| Brown | metal3_bmo (firmware push phases) |
| Gray | redfish_bmc (Redfish task lifecycle) |
| Black | audit (TMF688 emission) |

## Implementation notes

- Single static HTML file, no build step, no node_modules, no external CDN
- Vanilla JS uses `fetch()` against the relative path `../shared_trace/{scenario}.jsonl`
- The server is a python `http.server.SimpleHTTPRequestHandler` rooted at `5G_O-RAN_SIM/`
  so the dashboard and the trace files share an origin
- Port 8095 by default; configurable via `TRACE_VIEWER_PORT`

## Honest scope

This is a read-only static viewer. It does not write to traces, does not control the
bench, does not orchestrate anything. Run the bench first, refresh the page to see
fresh data. For post-talk analysis the JSONL files can also be piped through `jq` or
loaded into any other tooling.
