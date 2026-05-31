---
title: "Chat demo prompt playbook"
author: David Kypuros
venue: O-RAN nGRG Workshop, Seattle
date: 4th [THU] JUN 2026
license: Apache-2.0
status: curated prompts for the oh-my-tiny-oran chat tab, sequenced for storytelling, with the pedagogical why for each
---

# Chat demo prompt playbook

This file gives the speaker a ready-to-paste set of prompts for the **oh-my-tiny-oran** chat at
`http://localhost:8097/#chat`. Each prompt is annotated with:

  - **The prompt** (verbatim, copy-paste)
  - **What the agent does** (expected tool calls and key response fields)
  - **The architectural moment it teaches** (the reason this prompt earns its place)

The prompts are sequenced for a 25-minute talk demo, but any subset works in isolation. For
hallway capture, the orchestrator alone covers the surface. For a deep technical walkthrough,
the five scenario prompts plus the two follow-up prompts cover the full architecture.

---

## Section 1: Warm-up prompts (no scenario firing)

These prompts establish the chat surface and the harness contracts before any remediation
fires. Use them to anchor the audience before the live action.

### Prompt 1.1: Pre-flight orchestrator survey

**Prompt:**

```
/oran-discover:plan
```

**What the agent does:** Reads the six discovery skill markdowns, then curls the lab's HTTP
wrappers for live state, then synthesizes a one-page survey covering left loop, infrastructure
loop, service loop, taxonomy, and guardrail policy. Roughly 30 seconds, ~10 tool calls.

**What it teaches:** Demonstrates the chat IS the harness, not a separate viewer. The
orchestrator skill walks all six discovery skills in one chat turn. The output mirrors the
narrative's four-piece structure (left loop, cognitive middle, routing decision, sandbox plus
operator seam) at the resting state of the lab. This is the canonical talk opener for slide 6
because it tells the audience what the lab looks like before anything fires.

**Captured run:** `talk/demo_logs/2026-05-30_oran-discover-plan_orchestrator_run.md`

### Prompt 1.2: Inspect the routing taxonomy

**Prompt:**

```
/oran-discover:taxonomy
```

**What the agent does:** Reads `harness/taxonomy.yaml` (20 entries grounded in the O-RAN WG6
O-Cloud resource model) and produces a structured walkthrough showing taxonomy ids, target
layers, and spec anchors. Notes which entries resolve deterministically and which fall to the
ambiguous-path LLM disambiguator.

**What it teaches:** Makes the deterministic-first commitment concrete. A reviewer who hears
"the router resolves most faults deterministically" can ask "show me the lookup table" and the
agent produces it from the actual YAML. The taxonomy is the contract; this prompt surfaces it.

### Prompt 1.3: Inspect the guardrail policy

**Prompt:**

```
/oran-discover:guardrail
```

**What the agent does:** Reads `harness/guardrails.yaml` and reports the action allowlist,
blast radius caps (one node, one site, four cells in v0), dry-run defaults, co-authorization
phases, and crisis_mode override semantics.

**What it teaches:** Demonstrates the LLM-free safety surface. Tells the audience the bench is
not "AI loose in a production RAN" because every action is gated by deterministic policy. Sets
up the trust loop story for slide 7.

---

## Section 2: One prompt per scenario (the five canonical scenarios)

Each prompt below fires one of the five committed scenarios through the harness walker and
asks the chat to narrate what happened. Sequence: A → A-prime → D → E → E_with_smo_reject.
A reviewer who wants the full bench tour walks them in that order; the four-piece architecture
is illustrated by the contrasts between them.

### Prompt 2.1: Scenario A (fw-lldp-agent host service interference)

**Prompt:**

```
Fire scenario A_fw_lldp_agent through the harness walker. Show me which gates the proposal passed and what the operator sees on the AuditEvent.
```

**What the agent does:** Calls `curl_endpoint http://harness-walker:8096/run/A_fw_lldp_agent`,
reads the audit event, narrates the cognitive middle's classification
(`taxonomy_match: ptp_host_stack`, deterministic, high confidence) and the routing decision
(target_layer infra, action_type `apply_machine_config`, MCO delivery).

**What it teaches:** The simplest case in the bench. Single-route DOWN through O2 IMS to MCO.
Blast radius zero cells. No companion intent because PTP host service interference does not
touch the service layer. Teaches the deterministic-classification + routing-by-resource-layer
discipline at the cleanest scope.

### Prompt 2.2: Scenario A-prime (ice driver KMM swap)

**Prompt:**

```
Now fire scenario A_prime_ice_driver. Compare its routing decision to scenario A. Same DOWN-route or different?
```

**What the agent does:** Curls `/run/A_prime_ice_driver`, observes
`taxonomy_match: host_driver`, target_layer infra, `action_type: apply_kmm_module`. Compares
to A and explains: same DOWN-route (both flow through O2 IMS), but different CRD inside the
O-Cloud. A delivers via MachineConfig; A-prime delivers via KMM Module CR.

