---
title: "Standards Conformance Walkthrough: the citation pyramid as the artifact"
author: David Kypuros
license: Apache-2.0
status: how the bench proves its claims without asking you to take its word
audience: O-RAN working-group chairs, academic reviewers, anyone who has to trust this work in print
---

# Standards Conformance Walkthrough

Most agentic-RAN work asks you to trust the architecture. This bench asks you to verify it. Three
layers of verification stack on top of each other: a bibliography that does not move, a narrative
that anchors at file plus line, and a runnable gate that returns a falsifiable yes or no on the
structural claims. This narrative walks all three.

A reader who reaches the end of this document will know exactly how to falsify the bench's
claims, which is the proper test of whether to trust them.

## Layer 1: the bibliography that does not move

The bibliography lives at `../docs/references.md`. 52 numbered AMA-style refs, every entry with a
stable URL or specification document number, every entry with an HTML id anchor (`<a id="ref-N">`)
so the rest of the bench can deep-link.

Coverage spans:

  - **O-RAN Alliance**: refs 1-6, 31, 35, 48, 49 (Architecture, O2, O-Cloud Notification API, WG1
    Decoupled SMO, WG10 O1)
  - **Kubernetes-native delivery**: refs 7-10 (Metal3, MCO, KMM)
  - **TM Forum**: refs 18-22 (TMF688, TMF921, TMF GB922 SID, ODA Canvas)
  - **DMTF**: ref 46 (Redfish DSP0266)
  - **IEEE / ITU-T**: refs 26, 44 (1588-2019 PTP, G.8275.1 telecom profile)
  - **CNCF**: ref 30 (CloudEvents 1.0)
  - **Operating systems**: refs 27, 28, 29 (linuxptp, Red Hat PTP Operator, cloud-event-proxy)

The bibliography is the only place in the bench where authority is borrowed. Everything else
quotes it.

## Layer 2: the narrative anchored at file plus line

Every claim in the talk's architecture narrative resolves to a file path. Most resolve to a
specific section of a specific file. This is the discipline the talk speaker confirmed on
2026-05-16 against the V15 plan: anchor golden code by path plus line, enumerate verified
infrastructure as a file plus line plus role table.

Open `../talk/architecture_narrative.md`. Every paragraph contains links like
`[ref 28](../docs/references.md#ref-28)`. The links resolve to the bibliography's HTML anchors,
which resolve to a URL or specification number. Three hops, every hop verifiable.

The same discipline applies to `../harness/conformance.md`. This file is the central citation
index for the harness. It tells you which harness artifact cites which bibliography ref. 43 rows
at the time of writing. The verify gate's `conformance_complete` check enforces bidirectional
consistency: every taxonomy entry, schema, and routing rule that cites a ref appears in the
conformance table, and every conformance row points at a file that actually exists.

That bidirectional check is what makes the citation chain non-rotting. If you delete a harness
file but forget to remove its conformance row, the verify gate fails. If you add a new file with
a ref citation but forget to register it in conformance.md, the verify gate fails. Either way
the reviewer sees a 9/10 instead of 10/10 and knows to look.

## Layer 3: the runnable gate

`../scripts/verify.py` runs 10 structural checks against the bench:

  1. JSON parse over every committed JSON file (schemas, fixtures, audit events)
  2. YAML parse over every committed YAML file (taxonomy, guardrails, routing rules)
  3. `conformance.md` bidirectional check (described above, 43 rows scanned)
  4. Em dash audit over the public tree (em dashes are an "AI tell"; the bench rejects them)
  5. Leakage guard via `git ls-files` (no `.local/`, no `.env`, no `*.pdf` in the public tree)
  6. README structure check (line count cap, three-goals strings present in the top 60 lines)
  7. File counts (`harness/` at 26 files, `omc-skills/o-ran/` at 6 markdown files)
  8. Schema validation (every committed `scenarios/*/*.json` validates against
     `harness/schemas/*.json`)
  9. Runtime walker end-to-end (the deterministic Python runtime in `harness/runtime/` walks each
     of the four scenarios and produces an audit event identical to the committed expectation)
  10. The summary line

Running `python scripts/verify.py` returns `SUMMARY: 10/10 checks passed, OVERALL: PASS` on a
healthy commit. Any single failure surfaces with the specific row that broke. CI runs the same
gate on every push to main (`../.github/workflows/verify.yml`).

