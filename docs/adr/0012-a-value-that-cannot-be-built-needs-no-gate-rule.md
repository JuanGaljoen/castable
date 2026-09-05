# 12. A value that cannot be built needs no gate rule to reject it

- **Status:** Accepted
- **Date:** 2026-09-05
- **Context ticket:** RNG-25 (shank profile family) CP1/CP3.

## Context

RNG-25's ticket asked for an "enforced minimum edge width" on the knife-edge
shank profile, naming it as a castability rule alongside the existing
`min_wall`/`min_prong_tip` checks in `ringcad/ringspec/castability.py` — a
new `Violation` code, checked pre-geometry, that would reject a knife edge
whose ridge came out thinner than the casting floor. Understand even worked
through who the repair should target if vision suggested a too-thin knife
edge (RNG-32's `make_coherent` machinery, ADR-0009).

Building the knife-edge cross-section as a genuine two-slope ridge showed a
simpler option: instead of computing how thin the apex WOULD BE and rejecting
it after the fact, size the flat crown itself so it is always exactly
`MIN_WALL_MM` wide, for every `band_width` in range
(`sections.knife_edge_apex_fraction = min(1, MIN_WALL_MM / band_width)`). The
apex cannot be built too thin, because "too thin" is not a value the
construction can produce.

## Decision

No `min_edge_width` violation code was added. The apex floor is enforced by
construction in `ringcad/ringspec/sections.py`, not by a check in
`castability.py`. `make_coherent` needed no new repair path either — there is
no violation for it to react to.

**The general move:** before adding a castability rule for a new failure
mode, ask whether the unsafe value can instead be made unreachable by the
parametrisation itself. A gate rule is validate-then-reject; this is
"there is no invalid input to reject." The second is strictly stronger (it
cannot regress if someone edits an unrelated part of the builder and forgets
the check) and needs no test of the rejection path, only a test that the
construction holds its invariant — which `tests/test_sections.py`'s apex
tests already are.

This is not a new idea in this codebase — ADR-0008 ("model the negative, not
the setting") is the same move at a different scale, and RNG-17's whole
"castable by construction" framing is this principle as a project-wide bar.
This ADR exists because the move nearly didn't happen: the ticket, and the
Understand interview, had both already reasoned all the way through to a
gate-rule design (including which sibling field a repair should move) before
CP2's actual geometry work showed the rule was unnecessary. **Reasoning
about a gate rule in the abstract, before anything is built, tends to assume
a gate rule is the answer.**

## Consequences

- When scoping a new castability concern, hold the "can this be made
  unreachable by construction" question open through Design, not just at
  Forge — Understand's own repair-victim discussion for this ticket is now
  moot, recorded in `specs/RNG-25.md` as a decision that turned out to need
  no code.
- A future cross-section profile that CAN'T be made safe by construction
  (if one exists) should get a real gate rule, following ADR-0009's "repair
  from the gate's own violations" pattern — this ADR is not "gate rules are
  wrong," it's "check whether you need one before assuming you do."
