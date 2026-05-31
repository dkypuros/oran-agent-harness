---
title: "Runsheet: 25-minute talk for O-RAN nGRG Workshop"
author: David Kypuros
venue: O-RAN nGRG Workshop, Seattle
date: 4th [THU] JUN 2026
license: Apache-2.0
status: slide-level pacing, what to say, what to show, where to recover if something breaks
---

# Runsheet, 25 minutes

This document is the operator's manual for the talk. Each entry has a time marker, the slide
visual, what David says (key phrases, not exact words), and a fallback if a live element fails.
Total clock: 25 minutes plus a 5 minute Q&A buffer.

## Pacing summary

| Block               | Minutes | Cumulative |
|---------------------|---------|------------|
| Title + author      | 1       | 1          |
| Motivation, the "From" half of the title | 3 | 4 |
| Architecture macro, the 7-box diagram | 2 | 6 |
| Cognitive middle, deterministic taxonomy plus LLM-on-ambiguous | 4 | 10 |
| Routing decision, high side TMF921, low side O2 IMS plus CRDs | 3 | 13 |
| Demo, recorded video of scenario D or E | 4 | 17 |
| Trust loop, Digital Twin substrate, EvalOps, Killswitch | 4 | 21 |
| Novelty positioning + repo handoff | 2 | 23 |
| Q&A buffer | 2 | 25 |

## Slide-by-slide