**What it teaches:** The architectural teaching point in the talk's slide 5. Same routing
rule, two different in-O-Cloud delivery mechanisms (MCO vs KMM). Proves the routing rule is
about resource layer, not about CRD type. The O-Cloud has its own typology of delivery
operators; the harness routes to the layer, not to the operator.

### Prompt 2.3: Scenario D (software-OK vs hardware-NOT-OK divergence)

**Prompt:**

```
Walk me through scenario D_phc_drift_hw_only. The contributing signals show software_ok AND hardware_anomaly. How does the harness avoid being fooled by the surface signal?
```

**What the agent does:** Curls `/run/D_phc_drift_hw_only`, observes the divergence signature
in contributingSignals (ptp4l state synchronized persistent AND phc2sys drift monotonic AND
NIC tx_hwtstamp_timeouts climbing). Explains the Hardware Agent's verdict overrides the
Platform Agent's reported state, classification resolves to `host_driver`, target_layer infra,
KMM route.

**What it teaches:** The MEATIEST scenario in the bench. Software-LOCKED + hardware-NOT-OK
divergence is the canonical "the surface signal is lying" case. linuxptp says it's
synchronized; the NIC hardware-timestamping says otherwise. The harness sees through the
discrepancy because the Hardware Agent has its own evidence source (the NIC PHC counters)
that the Platform Agent does not. This is the strongest teaching moment for "why three domain
agents" and "why correlation matters."

### Prompt 2.4: Scenario E (NIC firmware update with dual-route accepted)

**Prompt:**

```
Now actually fire scenario E by calling the harness walker's /run/E_nic_firmware_update endpoint. Then re-check /oran-discover:metal3 and /oran-discover:smo to show me the dual-route really happened. Compare before and after.
```

**What the agent does:** Captures before state (Metal3 and TMF921 stubs both empty), curls
`/run/E_nic_firmware_update` to fire the scenario, then re-curls metal3 and smo `/history`.
Produces a before-and-after comparison showing the 5 Metal3 firmware phases (Preparing,
Pushing, Rebooting, Verifying, Updated) AND the TMF921 MaintenanceWindowNotification with
`dispatch_result.accepted: true` and `smo_intent_id: SMO-ACK-INT-flt-E-001-companion`. About
22 seconds, ~13 tool calls.

**What it teaches:** The 2+3+8+9 conjunction in motion. The harness fires BOTH routes in
parallel for a node_firmware action: DOWN through O2 IMS into Metal3 HostFirmwareComponents
(refs 2, 3, 7, 8), AND UP through TMF921 to the partner SMO (refs 18, 19). The SMO accepts
the maintenance window because neighboring cells have capacity. The operator sees both
outcomes in the audit event before signing. This is the canonical demo prompt for slide 6.

**Captured run:** `talk/demo_logs/2026-05-30_scenario_e_dual_route_run.md`

### Prompt 2.5: Scenario E_with_smo_reject (dual-route, SMO rejects)

**Prompt:**

```
Now fire scenario E_with_smo_reject. Same firmware push as scenario E, but different worker. Compare the companion_intent.dispatch_result against scenario E. What changes for the operator?
```

**What the agent does:** Curls `/run/E_with_smo_reject`. The audit event carries the same
Sandbox apply_allowed=true (the twin still says the firmware push is safe), the same Metal3
phases, BUT the companion_intent.dispatch_result is now `accepted: false` with
`rejection_reason: neighboring_cells_at_capacity` and an SMO response explaining the 92%
capacity figure. Compares to scenario E and explains: Sandbox passed both, SMO accepted E
but rejected E_with_smo_reject. The operator becomes the reconciliation point.

**What it teaches:** This is the explicit Q14 answer made visible. Dual-route is parallel
emission, not distributed two-phase commit. The Sandbox gate is independent of the SMO's
acceptance. The dispatch_result captures the rejection BEFORE operator co-authorization, so
the operator sees both routes' outcomes and decides: defer the window, accept SLA risk, or
escalate. The Killswitch is reserve power if reconciliation fails mid-flight. Proves the
architecture's failure-mode honesty: the bench does not pretend SMO acceptance is guaranteed.

---

## Section 3: Advanced follow-up prompts (mechanism deep-dives)

Use these in Q&A or hallway capture when a reviewer presses on the Sandbox gate or the
trust posture. Each one exercises a specific architectural mechanism.

### Prompt 3.1: Prove the Sandbox gate is a real gate

**Prompt:**

```
Walk me through what happens if the Sandbox verdict comes back with apply_allowed=False. Show me the code path that blocks the apply, and tell me which test proves it.
```

**What the agent does:** Reads `harness/runtime/walker.py sandbox_simulation()` to explain
where the verdict gets attached, then reads `harness/runtime/guardrail.py evaluate()` to
explain the gate check (lines 65-72: the apply_allowed=False branch raises ValueError before
the action_allowlist check). Then reads `tests/test_runtime.py` to surface
`test_evaluate_sandbox_block_when_apply_disallowed`, which monkey-patches a False verdict and
asserts the ValueError fires.

