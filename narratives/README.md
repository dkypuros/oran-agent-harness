# Narratives

Long-form per-audience cuts of the research bench. Each narrative is self-contained and stands
alone if a reader lands on it directly. Citations anchor to harness contracts and bibliography
refs at file plus line where applicable. The nGRG talk under `../talk/` is one specific
appearance of the bench; these narratives carry the broader teaching weight.

## Index

| Narrative                                  | Audience                                    | Status            |
|--------------------------------------------|---------------------------------------------|-------------------|
| `operator_day_without_harness.md`          | The "From" half of the talk title made concrete. Operations engineers, SREs, day-2 leads. | Landed |
| `trust_loop_framing.md`                    | Trust layer above the three core contributions. Architects, working group reviewers. | Landed |
| `standards_conformance_walkthrough.md`     | The citation pyramid as the artifact. Working-group chairs, academic reviewers. | Planned |
| `multivendor_interop_narrative.md`         | The partner SMO contracts, why TMF921 carries the high side, why O2 IMS carries the low side. Vendor PMs, integration leads. | Planned |
| `trajectory_what_day_3_looks_like.md`      | Post-Day-2 roadmap, multi-site coordination, cross-vendor shared learning. Workshop reviewers, funding bodies. | Planned |
| `post_ngrg_handoff.md`                     | Public-facing handoff template for social channels after the talk. | Planned |

## Reading order if you have time

1. `operator_day_without_harness.md`, sets the problem.
2. `trust_loop_framing.md`, sets the trust posture.
3. The nGRG talk narrative under `../talk/architecture_narrative.md`, the architecture.
4. The remaining narratives as they land.

## Authoring notes (for contributors)

- Each narrative is self-contained. A reader landing on one directly should not need to read
  other narratives to follow it.
- Citations anchor to file plus line whenever possible. Bibliography refs go through
  `../docs/references.md`. The verify gate em-dash check applies to every file in this tree.
- Voice is plain prose, no marketing copy. Working-group reviewers and senior engineers are the
  default reader.
- Filenames lowercase, dates in ordinal format with day brackets when used.
