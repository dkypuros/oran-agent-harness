# Demo talk track

Draft 1. Speaker notes for the demo segment of the O-RAN nGRG Workshop talk
*From Multivendor Diagnosis to Closed-Loop Remediation: An Agent Harness for Cloud RAN Day-2*,
Seattle, 4th [THU] JUN 2026.

This file drives the build. Words first; everything else gets shaped to serve them.

## Placement in the 20-minute talk

| Block | Length | Content |
|-------|--------|---------|
| Opening hook | 2 min | The Day-2 problem in three sentences, why multivendor makes it worse |
| Architecture | 5 min | The macro diagram, what is on the slide |
| Three contributions | 4 min | Routing rule, guardrail contract, LLM-neutral substrate |
| **Demo** | **4 min** | **This file** |
| Trust loop + killswitch | 3 min | Reversibility profile, AT&T-reviewed crisis_mode |
| Close | 2 min | The GitHub URL, the standards-track ask |

If the talk runs long, the demo holds its 4 minutes and other blocks compress. The demo is the
piece that has to be live on screen; the rest is recoverable from slides.

## Demo structure (4 minutes, 5 beats)

| Beat | Time | What is on screen | What the speaker says (load-bearing) |
|------|------|--------------------|---------------------------------------|
| 1. Opening frame | 0:00 to 0:30 | Architecture macro PNG with the 7 boxes | "Two scenarios. Real Router. Real Guardrail. Everything else stubbed but contract-honest." |
| 2. Left loop | 0:30 to 1:30 | Verbose walker output, Stage 1 and Stage 2 highlighted | "FaultPayload to RCA. The MCP server would have emitted these signals. The agent reshapes them. The taxonomy match is ptp_host_stack." |
| 3. Middle | 1:30 to 2:30 | router.py source side by side with taxonomy.yaml | "This is the part with research teeth. Deterministic taxonomy. The Router decides up versus down. The Guardrail evaluates four rules." |
| 4. Right loop | 2:30 to 3:30 | audit_event.json with the reversibility profile expanded | "Seven fields. Rollback intent, blast radius, rebuild timeline, twin verdict, risk burn-down. The contract is honest about what reverse looks like." |
| 5. Killswitch | 3:30 to 4:00 | terminal split: walker on left, activate command on right | "Operator override. Every write freezes. The reversibility profile stays queryable. Fail safe, not catastrophic." |

## Script (full prose, read for timing)

> [Beat 1, opening, 0:00 to 0:30]
>
> What you are about to see is a deterministic stub runtime that proves the closed loop composes
> end-to-end. The Router and the Guardrail engine are real Python. The Gateway, the MCP servers,
> the Domain Agents, and the Digital Twin are stubbed, but every contract at every seam validates
> against a schema and cites an upstream spec. The repo is at github.com/dkypuros/oran-agent-harness.
> Two scenarios. Both PTP host-platform faults. One is service contention. The other is a driver
> regression. Watch the same architecture handle both without changing the path.

> [Beat 2, left loop, 0:30 to 1:30]
>
> Scenario A. fw-lldp-agent active on the PTP-bound slave interface. In production, the linuxptp
> daemon publishes a CloudEvent. Here we load the FaultPayload from disk. The evidence array
> carries what an MCP server would have emitted: ptp4l state unstable, master offset spike,
> tx_hwtstamp_timeouts climbing past threshold. A Platform Domain Agent reshapes this into an
> RCA. Candidate classification: ptp_host_stack, target layer infra, confidence high. The
> contract is what matters here. The FaultPayload validates against harness/schemas/FaultPayload.
> The MCP tool surface is declared in harness/mcp-tool-schemas/mcp-platform.json. Every spec-derived
> claim has a bibliography reference. The reversibility profile and the crisis_mode envelope are
> explicitly harness-unique and labeled as such. If you read the verbose output during the recorded
> run, every artifact at every seam parses.

> [Beat 3, middle intelligence, 1:30 to 2:30]
>
> This is the part with real teeth. The Router loads taxonomy.yaml at import time. Twenty entries
> organized around the IMS/SMO boundary established in WG6's O2 interface architecture (O2-GAnP
> Sections 3.2 through 3.4). Twelve infra. Five service. Three ambiguous. The
> classification feeds a routing rule. Infra routes down to the O-Cloud via the O2 IMS Provisioning
> Service, which a production SMO would invoke through FOCOM. Service routes up to the SMO as a
> TMF921 intent. MCP is internal scaffolding that orchestrates the agent loop; it is not an O-RAN
> management plane interface. R1 would expose the resulting capability to the SMO. A1 targets
> Near-RT RIC behavior; this harness targets infrastructure remediation via O2 IMS, a different
> layer. The ambiguous path is where LLM-assist would tier in. Neither
> scenario in this set triggers it. That is deliberate. The deterministic core is what gives this
> work research credibility. The Guardrail engine then evaluates four named elements. Action
> allowlist. Blast radius caps. Require human approval. Crisis mode global override. All four
> pass for Scenario A. The output is a TMF688-shaped AuditEvent.

