# Draft scientific papers

Five short scientific drafts derived from the O-RAN Agent Harness, drafted
2026-05-31 through 2026-06-02 in preparation for the nGRG Workshop talk
(Seattle, 2026-06-04) and for subsequent submission to a relevant venue.
These are author drafts, not final submissions.

| File | Pages | Thesis |
|------|------:|--------|
| `0_paper_intelligence_augmentation.tex` -> `0_paper_intelligence_augmentation.pdf` | 5 | Human-governed intelligence augmentation overview for the shared spine: observation -> RCA -> RemediationProposal -> schema validation -> sandbox/five-subcheck policy guardrail -> human challenge/co-authorization -> TMF688-shaped audit -> O2 IMS/TMF921 standards-shaped dispatch -> native reconciler execution |
| `1_paper_architecture.tex` -> `1_paper_architecture.pdf` | 7 | Closed-Loop Day-2 remediation runtime architecture grounded in the O2-IMS-to-operator-CRD bridge (O-RAN O2 GA&P + O2 IMS + Metal3 + MCO) |
| `2_paper_standards_bridges.tex` -> `2_paper_standards_bridges.pdf` | 6 | Six v0 bridges plus one prospective R1 seam composing O-RAN, TM Forum, IEEE, DMTF, and Kubernetes-native contracts without proposing a replacement standards body |
| `3_paper_research_harness.tex` -> `3_paper_research_harness.pdf` | 5 | Fixture-driven research harness methodology with a verify gate producing binary pass/fail any reviewer can reproduce against a cited repository state, with full ten-check reproduction requiring jsonschema |
| `4_paper_structural_communication.tex` -> `4_paper_structural_communication.pdf` | 5 | Structural demarcation pattern for containing AI nondeterminism with schema-validated artifacts, deterministic gates, standards-shaped envelopes, and native reconciler delegation |

All five papers cite from a shared bibliography (`refs.bib`) sourced from
`docs/references.md`. The bibliography is comprehensive (52 entries spanning
O-RAN Alliance, TM Forum, IEEE, ITU-T, DMTF, CNCF, Kubernetes SIGs, plus
project references for Metal3, MCO, KMM, MCP, linuxptp, and the prior
multivendor diagnostic publication).

## Contribution matrix

| Paper | Unique claim | Proof artifact | Out-of-scope |
|-------|--------------|----------------|--------------|
| Paper 0 | Human-governed intelligence augmentation is the correct control frame for closed-loop O-RAN Day-2 remediation. | Shared spine connecting observation, RCA, proposal, validation, guardrails, audit, dispatch, and reconciler execution. | New standards interface, autonomous production control, or live O2/SMO interoperability. |
| Paper 1 | O2 IMS-shaped infrastructure dispatch can bridge to Kubernetes-native operator contracts without direct agent write authority. | O2-IMS-to-operator-CRD bridge pattern and CRD-shaped fixtures. | Production O-Cloud Manager deployment, live cluster mutation, or vendor-certified O2 IMS conformance. |
| Paper 2 | Existing O-RAN, TM Forum, IEEE, DMTF, and Kubernetes-native contracts can be composed without replacement. | Standards-lineage bridge map, six v0 bridges, and one prospective R1 seam. | New standards-body proposals or complete normative conformance testing. |
| Paper 3 | Reviewers can falsify covered v0 claims through fixture replay and schema-backed verification. | Committed scenarios, JSON Schemas, standards-lineage index, and verify gate. | Live production deployment, exhaustive taxonomy coverage, or LLM-dependent proof. |
| Paper 4 | AI nondeterminism can be contained by structural communication through deterministic, schema-validated artifacts. | Schema gate, five-subcheck policy guardrail, TMF688/TMF921/O2 IMS-shaped envelopes, and native reconciler delegation. | Raw LLM-generated configuration, direct hardware calls, live Redfish writes, or standards-body schema conformance claims. |

## Author

David Kypuros, Red Hat. Sole author. Apache-2.0.

## Compiling the PDFs

The PDFs in this directory are pre-compiled from the `.tex` sources. To
regenerate any of them from source after edits:

```bash
cd draft_papers
pdflatex 1_paper_architecture.tex
bibtex 1_paper_architecture
pdflatex 1_paper_architecture.tex
pdflatex 1_paper_architecture.tex
```

Repeat for `0_paper_intelligence_augmentation`, `2_paper_standards_bridges`,
`3_paper_research_harness`, and `4_paper_structural_communication`. The
double `pdflatex` pass after `bibtex` is standard practice to resolve
cross-references.

Requirements: a TeX Live distribution (MacTeX on macOS, TeX Live on Linux,
MiKTeX on Windows). The papers use the standard `article` class with the
`twocolumn` option and `plain` bibliography style; no external classes
beyond core LaTeX are required.

## Honest scope on the drafts

These are author drafts, not peer-reviewed and not yet submitted. The thesis
statements are intended to be falsifiable. Each paper includes or preserves an
honest-scope section acknowledging v0 limits: stub-driven runtime, no live
production deployment, no live O2 IMS/TMF921/Redfish interoperability, no
multi-cluster scale, and schemas that are harness-authored approximations rather
than standards-body-published conformance suites.

The repository's `scripts/verify.py` reports the v0 implementation state
the papers describe. Any reviewer who wants to falsify a covered claim should
run the verify gate against the repository state cited in the paper. The v0
claims are proposal-shape, dispatch-shape, guardrail-shape, audit-shape, and
reversibility-profile claims, not live production interop claims.

## Files in this directory

```
draft_papers/
  README.md                                this file
  refs.bib                                 shared 52-entry BibTeX bibliography
  prd.json                                 story tracker for paper drafting
  0_paper_intelligence_augmentation.tex    Paper 0 source
  0_paper_intelligence_augmentation.pdf    Paper 0 compiled
  1_paper_architecture.tex                 Paper 1 source
  1_paper_architecture.pdf                 Paper 1 compiled
  2_paper_standards_bridges.tex            Paper 2 source
  2_paper_standards_bridges.pdf            Paper 2 compiled
  3_paper_research_harness.tex             Paper 3 source
  3_paper_research_harness.pdf             Paper 3 compiled
  4_paper_structural_communication.tex     Paper 4 source
  4_paper_structural_communication.pdf     Paper 4 compiled
```

Build artifacts (`.aux`, `.log`, `.out`, `.bbl`, `.blg`, etc.) are
gitignored and regenerated on compile.
