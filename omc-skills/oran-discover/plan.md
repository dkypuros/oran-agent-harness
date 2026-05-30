---
name: oran-discover:plan
description: Pre-flight survey orchestrator. Walks all six oran-discover skills in order and produces a single page summary of platform, taxonomy, and policy state.
argument-hint: "(no arguments)"
level: 1
citation_anchor:
  inputs:
    - ./ptp.md
    - ./metal3.md
    - ./redfish.md
    - ./smo.md
    - ./taxonomy.md
    - ./guardrail.md
  outputs: []
  bibliography_refs: [2, 3, 8, 9, 10, 18, 19, 26, 27, 28, 29, 30, 31, 44, 46]
---

# /oran-discover:plan

<Purpose>
Pre-flight check before any operator action. Walk all six discovery skills in a deliberate order
(left loop, right loop infra, right loop service, middle taxonomy, middle guardrail) and produce
one summary the operator reads top to bottom. The point is to make the operator earn awareness of
platform state, contracts, and policy before they authorize any remediation.
</Purpose>

<Use_When>
- Start of a shift: operator wants the full survey before any decisions
- Pre-talk dry-run: confirm every harness surface is reporting and the lab is healthy end to end
- Reviewer walkthrough at nGRG: one command produces the full tour
- After a stack restart: confirm everything is back online and consistent
</Use_When>

<Steps>

1. **Run `/oran-discover:ptp`**. Capture the alarm-sequence verdict pattern (software_ok,
   hardware_anomaly, firmware_anomaly). This is the left loop's current voice.

2. **Run `/oran-discover:metal3`**. Capture which BareMetalHosts have phase activity. If none,
   note that the infrastructure side is quiet.

3. **Run `/oran-discover:redfish`**. Capture which BMC tasks are in flight. Cross-check: any
   active Metal3 phase should have a corresponding Redfish task. A divergence is a clue.

4. **Run `/oran-discover:smo`**. Capture which TMF921 intents have been emitted recently. A
   recent companion intent should correlate with a Metal3 firmware push.

5. **Run `/oran-discover:taxonomy`**. List the routing taxonomy. Operator should know what the
   harness will route deterministically vs hand off to the LLM disambiguator.

6. **Run `/oran-discover:guardrail`**. Print the policy. Operator should know the blast caps,
   the action allowlist, and whether crisis_mode is active.

7. **Cross-check three things** and surface any anomaly:
   - **Loop coverage.** If PTP is emitting alarms but Metal3 / Redfish / SMO are all idle,
     either the harness has not yet routed anything or the run has not started.
   - **Right-loop consistency.** A Metal3 `Pushing` phase should pair with a Redfish `Running`
     task. A drift between them is a real signal.
   - **Dual-route consistency.** A scenario E run should emit BOTH a Metal3 firmware push AND a
     TMF921 companion intent. Missing one means the routing rule is not firing dual-route.

8. **Print one final block: "What to do next."** Three choices:
   - If there is an active fault and you want to investigate it:
     `/o-ran:troubleshoot <path to fault_payload.json>`
   - If you want to walk the existing scenario fixtures:
     `/o-ran:plan scenarios/E_nic_firmware_update/fault_payload.json`
   - If you want to fire a fresh sequence against the lab:
     `curl -X POST http://localhost:8091/publish` (PTP alarms) or
     `curl http://localhost:8096/bench/all` (full bench).

</Steps>

<Determinism_Contract>
Composition of six read-only discoveries. Same determinism guarantees as each constituent skill.
No state mutation. No LLM call. The cross-checks in step 7 are deterministic pattern matches.
</Determinism_Contract>

<Verification>
- The six constituent skills are verified by `conformance.md` in this directory.
- The cross-check logic in step 7 mirrors what the verify gate's walker_e2e exercises end to
  end; this skill is the operator-facing surface of the same checks.
</Verification>
