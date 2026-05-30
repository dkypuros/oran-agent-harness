# Pull Request

## Summary

<!-- One paragraph: what does this PR change and why -->

## Issue

<!-- Reference the GitHub issue this PR closes. Use "Closes #N" syntax so the issue auto-closes on merge. -->

Closes #

## Type of change

- [ ] New walkthrough scenario (under `scenarios/`)
- [ ] New OMC skill (under `omc-skills/<domain>/`)
- [ ] New harness component (under `harness/`)
- [ ] New or updated diagram (under `talk/`)
- [ ] Documentation only
- [ ] Tooling, CI, or build (structural)
- [ ] Other (describe below)

## Verify-gate checklist

- [ ] `make verify` exits 0 locally (10/10 PASS)
- [ ] Every new YAML carries a `# Conforms to:` plus `# Bibliography ref:` header
- [ ] Every new JSON carries a top-level `_conforms_to` object
- [ ] Every new file under `harness/` or `scenarios/` has a row in `harness/conformance.md`
- [ ] No em dashes (U+2014) anywhere in changed files
- [ ] No `Co-Authored-By` trailers on commits
- [ ] Commit messages stage specific paths only (no `git add -A` or `git add .`)
- [ ] PR title references the GitHub issue (e.g. "Issue #N: short description")

## Bibliography references

<!-- If this PR cites a new upstream document, list the new bibliography ref number and URL.
     Confirm it has been appended to docs/references.md. -->

- [ ] No new bibliography references, OR
- [ ] New refs appended to `docs/references.md` (list the new numbers below)

## Testing

<!-- What did you run locally to confirm this works? -->

- [ ] `make install`
- [ ] `make verify`
- [ ] `make demo` (when scenario or runtime is touched)
- [ ] Other (describe)

## Risk and rollout

<!-- Anything reviewers should know about scope, ordering with other PRs, or potential surprises. -->
