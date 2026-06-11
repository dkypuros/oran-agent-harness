# LangGraph Taxonomy Runner

Status: optional orchestration target for the taxonomy harness.

`harness/taxonomy.yaml` remains the canonical taxonomy. The LangGraph upgrade is intentionally thin:
`harness/runtime/taxonomy_graph.py` wraps the existing deterministic router, sandbox, and guardrail
stages as named graph nodes. If `langgraph` is installed, the runner compiles a LangGraph state graph.
If it is not installed, the same node contract runs through a dependency-free fallback graph so demos
and CI stay stable.

## Node contract

| Node | Responsibility |
|---|---|
| `load_taxonomy` | Load and flatten `harness/taxonomy.yaml` into graph state. |
| `classify_fault` | Validate the top RCA candidate against taxonomy.yaml, attach taxonomy metadata, and replace any missing layer with the canonical taxonomy layer. |
| `ambiguity_assist_boundary` | Stop ambiguous classifications for human review. Optional LLM-assist text is stored only as review context and is not parsed into an automated route in v0. |
| `route_decision` | Call the existing deterministic `router.route()` implementation only after taxonomy authorization. |
| `sandbox_gate` | Attach the existing digital-twin sandbox verdict before guardrails. |
| `guardrail_human_approval_gate` | Call `guardrail.evaluate()` and emit the TMF688-shaped audit event with pending human approval. |

## Boundary guarantees

The graph does not let RCA producers override the taxonomy boundary:

- unknown `taxonomy_match` values are rejected before routing;
- a supplied `target_layer` must match the layer in `taxonomy.yaml`;
- ambiguous taxonomy entries remain blocked for review even when the LLM-assist seam returns a hint;
- only non-ambiguous, taxonomy-authorized candidates can reach `router.route()`.

This is the important LangGraph seam for continue/demo purposes: graph state makes each decision point
visible without moving classification authority into prompts.

## What LangGraph adds now vs. later

Implemented now: a LangGraph-compatible state graph with a deterministic fallback runner and matching
node traces for the supported path.

Not implemented yet: durable checkpoint persistence, `thread_id`/config-driven continue, LangGraph
interrupts, or production human-in-the-loop approval queues. Those are the next runtime layer to add
around this graph; this patch only establishes the safe node contract.

## Why this is the right upgrade path

The taxonomy is not replaced by LangGraph. LangGraph is the orchestration runtime target: persistence,
checkpointing, interrupts, human-in-the-loop approval, streaming, and debug visibility can be added
around the deterministic taxonomy contract without moving classification rules into prompts.

This keeps the core thesis intact:

1. deterministic taxonomy lookup first;
2. LLM-assist only as review context on ambiguous edges;
3. sandbox before apply;
4. guardrails before human approval;
5. no autonomous production mutation from the model.

## Usage

```python
from harness.runtime.taxonomy_graph import TaxonomyGraphRunner

runner = TaxonomyGraphRunner()
result = runner.walk_fault_payload("scenarios/A_fw_lldp_agent/fault_payload.json")
print(result.backend)      # "langgraph" when installed, otherwise "fallback"
print(result.node_trace)   # explicit graph stages
print(result.audit_event)  # final TMF688-shaped audit event
```

Install the optional LangGraph runtime with Python 3.10+:

```bash
pip install -e '.[langgraph]'
```

The default test path does not require LangGraph and remains compatible with the repository baseline:

```bash
python3 -m pytest tests/test_taxonomy_graph.py
python3 scripts/verify.py
```

## Relationship to Telco Systems Integration Lab

`Telco_Systems_Integration_Lab` remains background research material for standards grounding, including
the recent action-boundary and perception-boundary work. This repository is the target runtime for the
taxonomy-driven harness.
