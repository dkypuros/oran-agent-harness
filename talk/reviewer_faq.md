---
title: "Reviewer FAQ"
author: David Kypuros
venue: O-RAN nGRG Workshop, Seattle
date: 4th [THU] JUN 2026
license: Apache-2.0
status: anticipated reviewer questions with citation-anchored answers
---

# Reviewer FAQ

Questions the speaker expects from working-group reviewers, senior engineers, vendor PMs, and
academic readers. Each answer is anchored at file plus line where possible so the reviewer can
verify the claim without taking the speaker's word.

## Q1. How is this different from existing agentic-RAN frameworks?

Most prior agentic-RAN work either stops at the SMO boundary (the proposal terminates as an
intent, no delivery story) or proposes a custom controller plane that side-steps O-RAN's own
resource layering. This bench grounds the right-side execution path in two standardized contracts
simultaneously: O-RAN O2 IMS above (`docs/references.md#ref-2`, `docs/references.md#ref-3`), and
the CRD-shaped delivery contracts below (Metal3 BareMetalHost / HostFirmwareComponents at
`docs/references.md#ref-8`; Machine Config Operator at `docs/references.md#ref-9`). The 2+3+8+9
conjunction is the novelty claim. Full positioning at `talk/architecture_narrative.md` lines
18-35.

## Q2. Why deterministic taxonomy first instead of LLM-first?

LLM-first routing has two failure modes that matter for production telco: nondeterministic
outputs on identical inputs, and silent drift when a model version changes. The bench inverts
this: the taxonomy at `harness/taxonomy.yaml` is a 20-entry deterministic lookup against the
O-RAN WG6 O-Cloud resource model. The LLM is invoked only when the taxonomy resolves to the
`ambiguous` class, which is a minority of faults. The routing rule at
`harness/routing-rules/contribution-1-routing-rule.yaml` enforces this ordering. The deterministic
runtime is at `harness/runtime/router.py`; the test suite at `tests/test_runtime.py` exercises
both the deterministic path and the LLM-assist path.

## Q3. What about LLM bias in the ambiguity resolution step?

EvalOps treats agent quality the way SRE treats latency: continuously measured, tied to specific
scenarios, surfaced as a first-class telemetry signal. The harness tracks, per taxonomy entry,
the historical accuracy of both the deterministic classifier and the LLM-assist tier (see
`talk/trust_loop.md` lines 30-42). Drift in either signal triggers operator review. Plus, every
LLM response on the ambiguous path is recorded in the AuditEvent's `knowledge_base_lookups`
field, so the bias case has an audit trail.

Implementation status for this in v0 is tracked in `../docs/evalops-and-validation.md`: EvalOps fields and schemas exist today, while live telemetry is the v1 replacement for fixture-backed values.

## Q4. How does this interact with the O1 / O2 vs MCP-private telemetry boundary?

The MCP servers consume O-Cloud-internal platform telemetry (linuxptp state, MachineConfig pool
status, KMM Module load state, NIC PHC counters). This is NOT governed by O-RAN O1
(`docs/references.md#ref-49`), which standardizes SMO-to-managed-element OAM where managed
elements are O-CU, O-DU, O-RU. The O-Cloud platform layer sits below the managed-element
boundary. The standardized SMO-facing flow IS spec-governed: the guardrail engine emits a TMF688
AuditEvent (`docs/references.md#ref-18`) and the O-Cloud Manager exposes alarms via the O2 IMS
AlarmEventRecord (O2IMS-INTERFACE R005-v11 Section 3.3.6.2.2,
`docs/references.md#ref-3`). Full boundary discussion at `talk/architecture_narrative.md`
section 2.

## Q5. Why route through Machine Config Operator instead of direct kubectl?

Three reasons. First, MachineConfig (`docs/references.md#ref-9`) is the audited delivery
mechanism on OpenShift O-Cloud; direct kubectl bypasses cluster-admin separation. Second, MCO
handles node draining, ordered reboot, and pool-level coordination, which the harness should not
re-implement. Third, the audit trail lands in the same place every other change does, so the
operator who reviews MCO changes weekly does not need a new tool for harness-driven changes.