> [Beat 4, right loop, 2:30 to 3:30]
>
> Inside the AuditEvent, the reversibility profile. This is the trust-loop contribution. Seven
> fields. Rollback intent, the inverse action with target and payload. Blast radius if reverse,
> nodes and sites and cells affected. Rebuild timeline, estimated minutes with a confidence band.
> Replication history, how often this remediation has run in a 30-day window. Validation history,
> Digital Twin pass rate. Risk profile burn-down. And confidence in reversibility. Every field is
> a real EvalOps category. Today the values are stubbed from a per-scenario table. In production,
> EvalOps telemetry fills them. The committed remediation.yaml is a real MachineConfig CR. If you
> point this runtime at a real O-Cloud Manager, the apply happens.

> [Beat 5, killswitch, 3:30 to 4:00]
>
> One more thing. We flip the killswitch. CrisisModeActivation envelope. Operator override. The
> Guardrail engine refuses every write. The reversibility profile stays queryable. This is the
> AT&T operations team review pattern. Agentic systems fail safe, not catastrophic. That is the closing piece
> of the agentic recoverability story, and that is the contract this harness is offering for
> standards discussion.

## Word count and pacing

- Actual prose count: 548 words across the 5 beats (87, 118, 177, 108, 58).
- At a conversational technical-speaker pace of 150 to 170 words per minute, that lands at
  3:13 to 3:39. **Under the 4-minute target slot. Beat 3 is now the longest at roughly 1:05.**
- Two options:
  1. Keep at 3 minutes. Use the extra minute as transition breathing room into the trust-loop
     block. Lower risk on talk day.
  2. Expand to 4 minutes. The under-served beats are the ones with the strongest material to
     amplify: Beat 3 (router + guardrail internals) can carry another 80 to 100 words showing one
     specific routing decision walked through verbally. Beat 4 (reversibility profile) can carry
     another 50 words on validation history and what twin_pass_rate 1.0 actually proves.
- If the slot compresses on talk day, drop Beat 5 (killswitch moves into the trust-loop block
  immediately after). That recovers 30 seconds. Cuts target time to roughly 2:30.

## What every beat needs the demo to show

This is the build implication. Each row maps a beat to a sub-issue under the big-demo umbrella.

| Beat | What must appear on screen | Sub-issue |
|------|----------------------------|-----------|
| 1 | The static macro diagram already in talk/architecture.png | (already shipped) |
| 2 | Verbose walker output for Scenario A, Stage 1 plus Stage 2 readable | #15 (Agent), or fallback to existing make demo |
| 3 | router.py and taxonomy.yaml side by side | Static screenshot, no build needed |
| 4 | audit_event.json with reversibility_profile rendered as a 7-row card | #20 (dashboard) or static slide |
| 5 | Live terminal showing crisis_mode activation refusing the next walker invocation | #19 (killswitch end-to-end) |

The minimum buildable set to support every beat: #15, #19, #20. The other 8 big-demo issues
are amplifiers that improve the look but do not change what the script says.

## Open decisions (for David)

1. **Beat 5 placement.** Killswitch as the demo closer here, or as the opener of the trust-loop
   block immediately after? Either works; the demo-closer placement gives the demo a sharper
   ending but spends 30 seconds on something that is not the core agentic-recoverability framing.
2. **Beat 3 visualization.** Source code side-by-side reads as deep but lands flat in a recorded
   capture. Alternative: an animated decision-tree showing the taxonomy entries and the routing
   rule firing on each scenario. More polish, more build effort.
3. **Live versus recorded.** A live demo of the killswitch carries more conviction. A recorded
   capture eliminates demo-day failure modes. The OpenScreen pipeline (issue #21) supports
   either. Recommend recorded with a live re-run as backup if time permits.
4. **Scenario A only, or A and A-prime together?** A only fits in 4 minutes comfortably. A and
   A-prime together require either compressing each by 30 seconds or expanding the slot to 6
   minutes (which compresses the contributions block). Recommend A only on stage; A-prime
   appears in the GitHub repo for self-serve replay.
5. **Drop or keep the bibliography callout in Beat 2?** Removing it saves 8 seconds. Keeping it
   reinforces the citation-discipline story but may read as pedantic.

## Constraints honored

- No em dashes (U+2014). Commas, periods, and parentheses only.
- No marketing language. Technical depth assumed.
- All file paths are accurate against the current repo (commit 8a9a402, post Issue #10).
- All bibliography references exist in docs/references.md.
- The script does not over-claim. Stubbed components are named as stubbed when relevant.

## Next iterations

- Draft 2: David's voice pass. The current draft is in the style of "technical Red Hat principal";
  pull it toward David's actual rhythm.
- Draft 3: time the prose against a stopwatch read-aloud. Trim or expand to hit 4:00 exactly.
- Draft 4: lock the build implications. The minimum set is #15, #19, #20. Decide whether the rest
  earn their slot or get pushed to a v0.2 follow-up.