The walker end-to-end check in slot 9 is the heaviest. It loads each scenario's
`fault_payload.json`, runs it through the real `Router` and `Guardrail` Python classes (not
stubs), and compares the resulting `audit_event.json` byte-for-byte against the committed
expectation. If the runtime drifts, the gate fails. If a scenario fixture drifts, the gate
fails. The deterministic runtime IS the verification.

## Where the LLM lives in the verification story

The bench's LLM-ambiguity-resolution path is explicitly excluded from the deterministic verify
gate, because LLM output is nondeterministic and would fail a byte-for-byte comparison. Instead,
the LLM path has its own test (`../tests/test_runtime.py::test_route_ambiguous_with_llm_mode_live`)
that runs only when `ORAN_LLM_MODE=live` is set in the environment, and asserts only that the
LLM responds with a valid taxonomy entry id. The bench separates deterministic claims (which
must reproduce) from probabilistic claims (which must validate against a contract).

This separation matters for reviewers: when a reviewer asks "what does the verify gate prove?"
the answer is precise. It proves that the deterministic taxonomy, routing rule, guardrail, and
schema layer reproduce identical outputs on identical inputs. It does NOT prove that the LLM
disambiguator produces consistent answers on the ambiguous class; that is what EvalOps measures
over time, not what the verify gate measures at commit time.

## How a reviewer can falsify any claim

The three-layer structure means a reviewer can falsify any individual claim in the bench by
following one of three paths.

  1. **Bibliography falsification.** Click any `[ref N]` link in the narrative. The link resolves
     to a bibliography entry with a URL or specification number. If the URL is dead, the spec
     does not say what we claim, or the section number we cited is wrong, the citation is
     falsified.
  2. **Conformance falsification.** Open `../harness/conformance.md`. Pick any row. Verify the
     file path resolves to a committed artifact. Verify the cited bibliography ref says what the
     row description claims. If either fails, the citation chain is broken.
  3. **Runtime falsification.** Clone the repo. Run `python scripts/verify.py`. If the gate
     reports anything less than 10/10 PASS, the bench is currently broken. If the gate reports
     10/10 PASS but a scenario walks to an audit event the reviewer disagrees with, the
     reviewer can edit the audit event's expected fields and rerun the gate to see exactly
     which expectation the runtime contradicts.

Three falsification paths is more than most published research provides. The bench is
deliberately built so that "I do not believe this" can be turned into "here is the specific
field, in the specific file, that does not hold." That is what citation discipline buys at the
end.

## What this layer is not

It is not peer-reviewed. The bibliography includes upstream open-source projects (Metal3, MCO,
KMM, linuxptp, cloud-event-proxy) alongside O-RAN, TM Forum, DMTF, IEEE, ITU-T, and CNCF
specifications. Some refs are formal standards; some are stable upstream code. The bench treats
both as authority for what they each are: standards define the contract, upstream code defines
the delivery mechanism.

It is not a guarantee of completeness. The bench's structural claims are gated. The substance of
the talk (the architecture, the novelty claim, the trust loop) is reviewed by senior engineers
and the talk speaker's collaborators, not by the verify gate.

It is also not a substitute for empirical validation. The walker end-to-end check proves the
runtime is consistent with its own committed expectations. Whether those expectations match what
a production O-Cloud actually does is the work of the deployment, not the work of the gate.

## Summary for a reviewer

If you are a working-group chair or academic reviewer and you have 15 minutes:

  1. Read this file (you are here).
  2. Open `../docs/references.md` and confirm the bibliography is shaped the way a reviewer
     expects (AMA-style, URLs accessible, accessed-on dates present).
  3. Open `../harness/conformance.md` and trace one row top-to-bottom: cited ref to bibliography
     entry, file path to committed file, file content to the section the row references.
  4. From the repo root, run `python scripts/verify.py` and read the summary.

If all three pass and the verify gate reports 10/10 PASS, the bench's structural claims hold up
to scrutiny. The architecture claims (the 2+3+8+9 conjunction, the deterministic-taxonomy-first
routing decision, the trust loop) sit on top of that structure but are not themselves verified
by the gate. They are verified by the reader's judgment of the narrative.

The pyramid is the artifact. Trust the structure, then evaluate the substance.