## Q6. What's the rollback story?

Every AuditEvent carries a populated ReversibilityProfile (schema at
`harness/schemas/ReversibilityProfile.json`) with seven fields: rollback_intent,
blast_radius_if_reverse, rebuild_timeline, replication_history, validation_history,
risk_profile_burn_down, confidence_in_reversibility. Agentic Recoverability runs the inverse
action on the Digital Twin before the operator commits, and writes the verdict to the
validation_history field. See `talk/trust_loop.md` lines 56-67.

## Q7. What if the digital twin diverges from production?

EvalOps measures twin-vs-prod fidelity continuously as part of the same telemetry stream that
tracks agent accuracy. When fidelity drops below a threshold, the harness downgrades EvalOps
confidence on twin-passed proposals. Twin substrate is operationally flexible per
`talk/trust_loop.md` lines 24-28: a same-topology mirrored cluster OR a simulated linuxptp plus
NIC stack works. The architecture is twin-substrate-neutral.

## Q8. How does crisis_mode get activated and by whom?

A NOC supervisor sets `crisis_mode: true` in `harness/guardrails.yaml`. When active:
all write paths revoked (O2 IMS and SMO TMF921), EvalOps confidence pinned to zero, telemetry
routed to manual queue. Existing in-flight actions allowed to complete or roll back; no new
actions accepted. Full discussion at `talk/killswitch.md` (AT&T-reviewed per the document's
status line). Activation pathway in `harness/runtime/guardrail.py`; the
`test_evaluate_crisis_mode_active` test verifies the override.

## Q9. Is this Red Hat product code or research?

Research bench under Apache 2.0. Not product. The reference O2 IMS implementation cited
throughout IS Red Hat product (`openshift-kni/oran-o2ims`, `docs/references.md#ref-6`), but the
harness pattern itself is operationalization-agnostic. The contracts are portable to LangGraph,
OpenAI Agents SDK, Microsoft Semantic Kernel, or any agent framework that reads JSON Schema and
YAML.

## Q10. What scale has this been exercised at?

The four walkthrough scenarios under `scenarios/` are fixture-driven, exactly as committed. The
research bench at `5G_O-RAN_SIM/bench/` runs all four end-to-end deterministically. The
research foundation is a 1+ year Ericsson Red Hat Intel initiative where the speaker is the
solo Red Hat representative; the bench is the open-source crystallization, not the full
production deployment. Production-scale numbers belong to the partner engagement, not the bench.

## Q11. Where's the paper?

The repo IS the paper. The citation pyramid at `docs/references.md` (52 numbered AMA-style
refs), the narrative at `talk/architecture_narrative.md` anchored at file plus line, and the
runnable demo are the three layers. The verify gate (`scripts/verify.py`) gives a reviewer a
falsifiable yes/no on the structural claims. A traditional paper companion is possible if a
venue requires one, but is not the primary artifact.

## Q12. How portable is this beyond Ericsson?

The harness pattern is operationalization-agnostic. Three contributions: routing rule (declared
at `harness/routing-rules/contribution-1-routing-rule.yaml`), guardrail contract
(`harness/routing-rules/contribution-2-guardrail-contract.yaml` plus
`harness/guardrails.yaml`), LLM-neutrality
(`harness/routing-rules/contribution-3-llm-neutrality.yaml`). The contracts read identically
whether the partner SMO is Ericsson, Nokia, Amdocs, Mavenir, or ZTE. The TMF921 intent shape is
the standardized interop point.

## Q13. Is there a slide deck I can have?

The repo has more than the deck. Point reviewers at the repo URL plus
`talk/architecture_narrative.md` for the full walkthrough. Slide deck is out of scope for this
repo per the locked plan decision (see `talk/slides.md`).

## Q14. How does the dual-route handle transaction atomicity between the TMF921 up route and the O2 IMS down route? What if the partner SMO rejects the companion intent after the firmware push has already started?