### Slide 1 (00:00, 1 min). Title

  Show: title, talk venue, author, date, repo URL.
  Say: name, role at Red Hat, the one-sentence framing ("This is a research bench for closed-loop
       O-RAN remediation; today we walk one appearance of it as a 25 minute talk").
  Fallback: none, this is the opener.

### Slide 2 (01:00, 3 min). The "From" half. A day in multivendor diagnosis without the harness

  Show: a Splunk + Ericsson EMS + Nokia NetAct + Red Hat ACM + Grafana five-pane composite. PTP
        alarm visible in three panes with three different shapes.
  Say: PTP drifts on a customer site. Operator opens 5 tools, each shows partial truth. Open a
       ticket. 30+ minutes elapse before any single vendor confirms ownership. Site under SLA
       pressure. This is the day-2 status quo.
  Fallback: if the composite slide is missing, narrate the same scenario from text bullets.

### Slide 3 (04:00, 2 min). The 7-box architecture

  Show: `talk/architecture.png` (7-box macro).
  Say: four pieces in order, observation loop on the left, cognitive middle in the harness,
       routing decision splitting high and low, sandbox before any live action. Name the
       2+3+8+9 conjunction at the end of this slide as the lede for the rest of the talk.
  Fallback: the diagram is committed, no live render needed.

### Slide 4 (06:00, 4 min). Cognitive middle. Deterministic taxonomy plus LLM-on-ambiguous

  Show: `harness/taxonomy.yaml` snippet on screen plus `harness/routing-rules/contribution-1-routing-rule.yaml`.
  Say: 20 taxonomy entries grounded in O-RAN WG6 O-Cloud resource model. Deterministic lookup
       handles the great majority of faults. LLM reasoning invoked only on the residual
       ambiguous class. This is a real architectural commitment, not the typical "hand
       everything to the model" agentic-X demo.
  Fallback: read taxonomy.yaml from the live repo if the slide screenshot is wrong size.

### Slide 5 (10:00, 3 min). Routing decision. High side TMF921, low side O2 IMS plus CRDs

  Show: routing rule split view with sample TMF921 intent on the right, sample O2 IMS apply on
        the left. `scenarios/E_nic_firmware_update/companion_intent.json` for the right side.
  Say: high side belongs to the partner SMO, harness emits TMF921 and observes. Low side flows
       into the O-Cloud via O2 IMS, delivered by Metal3 BareMetalHost or HostFirmwareComponents,
       Machine Config Operator, or KMM. Name the dual-route pattern: scenario E fires BOTH
       because node firmware reboots require SMO coordination regardless of cell count.
  Fallback: walk the diagram on slide 3 again if the split-view rendering breaks.

### Slide 6 (13:00, 4 min). Demo

  Three independent demo paths exist, all reaching the same teaching moment. Pick one as primary
  and keep the others as fallbacks. Three captured runs from 2026-05-30 live under
  `talk/demo_logs/` as references.

  Path 1 (primary, safest). Prerecorded screencast of the trace timeline viewer at
        `:8095/dashboard/trace_view/index.html`. If scenario D was chosen, point at the
        software_ok vs hardware_anomaly divergence. If scenario E was chosen, point at the
        dual-route firing. Does not depend on live network or LLM.

  Path 2 (deterministic backup). Live walk of the trace timeline viewer at
        `:8095/dashboard/trace_view/index.html` against `bench/all` on the harness walker.
        Same content as the recording, but live. Does not require an LLM key.

  Path 3 (live conversational, the one that proves the harness IS interactive). Open the
        dashboard at `:8097` and click the **oh-my-tiny-oran** tab. Paste these two prompts in
        order; the chat captures from 2026-05-30 in `talk/demo_logs/` confirm both work
        end-to-end on real Docker against the real Anthropic key.

        Prompt 1: `/oran-discover:plan`
        Effect: the orchestrator skill walks all six discovery skills in one chat turn and
        produces a one-page pre-flight survey covering left loop, infra loop, service loop,
        taxonomy, and guardrails. About 30 seconds, ~10 tool calls.

        Prompt 2: "Now actually fire scenario E by calling the harness walker's
        /run/E_nic_firmware_update endpoint. Then re-check /oran-discover:metal3 and
        /oran-discover:smo to show me the dual-route really happened. Compare before and
        after."
        Effect: the agent fires the real scenario, observes the dual-route firing in the
        trace, and produces a structured before/after comparison naming the Metal3 firmware
        phases (Preparing through Updated), the Redfish task lifecycle, and the TMF921
        companion intent envelope. About 22 seconds, ~13 tool calls.

  Say: name both prompts on stage. The first survey teaches what the lab looks like at rest;
       the second exercise teaches what dual-route looks like in flight. Together they are the
       2+3+8+9 conjunction in motion.

  Fallback for Path 3 specifically: if the chat takes too long on stage or the Anthropic API
        rate-limits, switch to Path 1 (recording) without narration about the failure. Audience
        does not need to know.

  Fallback for the whole slide: still images of the viewer for each scenario stage. Read the
        verdict transitions from the slides. The talk does not depend on a live network.

### Slide 7 (17:00, 4 min). Trust loop. Digital Twin substrate, EvalOps, Killswitch

  Show: Digital Twin substrate diagram from `talk/architecture_zoom_cognitive.mmd`.
  Say: the trust layer that sits ON TOP of the three contributions. Twin is the floor, three
       activities run on it (EvalOps, Sandbox, Agentic Recoverability), Intelligence
       Augmentation is the explicit banner, Killswitch is the operator's reserve power
       (AT&T-reviewed per `talk/killswitch.md`). The Reversibility Profile is the seven-field
       contract between the harness and the human at decision time.
  Fallback: cite `talk/trust_loop.md` directly. Three minutes is tight; abridge if needed.

### Slide 8 (21:00, 2 min). Novelty positioning + repo handoff

  Show: the 2+3+8+9 conjunction (O2 GA&P + O2 IMS + Metal3 + MCO) plus the repo URL.
  Say: most agentic-RAN work either stops at the SMO boundary without a delivery story, or
       proposes a custom controller plane that side-steps O-RAN's own resource layering. The
       2+3+8+9 conjunction is what makes this concretely operationalizable. Then: this is one
       moment of a durable research bench; reviewers, point at github.com/dkypuros/oran-agent-harness.
  Fallback: the repo URL is the durable handoff. Even if the visual is wrong, the URL works.

### Slide 9 (23:00, 2 min). Q&A buffer

  Show: contact info + repo URL kept on screen during Q&A.
  Say: take questions. Lean on `talk/reviewer_faq.md` answers for common questions. Hand off
       deep questions to coffee break.

## Recovery callouts

- **If the demo recording fails to play**: the trace viewer at `5G_O-RAN_SIM/dashboard/trace_view/`
  is a static HTML file that runs from local disk. Open it from a USB stick if needed.
- **If the projector cannot show Mermaid diagrams**: every diagram has a committed `.png` next to
  the `.mmd` in `talk/`.
- **If asked a question outside the talk scope**: route to `talk/reviewer_faq.md` ("good
  question, the repo has an entry on that under talk/reviewer_faq.md, happy to walk it at the
  break").

## After the talk

- Twitter / LinkedIn / Slack / email post templates with the repo URL live in
  `talk/post_ngrg_handoff.md`.
- Anyone who asks for the slides is pointed at the repo, not sent the deck. The repo has more.
- A short follow-up note on the author's personal session log captures live audience reactions.
