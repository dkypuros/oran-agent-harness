# Contributing to oran-agent-harness

This repository is the public artifact set behind the O-RAN nGRG Workshop talk *From Multivendor
Diagnosis to Closed-Loop Remediation*. Contributions are scoped to the four extensible surfaces
described below. All contributions must preserve the citation-grounded character of the project: every
new YAML or JSON artifact under `harness/` or `scenarios/` carries a citation header tying it to an
upstream specification.

## Before you start

1. Read `README.md` for the project goals and repository map.
2. Read `harness/conformance.md` for the central citation index.
3. Run the verify gate locally:
   ```
   make install
   make verify
   ```
   You should see `10/10 checks passed, OVERALL: PASS`.
4. Read `docs/references.md` for the bibliography numbering scheme.

## Four extensible surfaces

### A. Adding a new walkthrough scenario

A walkthrough scenario lives under `scenarios/<short_name>/` and consists of exactly five fixture
files plus a corresponding row in `harness/conformance.md`.

Required fixtures (citation header on every JSON):

```
scenarios/<short_name>/
  fault_payload.json         validates against harness/schemas/FaultPayload.json
  rca.json                   validates against harness/schemas/RCA.json
  remediation_proposal.json  validates against harness/schemas/RemediationProposal.json
  remediation.yaml           a real MachineConfig, KMM Module, or other O-Cloud CR
  audit_event.json           validates against harness/schemas/AuditEvent.json
```

Steps:

1. Copy an existing scenario folder, e.g. `cp -r scenarios/A_fw_lldp_agent scenarios/B_my_new_fault`.
2. Update every `_conforms_to` block in the JSON fixtures with the correct upstream section.
3. Update the `# Conforms to:` and `# Bibliography ref:` headers in the YAML remediation file.
4. Add a row to `harness/conformance.md` under the `## Scenario artifacts` table for each of the
   five new files.
5. If the new scenario exercises a taxonomy entry not already present, add it to `harness/taxonomy.yaml`
   and update the conformance file count expectations in `scripts/verify.py`.
6. Run `make verify`. You should still see `10/10 checks passed`.
7. Open a PR using the template at `.github/PULL_REQUEST_TEMPLATE.md`. The PR title must reference
   the GitHub issue it closes.

### B. Adding a new OMC skill

OMC skill bundles live under `omc-skills/<domain>/`. The `o-ran` bundle is the reference
operationalization of the harness contracts.

Steps:

1. Create a new directory `omc-skills/<your_domain>/`.
2. Each skill is a single markdown file with a YAML frontmatter block declaring the skill name,
   description, and the contracts it reads from `harness/`.
3. Add a `README.md` at the bundle root that lists every skill, what input contract it consumes, and
   what output it produces.
4. Add a `conformance.md` mapping each skill to the harness artifact it consumes.
5. No verify-gate changes needed; OMC skill bundles are not scanned by the conformance check.

### C. Adding a new harness component

Every authored YAML or JSON artifact under `harness/` must:

1. Carry a citation header (`# Conforms to:` plus `# Bibliography ref:` for YAML; top-level
   `_conforms_to` object for JSON).
2. Have a row in `harness/conformance.md` under the `## Harness artifacts` table, with columns
   `File`, `Document family`, `Section`, `Version`, `Bibliography ref`.
3. Bibliography reference numbers must already exist in `docs/references.md`. If you cite a new
   upstream document, append it to `docs/references.md` first.
4. Update the file-count expectations in `scripts/verify.py` if you grow the harness beyond its
   current expected count.

Run `make verify` after every new artifact. The bidirectional conformance check ensures no file is
missing from the table and no table row points at a missing file.

### D. Adding a new diagram

The talk diagrams live under `talk/`. Each is a Mermaid source file (`.mmd`) plus a rendered PNG.

Steps:

1. Author the Mermaid source as `talk/<name>.mmd`. No em dashes (U+2014) anywhere. Use commas,
   periods, or parentheses instead. The verify gate has an em-dash audit that fails on any.
2. Render to PNG at appropriate resolution (the macro diagram is roughly 1600 px wide; the detail
   reference `architecture_full.png` is roughly 12000 px wide).
3. Add a row to the diagram table in `talk/architecture_narrative.md` describing what the diagram
   shows and when a reader should consult it.
4. If the diagram introduces a new contract or component, add a row in `harness/conformance.md` as well.

## Hard rules

- **No em dashes.** The em dash character (U+2014) is forbidden in any tracked file. Use commas,
  periods, or parentheses. The verify gate audits for this on every check.
- **No Co-Authored-By trailers on commits.** Authorship attribution is by the human contributor only.
- **No `git add -A` or `git add .`.** Stage specific paths only. This protects against accidental
  inclusion of `.local/`, `python_demo/`, or environment files.
- **Citation discipline is non-negotiable.** A new file in `harness/` or `scenarios/` without a
  citation header is incomplete and the verify gate will fail.
- **One PR closes one issue.** Use `Closes #N` syntax in the commit message so the issue auto-closes
  on merge.
- **The verify gate is the gate.** Open PRs only when `make verify` exits zero locally. The GitHub
  Actions workflow at `.github/workflows/verify.yml` runs the same gate on every PR and push.

## Reporting issues

Open issues at https://github.com/dkypuros/oran-agent-harness/issues. For new scenarios, use the
issue template at `.github/ISSUE_TEMPLATE/new-scenario.md`. For other contributions, describe the
upstream specification or contract you propose to add or change.

## License

By contributing you agree that your contributions will be licensed under the Apache License 2.0
(see `LICENSE`).