The dual-route is parallel emission, not a distributed two-phase commit. All three mechanisms
that handle the failure modes are implemented in v0 of the bench and exercised by the test
suite.

1. **The Sandbox gates the down route on twin convergence, not on the up route's acceptance.**
   Implemented in `harness/runtime/walker.py` `sandbox_simulation()` (the stage between Router
   and Guardrail). Reads the per-scenario twin verdict from
   `harness/runtime/scenario_stubs.json` `sandbox_verdict` block. The verdict carries
   `simulator_version`, `twin_converged`, `baseline_match`, `deviation_observed`, and
   `apply_allowed`. The Guardrail engine at `harness/runtime/guardrail.py` checks
   `apply_allowed`; if False, it raises `ValueError("sandbox_verdict.apply_allowed is
   False ... down-route blocked at twin gate")` before reaching the action_allowlist or
   blast_radius checks. Proven by `tests/test_runtime.py::test_evaluate_sandbox_block_when_apply_disallowed`,
   which monkey-patches a False verdict and asserts the apply is blocked.

2. **The up route's outcome lands in the AuditEvent BEFORE operator co-authorization.** The
   harness emits the TMF921 companion intent and captures the SMO's response in
   `companion_intent.dispatch_result`. Implemented in `harness/runtime/router.py`
   `_maybe_attach_dispatch_result()` and exercised end-to-end by
   `scenarios/E_with_smo_reject/`, where the SMO rejects the maintenance window because
   neighboring cells are at 92% capacity. The operator sees the rejection in the
   AuditEvent before signing. Proven by
   `tests/test_runtime.py::test_dispatch_result_rejected_on_smo_reject_scenario` (walks the
   scenario end-to-end and asserts `companion_intent.dispatch_result.accepted == False`).
   Per the `co_authorization` block in `harness/guardrails.yaml`, the operator can edit
   `permitted_modifications` (defer the apply, adjust the window, change the target node)
   or withhold approval entirely. The operator is the reconciliation point.

3. **The Killswitch is the global abort for the mid-flight failure case.** Implemented in
   `harness/runtime/guardrail.py` as the `_CRISIS_MODE_ACTIVE` seam that, when set, raises
   `RuntimeError("crisis_mode active, all writes frozen")` before any further evaluation.
   When activated by a NOC supervisor per `talk/killswitch.md`, all write paths revoke
   (O2 IMS and SMO TMF921), EvalOps confidence pins at zero, in-flight actions are allowed
   to complete or roll back per the ReversibilityProfile. Proven by
   `tests/test_runtime.py::test_evaluate_crisis_mode_active`.

A reviewer can verify all three by cloning the repo, running
`python -m tests.test_runtime`, and inspecting the test output (8/8 PASS including the
two new tests above). The walker_e2e check in `scripts/verify.py` exercises both the
accepted and rejected dispatch_result paths across the five committed scenarios.

What the architecture explicitly does NOT do: distributed two-phase commit across the SMO
and the O-Cloud. That would require a global transaction coordinator and would couple the
SMO's scheduling logic to the O-Cloud's firmware delivery state machine. Both vendors would
lose authority over their own domain. The architecture preserves their separation by making
the operator the reconciliation point and the Killswitch the global abort. Distributed
transaction atomicity across the SMO-to-O-Cloud boundary is an open research direction for
Day-3 (`narratives/trajectory_what_day_3_looks_like.md`, workstream 1, multi-site
coordination).

File anchors:
  `harness/runtime/walker.py` `sandbox_simulation()` for the Sandbox stage
  `harness/runtime/guardrail.py` for the Sandbox gate (`apply_allowed` check) and crisis_mode override
  `harness/runtime/router.py` `_maybe_attach_dispatch_result()` for the SMO response capture
  `harness/runtime/scenario_stubs.json` per-scenario `sandbox_verdict` and `smo_dispatch_outcome` blocks
  `harness/guardrails.yaml` for co_authorization and crisis_mode policy
  `scenarios/E_nic_firmware_update/` for the accepted dual-route path
  `scenarios/E_with_smo_reject/` for the SMO-rejection dual-route path
  `tests/test_runtime.py` 9/9 PASS, including the Sandbox gate, the SMO rejection capture, and the O2 IMS hop tests

