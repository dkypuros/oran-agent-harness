# LangGraph Taxonomy Runner

Status: optional runtime target for the taxonomy harness.

`harness/taxonomy.yaml` remains the canonical taxonomy. The LangGraph upgrade is intentionally thin:
`harness/runtime/taxonomy_graph.py` wraps the existing deterministic router, sandbox, and guardrail
stages as named graph nodes. If `langgraph` is installed, the runner compiles a LangGraph state graph.
If it is not installed, the same node contract runs through a dependency-free fallback graph so demos
and CI stay stable.

## Node contract

| Node | Responsibility |
|---|---|
| `load_taxonomy` | Load and flatten `harness/taxonomy.yaml` into graph state. |
| `classify_fault` | Read the top RCA candidate and attach taxonomy metadata. |
| `ambiguity_assist_boundary` | Stop ambiguous classifications at the LLM-assist boundary unless live ambiguous handling is explicitly enabled. |
| `route_decision` | Call the existing deterministic `router.route()` implementation. |
| `sandbox_gate` | Attach the existing digital-twin sandbox verdict before guardrails. |
| `guardrail_human_approval_gate` | Call `guardrail.evaluate()` and emit the TMF688-shaped audit event with pending human approval. |

## Why this is the right upgrade path

The taxonomy is not replaced by LangGraph. LangGraph is the orchestration runtime target: persistence,
checkpointing, interrupts, human-in-the-loop approval, streaming, and debug visibility can be added
around the deterministic taxonomy contract without moving classification rules into prompts.

This keeps the core thesis intact:

1. deterministic taxonomy lookup first;
2. LLM-assist only on ambiguous edges;
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

Install the optional LangGraph runtime with:

```bash
pip install -e '.[langgraph]'
```

The default test path does not require LangGraph:

```bash
python3 -m pytest tests/test_taxonomy_graph.py
python3 scripts/verify.py
```

## Relationship to Telco Systems Integration Lab

`Telco_Systems_Integration_Lab` remains background research material for standards grounding, including
the recent action-boundary and perception-boundary work. This repository is the target runtime for the
taxonomy-driven harness.
