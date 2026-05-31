# Draft scientific papers

Three short scientific drafts derived from the O-RAN Agent Harness, drafted
2026-05-31 in preparation for the nGRG Workshop talk (Seattle, 2026-06-04)
and for subsequent submission to a relevant venue. These are author drafts,
not final submissions.

| File | Pages | Thesis |
|------|------:|--------|
| `paper_architecture.tex` -> `paper_architecture.pdf` | 5 | Closed-Loop Day-2 remediation architecture grounded in the 2+3+8+9 conjunction (O-RAN O2 GA&P + O2 IMS + Metal3 + MCO) |
| `paper_standards_bridges.tex` -> `paper_standards_bridges.pdf` | 5 | Seven named bridges composing O-RAN, TM Forum, IEEE, DMTF, and Kubernetes-native contracts without inventing parallel standards |
| `paper_research_harness.tex` -> `paper_research_harness.pdf` | 4 | Fixture-driven research harness methodology with a 10-check verify gate producing binary pass/fail any reviewer can reproduce |

All three papers cite from a shared bibliography (`refs.bib`) sourced from
`docs/references.md`. The bibliography is comprehensive (52 entries spanning
O-RAN Alliance, TM Forum, IEEE, ITU-T, DMTF, CNCF, Kubernetes SIGs, plus
project references for Metal3, MCO, KMM, MCP, linuxptp, and the prior
multivendor diagnostic publication).

## Author

David Kypuros, Red Hat. Sole author. Apache-2.0.

## Compiling the PDFs

The PDFs in this directory are pre-compiled from the `.tex` sources. To
regenerate any of them from source after edits:

```bash
cd draft_papers
pdflatex paper_architecture.tex
bibtex paper_architecture
pdflatex paper_architecture.tex
pdflatex paper_architecture.tex
```

Repeat for `paper_standards_bridges` and `paper_research_harness`. The
double `pdflatex` pass after `bibtex` is standard practice to resolve
cross-references.

Requirements: a TeX Live distribution (MacTeX on macOS, TeX Live on Linux,
MiKTeX on Windows). The papers use the standard `article` class with the
`twocolumn` option and `plain` bibliography style; no external classes
beyond core LaTeX are required.

## Honest scope on the drafts

These are author drafts, not peer-reviewed and not yet submitted. The thesis
statements are intended to be falsifiable. Each paper includes an
honest-scope section acknowledging v0 limits (stub-driven runtime, no
production deployment, no multi-cluster scale, schemas are
harness-authored approximations not standards-body-published shapes).

The repository's `scripts/verify.py` reports the v0 implementation state
the papers describe. Any reviewer who wants to falsify a claim should run
the verify gate against the repository at the commit SHA cited in the paper.

## Files in this directory

```
draft_papers/
  README.md                              this file
  refs.bib                               shared 52-entry BibTeX bibliography
  prd.json                               story tracker for paper drafting
  paper_architecture.tex                 Paper 1 source
  paper_architecture.pdf                 Paper 1 compiled
  paper_standards_bridges.tex            Paper 2 source
  paper_standards_bridges.pdf            Paper 2 compiled
  paper_research_harness.tex             Paper 3 source
  paper_research_harness.pdf             Paper 3 compiled
```

Build artifacts (`.aux`, `.log`, `.out`, `.bbl`, `.blg`, etc.) are
gitignored and regenerated on compile.