## Q15. Why MCP and not LangGraph, Semantic Kernel, Bedrock Agents, or OpenAI Agents SDK?

The MCP choice is about the SERVER-TOOL contract, not the orchestrator. MCP
(`docs/references.md#ref-13`, `#ref-14`, `#ref-15`) standardizes how a tool surface declares its
inputs, outputs, and metadata; the orchestrator that consumes those tools is interchangeable.
The bench's four MCP servers (`harness/mcp-tool-schemas/mcp-platform.json`, `mcp-ran.json`,
`mcp-hardware.json`, `mcp-ocloud.json`) are valid for any host that speaks MCP. The orchestrator
could be the Claude Code CLI, LangGraph, Semantic Kernel, or OpenAI Agents SDK with no change to
the server side. Contribution 3 is exactly this LLM-neutral substrate
(`harness/routing-rules/contribution-3-llm-neutrality.yaml`). Picking LangGraph instead would
have coupled the harness to one orchestrator and one vendor; MCP keeps that coupling out of the
contract.

## Q16. Where is E2 and the Near-RT RIC in this architecture?

Outside scope by design. E2 (`docs/references.md#ref-52`, the WG3 family E2GAP / E2AP / E2SM-KPM
/ E2SM-RC / E2SM-LLC) governs Near-RT RIC interactions with E2 nodes (O-CU, O-DU). The harness
targets INFRASTRUCTURE remediation (host config, drivers, firmware, NIC stack) via O2 IMS, which
is a different layer. The disclaimer is explicit at `talk/architecture_narrative.md` section 5
three-layers paragraph. The harness composes with E2-driven RIC behavior at runtime (a slice
intent update that originates from a Near-RT RIC xApp could flow into the SMO and trigger a
companion intent), but the harness itself does not consume E2 messages.

## Q17. Where is A1 and the Non-RT RIC?

Also outside scope by design. A1 (`docs/references.md#ref-50`, WG2 A1GAP and A1AP) targets
Near-RT RIC behavior: slice SLA enforcement, traffic steering policies, QoS. The harness targets
the layer BELOW (infrastructure remediation via O2 IMS). The two layers compose cleanly. The
positioning note is in `talk/architecture_narrative.md` section 5 and in
`harness/routing-rules/contribution-3-llm-neutrality.yaml` layering_disclaimer block.

## Q18. Where is R1?

R1 (`docs/references.md#ref-51`, WG2 R1GAP and R1AP) is the SMO-internal service-exposure
interface for rApps. The harness's MCP gateway is NOT R1; MCP is internal agent scaffolding
within the harness itself. If a future deployment wraps the harness as an rApp consumed by other
SMO components, R1 is the surface to expose. v0 does not implement an R1 endpoint. The
distinction is explicit at `talk/architecture_narrative.md` section 5 and in the
`contribution-3-llm-neutrality.yaml` layering_disclaimer.

## Q19. How does this differ from Nephio?

Nephio (`docs/references.md#ref-36`) is cloud-native network automation focused on package
specialization and KRM-based intent for orchestration. The harness is closed-loop REMEDIATION:
diagnostics flow into a deterministic router, the router emits a RemediationProposal, the
guardrail engine gates it, the Twin pass validates it, the operator co-authors. Different
problem. The two compose: Nephio could deliver the initial cluster topology and standing
configuration; the harness handles post-deployment Day-2 anomalies on top of that topology.

## Q20. How does this differ from ONAP and OSM?