**What it teaches:** Proves the Sandbox is not architectural cosplay. The gate is real,
enforced in the Guardrail engine, and has a passing test that fails if the gate is removed.
A reviewer who clones the repo and runs `python -m tests.test_runtime` sees 8/8 PASS
including this one.

### Prompt 3.2: Compare the two routes' outcomes across both E scenarios

**Prompt:**

```
For scenarios E_nic_firmware_update and E_with_smo_reject, read both audit_event.json files and produce a side-by-side comparison showing what changes and what stays the same. Focus on sandbox_verdict, the Metal3 phases, and companion_intent.dispatch_result.
```

**What the agent does:** Reads both audit events via `read_file`. Produces a structured
comparison: Sandbox verdict identical (apply_allowed=true both), Metal3 phases identical
(same 5-phase firmware push), `companion_intent.dispatch_result.accepted` is true for E and
false for E_with_smo_reject. The teaching contrast lives in one field.

**What it teaches:** The dual-route reconciliation question made concrete. Two scenarios,
nearly identical except for one field, demonstrate the architectural commitment: the harness
captures the SMO's response and surfaces it to the operator. No two-phase commit, no global
transaction, just observable parallel emission with operator-mediated reconciliation.

### Prompt 3.3: Demonstrate the Killswitch override

**Prompt:**

```
Explain how the Killswitch (crisis_mode) overrides the dual-route. If a NOC supervisor activates crisis_mode while scenario E is mid-flight (Metal3 Pushing phase), what happens? Cite the code and the test.
```

**What the agent does:** Reads `harness/guardrails.yaml` crisis_mode block, then
`harness/runtime/guardrail.py` lines 62-63 (the `_CRISIS_MODE_ACTIVE` check that raises
RuntimeError before any further evaluation). Reads
`tests/test_runtime.py::test_evaluate_crisis_mode_active` for the test. Explains the override
revokes O2 IMS AND TMF921 write paths, pins EvalOps confidence at zero, lets in-flight
actions complete or roll back per the ReversibilityProfile.

**What it teaches:** Closes the trust posture loop. The Sandbox gates the action at twin
convergence. The dispatch_result captures the SMO's response. The Killswitch is the global
abort if reconciliation fails. Together they are the v0 implementation of the three
reconciliation mechanisms described in reviewer FAQ Q14.

---

## Section 4: Demo sequencing for the 25-minute talk

For slide 6 of the talk (4 minutes of live or recorded demo), the recommended two-prompt
sequence is **Prompt 1.1 then Prompt 2.4**. The orchestrator sets the resting state; scenario
E fires the dual-route. Both prompts are captured in `talk/demo_logs/` so the speaker can
fall back to the recorded screencast or the trace timeline viewer if the live chat fails.

For a five-scenario hands-on tour (post-conference, hallway capture, or live workshop), the
recommended sequence is:

  1. Prompt 1.1 (orchestrator) to set the surface
  2. Prompt 2.1 (scenario A) for the simplest case
  3. Prompt 2.3 (scenario D) for the meatiest divergence
  4. Prompt 2.4 (scenario E) for the dual-route accepted path
  5. Prompt 2.5 (scenario E_with_smo_reject) for the dual-route rejected path

That sequence covers all four pieces of the architecture (left loop, cognitive middle,
routing decision, sandbox plus operator seam) and the dual-route teaching moment in both
its accepted and rejected forms. About 4-5 minutes of agent compute total at Haiku 4.5
pricing of roughly half a cent per slash.

For a Q&A deep-dive, the three advanced follow-ups (3.1, 3.2, 3.3) cover the Sandbox gate,
the dual-route comparison, and the Killswitch override respectively. Pull whichever one a
reviewer presses on.

---

## How to use these prompts in the dashboard

1. Bring up the lab: `cd macbook_lab && ./run.sh`
2. Wait for the 9 containers to come up healthy (about 60 seconds on first run, instant on rerun)
3. Open `http://localhost:8097` in a browser
4. Click the **oh-my-tiny-oran** tab (second tab from the left)
5. Either click a slash shortcut button above the chat input (pre-fills `/oran-discover:<name>`) or paste a prompt from this file
6. Click **Send**
7. Watch the agent narrate

The chat persists session state in memory. Click **new session** in the top-right of the chat
tab to reset.

---

## What this file is NOT

It is not a chat transcript. The captured runs (`talk/demo_logs/`) preserve the verbatim
agent responses to two of these prompts. The other prompts are reproducible against the bench
but have not been captured. A speaker who wants to capture additional runs can paste the
prompt and copy the agent's response into a new file under `talk/demo_logs/`.

It is also not the runsheet. The runsheet (`talk/runsheet_25min.md`) is the slide-by-slide
pacing for the 25-minute talk. This file is the prompt-level companion that gives the speaker
ready-to-paste chat input for slide 6 specifically and for hallway capture more broadly.
