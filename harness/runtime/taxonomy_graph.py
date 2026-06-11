"""LangGraph-compatible taxonomy orchestration runner.

The taxonomy YAML remains the source of truth.  This module adds a thin graph
runtime around the existing deterministic router/guardrail path so the harness
can be run as explicit orchestration stages today and can compile to LangGraph
when the optional dependency is installed.

The fallback runner is intentionally dependency-free and uses the same node
names as the LangGraph path.  That keeps CI and laptop demos stable while making
LangGraph a future production target for durable execution, checkpoints,
interrupts, and human-in-the-loop control.  Those durable runtime concerns are
not implemented by this thin runner yet.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Mapping, TypedDict

import yaml

from harness.runtime import guardrail, router, walker

_RUNTIME_DIR = Path(__file__).resolve().parent
_HARNESS_DIR = _RUNTIME_DIR.parent
_TAXONOMY_PATH = _HARNESS_DIR / "taxonomy.yaml"

NODE_LOAD_TAXONOMY = "load_taxonomy"
NODE_CLASSIFY = "classify_fault"
NODE_AMBIGUITY = "ambiguity_assist_boundary"
NODE_ROUTE = "route_decision"
NODE_SANDBOX = "sandbox_gate"
NODE_GUARDRAIL = "guardrail_human_approval_gate"
GRAPH_NODE_SEQUENCE: tuple[str, ...] = (
    NODE_LOAD_TAXONOMY,
    NODE_CLASSIFY,
    NODE_AMBIGUITY,
    NODE_ROUTE,
    NODE_SANDBOX,
    NODE_GUARDRAIL,
)


class TaxonomyGraphState(TypedDict, total=False):
    """Serializable state carried across graph nodes."""

    fault_payload: dict[str, Any]
    rca: dict[str, Any]
    taxonomy: dict[str, dict[str, Any]]
    classification: dict[str, Any]
    ambiguity_required: bool
    ambiguity_status: str
    ambiguity_hint: str
    proposal: dict[str, Any]
    audit_event: dict[str, Any]
    node_trace: list[str]
    backend: str
    status: str


@dataclass(frozen=True)
class TaxonomyGraphResult:
    """Result returned by the taxonomy graph runner."""

    state: TaxonomyGraphState
    backend: str
    node_trace: tuple[str, ...]

    @property
    def audit_event(self) -> dict[str, Any] | None:
        return self.state.get("audit_event")

    @property
    def proposal(self) -> dict[str, Any] | None:
        return self.state.get("proposal")


@dataclass
class _FallbackGraph:
    """Small sequential graph with a LangGraph-like invoke surface."""

    nodes: Mapping[str, Callable[[TaxonomyGraphState], Mapping[str, Any]]]

    def invoke(self, initial_state: Mapping[str, Any]) -> TaxonomyGraphState:
        state: TaxonomyGraphState = dict(initial_state)  # type: ignore[assignment]
        state.setdefault("node_trace", [])

        for node_name in (NODE_LOAD_TAXONOMY, NODE_CLASSIFY):
            state.update(self.nodes[node_name](state))

        if state.get("ambiguity_required"):
            state.update(self.nodes[NODE_AMBIGUITY](state))
            if state.get("status") == "blocked_ambiguous":
                return state

        for node_name in (NODE_ROUTE, NODE_SANDBOX, NODE_GUARDRAIL):
            state.update(self.nodes[node_name](state))
        return state


@dataclass
class TaxonomyGraphRunner:
    """Run the harness taxonomy as explicit graph stages."""

    taxonomy_path: Path = _TAXONOMY_PATH
    prefer_langgraph: bool = True
    ambiguity_resolver: Callable[[dict[str, Any]], str] | None = None
    _compiled_graph: Any | None = field(default=None, init=False, repr=False)
    _backend: str | None = field(default=None, init=False, repr=False)

    @property
    def backend(self) -> str:
        self._ensure_graph()
        return self._backend or "fallback"

    def invoke(self, rca: Mapping[str, Any]) -> TaxonomyGraphResult:
        """Invoke the graph from an RCA object."""

        graph = self._ensure_graph()
        state = graph.invoke({"rca": dict(rca), "backend": self.backend})
        trace = tuple(state.get("node_trace", ()))
        return TaxonomyGraphResult(state=state, backend=self.backend, node_trace=trace)

    def walk_fault_payload(self, fault_payload_path: str | Path) -> TaxonomyGraphResult:
        """Load a FaultPayload, build RCA with existing agents stub, then run graph."""

        payload = json.loads(Path(fault_payload_path).read_text())
        payload_no_meta = {key: value for key, value in payload.items() if key != "_conforms_to"}
        rca = walker.stubbed_agents(payload_no_meta)
        graph = self._ensure_graph()
        state = graph.invoke(
            {"fault_payload": payload_no_meta, "rca": rca, "backend": self.backend}
        )
        trace = tuple(state.get("node_trace", ()))
        return TaxonomyGraphResult(state=state, backend=self.backend, node_trace=trace)

    def _ensure_graph(self) -> Any:
        if self._compiled_graph is not None:
            return self._compiled_graph
        nodes = self._nodes()
        if self.prefer_langgraph:
            compiled = self._try_compile_langgraph(nodes)
            if compiled is not None:
                self._compiled_graph = compiled
                self._backend = "langgraph"
                return compiled
        self._compiled_graph = _FallbackGraph(nodes=nodes)
        self._backend = "fallback"
        return self._compiled_graph

    def _try_compile_langgraph(
        self,
        nodes: Mapping[str, Callable[[TaxonomyGraphState], Mapping[str, Any]]],
    ) -> Any | None:
        try:
            from langgraph.graph import END, START, StateGraph
        except Exception:
            return None

        graph = StateGraph(TaxonomyGraphState)
        for node_name, node in nodes.items():
            graph.add_node(node_name, node)
        graph.add_edge(START, NODE_LOAD_TAXONOMY)
        graph.add_edge(NODE_LOAD_TAXONOMY, NODE_CLASSIFY)
        graph.add_conditional_edges(
            NODE_CLASSIFY,
            _next_after_classify,
            {
                NODE_AMBIGUITY: NODE_AMBIGUITY,
                NODE_ROUTE: NODE_ROUTE,
            },
        )
        graph.add_conditional_edges(
            NODE_AMBIGUITY,
            _next_after_ambiguity,
            {
                NODE_ROUTE: NODE_ROUTE,
                END: END,
            },
        )
        graph.add_edge(NODE_ROUTE, NODE_SANDBOX)
        graph.add_edge(NODE_SANDBOX, NODE_GUARDRAIL)
        graph.add_edge(NODE_GUARDRAIL, END)
        return graph.compile()

    def _nodes(self) -> dict[str, Callable[[TaxonomyGraphState], Mapping[str, Any]]]:
        return {
            NODE_LOAD_TAXONOMY: self._load_taxonomy_node,
            NODE_CLASSIFY: self._classify_node,
            NODE_AMBIGUITY: self._ambiguity_node,
            NODE_ROUTE: self._route_node,
            NODE_SANDBOX: self._sandbox_node,
            NODE_GUARDRAIL: self._guardrail_node,
        }

    def _load_taxonomy_node(self, state: TaxonomyGraphState) -> Mapping[str, Any]:
        taxonomy = load_taxonomy(self.taxonomy_path)
        return _with_trace(state, NODE_LOAD_TAXONOMY, {"taxonomy": taxonomy})

    def _classify_node(self, state: TaxonomyGraphState) -> Mapping[str, Any]:
        rca = normalize_rca_with_taxonomy(state["rca"], state.get("taxonomy", {}))
        classification = dict(rca["candidate_classifications"][0])
        ambiguity_required = classification["target_layer"] == "ambiguous"
        return _with_trace(
            state,
            NODE_CLASSIFY,
            {
                "rca": rca,
                "classification": classification,
                "ambiguity_required": ambiguity_required,
            },
        )

    def _ambiguity_node(self, state: TaxonomyGraphState) -> Mapping[str, Any]:
        if not state.get("ambiguity_required"):
            return _with_trace(state, NODE_AMBIGUITY, {"ambiguity_status": "not_required"})

        resolver = self.ambiguity_resolver or resolve_ambiguity_for_review
        try:
            hint = resolver(state["rca"])
        except NotImplementedError as exc:
            hint = str(exc)
        return _with_trace(
            state,
            NODE_AMBIGUITY,
            {
                "ambiguity_status": "blocked_for_human_review",
                "ambiguity_hint": hint,
                "status": "blocked_ambiguous",
            },
        )

    def _route_node(self, state: TaxonomyGraphState) -> Mapping[str, Any]:
        proposal = router.route(state["rca"])
        return _with_trace(state, NODE_ROUTE, {"proposal": proposal})

    def _sandbox_node(self, state: TaxonomyGraphState) -> Mapping[str, Any]:
        proposal = dict(state["proposal"])
        fault_id = str(state["rca"]["fault_id"])
        proposal = walker.sandbox_simulation(proposal, fault_id=fault_id)
        return _with_trace(state, NODE_SANDBOX, {"proposal": proposal})

    def _guardrail_node(self, state: TaxonomyGraphState) -> Mapping[str, Any]:
        fault_id = str(state["rca"]["fault_id"])
        audit_event = guardrail.evaluate(state["proposal"], fault_id=fault_id)
        return _with_trace(
            state,
            NODE_GUARDRAIL,
            {"audit_event": audit_event, "status": "complete"},
        )


def load_taxonomy(path: str | Path = _TAXONOMY_PATH) -> dict[str, dict[str, Any]]:
    """Flatten taxonomy.yaml into id -> entry for graph-state lookup."""

    payload = yaml.safe_load(Path(path).read_text())
    taxonomy: dict[str, dict[str, Any]] = {}
    for section_name, entries in payload.get("resource_taxonomy", {}).items():
        for entry in entries or []:
            item = dict(entry)
            item["section"] = section_name
            taxonomy[str(item["id"])] = item
    return taxonomy


def normalize_rca_with_taxonomy(
    rca: Mapping[str, Any],
    taxonomy: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    """Return an RCA whose top candidate is authorized by taxonomy.yaml.

    The graph deliberately treats ``taxonomy.yaml`` as the source of truth.  RCA
    producers may suggest a taxonomy ID, but they may not override the canonical
    layer carried by that taxonomy entry.  Unknown IDs and layer mismatches stop
    before routing so a model or domain agent cannot cross the infra/service
    boundary by changing ``target_layer``.
    """

    candidates = rca.get("candidate_classifications") or []
    if not candidates:
        raise ValueError("RCA has no candidate_classifications, cannot classify")

    normalized = dict(rca)
    normalized_candidates = [dict(candidate) for candidate in candidates]
    top = dict(normalized_candidates[0])
    taxonomy_match = str(top.get("taxonomy_match") or "")
    if taxonomy_match not in taxonomy:
        raise ValueError(f"taxonomy_match {taxonomy_match!r} not found in taxonomy.yaml")

    taxonomy_entry = dict(taxonomy[taxonomy_match])
    canonical_layer = str(taxonomy_entry["layer"])
    supplied_layer = top.get("target_layer")
    if supplied_layer is not None and str(supplied_layer) != canonical_layer:
        raise ValueError(
            f"target_layer mismatch for {taxonomy_match}: "
            f"rca={supplied_layer!r} taxonomy={canonical_layer!r}"
        )

    top["target_layer"] = canonical_layer
    top["taxonomy_entry"] = taxonomy_entry
    normalized_candidates[0] = top
    normalized["candidate_classifications"] = normalized_candidates
    return normalized


def resolve_ambiguity_for_review(rca: dict[str, Any]) -> str:
    """Return an optional ambiguous-path hint without authorizing a route.

    ``router._resolve_ambiguous`` is still the single existing LLM-assist seam.
    The graph consumes its text only as operator context and always stops the
    ambiguous path for review in v0.
    """

    return router._resolve_ambiguous(rca)



def _with_trace(
    state: Mapping[str, Any],
    node_name: str,
    updates: Mapping[str, Any],
) -> dict[str, Any]:
    trace = list(state.get("node_trace", []))
    trace.append(node_name)
    merged = dict(updates)
    merged["node_trace"] = trace
    return merged


def _next_after_classify(state: TaxonomyGraphState) -> str:
    return NODE_AMBIGUITY if state.get("ambiguity_required") else NODE_ROUTE


def _next_after_ambiguity(state: TaxonomyGraphState) -> str:
    return "__end__" if state.get("status") == "blocked_ambiguous" else NODE_ROUTE


def run_fault_payload(fault_payload_path: str | Path) -> dict[str, Any]:
    """Convenience function returning the final AuditEvent for a fault payload."""

    result = TaxonomyGraphRunner().walk_fault_payload(fault_payload_path)
    if result.audit_event is None:
        raise RuntimeError(f"taxonomy graph did not produce audit_event: {result.state}")
    return result.audit_event