ONAP (`docs/references.md#ref-37`) and OSM (`docs/references.md#ref-38`) are management and
orchestration platforms. They are spec-aligned with the broader telco automation stack but
neither one ships a closed-loop remediation harness with a deterministic taxonomy, a five-gate
guardrail engine, and a Reversibility Profile attached to every audit. The harness pattern can
sit ABOVE ONAP or OSM (consuming their resource inventory and emitting remediation proposals
into their action surface) or BESIDE them (running against an OpenShift O-Cloud directly via O2
IMS, which is what v0 demonstrates).

## Q21. Is this production-ready?

No. v0 is a research substrate. The CONTRACTS (schemas, taxonomy, routing rule, guardrails,
ReversibilityProfile, AuditEvent) are publication-ready and validated by the verify gate. The
RUNTIME is stub-driven for the five committed scenarios; the platform stubs in `5G_O-RAN_SIM/`
emit shape-correct envelopes without crossing real network boundaries. The runnable layer that
wires the harness to a real Ericsson partner SMO, a real Red Hat O-Cloud Manager, real Metal3
BMO, and real Redfish-attached hardware is the v1 target. The honest-scope note appears at
`talk/architecture_narrative.md` and on every stub file's docstring.

## Q22. Is the LLM actually doing anything in the four committed scenarios?

No, by design. All four scenarios resolve via deterministic taxonomy lookup in
`harness/runtime/router.py` against `harness/taxonomy.yaml`. The LLM-assist tier is exercised
only when the taxonomy returns the `ambiguous` class. `ORAN_LLM_MODE=live` lights up the seam to
`5G_O-RAN_SIM/llm/inference_client.py` and the test
`test_route_ambiguous_with_llm_mode_live` proves the wire is connected, but no committed
scenario hits that path. This is the point: the LLM is NOT load-bearing on the routing decision.
It's a fallback for the residual ambiguous class. Contribution 1 is the routing rule, not the
LLM call.

## Q23. What conformance test suite is this validated against?

Two levels. (1) The repo-internal verify gate (`scripts/verify.py`) runs ten checks: citation
headers, JSON parse, YAML parse, conformance.md bidirectional completeness, em-dash audit,
leakage guard, README structure, file counts, schema validation, runtime walker end-to-end. Five
seconds end-to-end on a fresh clone. (2) The intended external target is the O-RAN Software
Community O2 IMS Compliance Test Suite (`docs/references.md#ref-5`,
`github.com/o-ran-sc/it-test`), which validates a real O2 IMS implementation against the
WG6.O2IMS-Interface spec. The harness emits requests SHAPE-correct enough that swapping the stub
for the SC suite is a v1 work item, not a redesign.

## Q24. How does this position against the O-RAN Decoupled SMO Architecture (WG1 TR R004)?

The harness is a candidate Closed-Loop Remediation SMOS (SMO Service) in the Decoupled SMO
framework (`docs/references.md#ref-48`). The narrative positions this explicitly: the harness
exposes a TMF688 audit emission surface and a TMF921 intent emission surface, both of which are
SMOS-compatible contract shapes. The standards-track ask in the close is twofold: (1) nGRG
outputs that name the closed-loop remediation SMOS as a first-class element of the Decoupled SMO
catalogue, and (2) a TMF Implementation Guide companion that documents the harness-unique
extensions (dispatch_result on TMF921 companion intents, the seven-field ReversibilityProfile)
as candidate API extensions.

## Q25. Why does the O2 IMS stub call its envelope "DeploymentRequest" when the O2IMS-Interface R005 spec calls the canonical resource "provisioningRequests"?

Terminology overlap that hedges to the broader concept. The spec carries both: `DeploymentManager`
is the managed entity ID, and `provisioningRequests` is the action collection. The stub envelope
label "DeploymentRequest" packages the request-plus-response pair, and the fields
`deploymentManagerId` and `deploymentRequestId` map onto the DM identity and the provisioning
action identity respectively. The stub's `_conforms_to.spec_section` deliberately reads
"Infrastructure Management Services request and response envelope" so both interpretations are
covered. The terminology note appears in `5G_O-RAN_SIM/oam/o2ims_stub.py` lines 5 through 17.

## Q26. Where are mTLS, OAuth2, and IP allowlist implemented?

In v0, nowhere. The Agentic Gateway in the architecture diagram exposes vendor-private tooling
"under controlled MCP interfaces (mTLS, OAuth2, IP allowlist; architectural pattern, v0 lab
trusts localhost)" per `talk/architecture_narrative.md` section 2. The phrasing is intentional:
the controls describe the production deployment posture, not the v0 lab runtime. v0 is
localhost-trust because the bench runs on a developer workstation. WG11-flavored OAuth2 stubs
exist in `5G_O-RAN_SIM/` for the broader platform but not for the harness's MCP gateway
specifically. Wiring real mTLS, OAuth2, and IP allowlisting onto the MCP gateway is a v1 work
item.

## Q27. What does "AT&T-reviewed" mean for the Killswitch?

The Killswitch design (crisis_mode in `harness/guardrails.yaml`, narrated in `talk/killswitch.md`)
was reviewed with AT&T operations stakeholders in a partner engagement context. The review
covered the activation pathway (who can flip crisis_mode), the write-path revocation contract
(both O2 IMS and SMO TMF921), the EvalOps confidence pinning at zero, and the manual telemetry
queue routing. The review was not a public ratification; it was operator input that shaped the
design before publication. The honest-scope phrasing in `talk/killswitch.md` reflects that.

## Q28. How is the O2 IMS hop actually exercised in code, not just claimed?

`harness/runtime/router.py::_call_o2ims_deploy()` (added in commit 23a6601) calls
`5G_O-RAN_SIM/oam/o2ims_stub.deploy_request()` whenever the routing decision lands on the infra
layer. The returned envelope is attached to the proposal as `o2ims_dispatch` and flows through
to the AuditEvent at `event.remediation.o2ims_dispatch`. The block carries
`deploymentManagerId`, `deploymentRequestId`, `ocloud_internal_path`, `reconciler_target`,
`ocm_version`, and `ocm_response`, plus a `_conforms_to` citing refs 2, 3, 6. The unit test
`test_o2ims_dispatch_attached_on_down_route` asserts that infra routes attach the envelope and
service routes do NOT (service routes cross TMF921, not O2 IMS). All five committed scenario
audit_event.json fixtures show the populated envelope. This is the v0 implementation that turns
the architecture diagram's O2 IMS edge into a real function call, not a synthesized string.

## Q29. What's the standards-track ask in the close?

Two specific asks. First, an nGRG output (technical report or recommendation) that names the
Closed-Loop Remediation SMOS as a first-class element of the Decoupled SMO Architecture
(`docs/references.md#ref-48`). This grounds the harness pattern in O-RAN's own architectural
catalogue. Second, a TM Forum Implementation Guide companion that documents two harness-unique
extensions as candidate API additions: (a) the `dispatch_result` field on the TMF921 companion
intent (the partner SMO's response shape, populated by `_maybe_attach_dispatch_result()`), and
(b) the seven-field Reversibility Profile attached to every TMF688 audit event. Both extensions
are in the schemas at `harness/schemas/` and the IG draft is a v1 deliverable not in this repo.

## Q30. How does this compose with the prior Ericsson multivendor diagnostic blog?

The prior published work (`docs/references.md#ref-35`, Kiani Mehr S, Korati Prasanna N, Kypuros
D, Vazquez Cebrian M, Srikanthan S, Venkatesh P, Multivendor agentic AI solution for Cloud RAN
troubleshooting, Ericsson Technology Blog, MAY 2026) established the diagnostic substrate: an
MCP-coordinated multivendor fault-localization layer that converges on a root cause. This work
extends that substrate to closed-loop remediation. The diagnostic agents in the prior work feed
the RCA artifact that this harness's router consumes. The novelty in this talk is the right-side
execution path (the 2+3+8+9 conjunction), not a re-derivation of the diagnostic layer. The
attribution is explicit in `talk/architecture_narrative.md` novelty paragraph (commit 44933da)
and in the bibliography refs cited from `omc-skills/o-ran/troubleshoot.md`
(`bibliography_refs: [31, 35]`) and `omc-skills/o-ran/plan.md` (`bibliography_refs: [1, 2, 3,
17, 18, 19, 31, 35]`).

## Q31. What if the verify gate passes but the runtime is wrong?

Possible in principle and worth saying out loud. The verify gate validates structural claims
(schemas resolve, citations resolve, fixtures match the walker's actual output on named
material fields, em-dash count is zero, no .local leaks). It does NOT validate that the routing
decision is the operationally CORRECT one for a given fault class. The defense against that gap
is the unit test suite (`tests/test_runtime.py`, 9/9 passing including the negative paths
test_evaluate_sandbox_block_when_apply_disallowed,
test_dispatch_result_rejected_on_smo_reject_scenario, test_o2ims_dispatch_attached_on_down_route)
plus the deterministic taxonomy itself (a routing decision that contradicts the taxonomy fails
schema validation because the routing rule constrains it). A real operational deployment would
add EvalOps drift monitoring as a third layer above both; that's a v1 work item.

## Q32. How would you scale this beyond one cluster?

Out of scope for v0; honest answer is "we have not exercised multi-cluster." The architecture
does not BAR scale: each O-Cloud has its own O-Cloud Manager (and therefore its own O2 IMS
endpoint), each cluster runs its own MCP server set, and the harness instance can be one
per-cluster or one per-region with the routing-rule splitting on cluster identity. The
multi-site coordination question (when a maintenance window on cluster A forces handover to
cluster B) is named explicitly as a Day-3 research direction in
`narratives/trajectory_what_day_3_looks_like.md` (workstream 1). Production-scale numbers belong
to the partner engagement under NDA, not the bench.

## Q33. What's the latency budget for a remediation cycle?

The bench is not optimized for latency; it's optimized for contract clarity. The deterministic
runtime (walker plus router plus guardrail) completes one scenario in under 100 milliseconds on
a developer workstation when stubs return immediately. The real-world latency budget is
dominated by (a) the LLM-assist tier on the ambiguous path (seconds, not milliseconds), (b) the
Twin pass on the Sandbox stage (seconds to tens of seconds depending on twin fidelity), and (c)
the operator co-authorization step (human time). The architecture explicitly does not target
sub-second remediation; the audience for a real apply is a NOC operator on a maintenance
window, not an automated control loop.

## Q34. Who owns the operator approval seat in production?

A licensed NOC operator at the carrier. The harness emits a TMF688 audit event with a populated
ReversibilityProfile; that audit lands in whatever incident management system the carrier
already uses (ServiceNow, BMC Remedy, the SMO's own dashboard, or a custom NOC UI). The
operator reviews the audit, edits the proposal per the `co_authorization.permitted_modifications`
list in `harness/guardrails.yaml`, and signs. The bench's dashboard at `macbook_lab/dashboard/`
is a lab-grade VIEWER (not the production approval surface). The production-grade approval flow
lives in the carrier's existing change-management tooling, which is why TMF688 is the audit
envelope: the audit already lands in the right place.

## Q35. What's the v0 to v1 plan?

The Day-2 v0 to v1 transition is captured at `narratives/trajectory_what_day_3_looks_like.md`.
Concretely: (1) wire the harness to a real Red Hat O-Cloud Manager (production
`openshift-kni/oran-o2ims`), (2) wire the dual-route up branch to a real partner SMO TMF921
endpoint instead of the stub, (3) light up the LLM-assist tier with a production model (Claude,
GPT, or a vLLM-hosted local), (4) add the EvalOps drift-monitoring layer, (5) implement the
co-authorization edit-phase wiring (the v1 target named in `talk/architecture_narrative.md`
section 4 scoping note), (6) MCP gateway with real mTLS / OAuth2 / IP allowlist. The
publication-grade contracts in v0 are unchanged; v1 swaps stubs for real systems behind the
same contract shapes.
