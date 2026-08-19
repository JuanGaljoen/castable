# 9. Drive spec repair from the castability gate's own violations, not a restated rule table

- **Status:** Accepted
- **Date:** 2026-08-16
- **Context ticket:** RNG-32 (vision estimates fields independently, producing specs the casting
  gate rejects)

## Context

`ClassifyResult.to_spec()` clamped each vision estimate to its own valid range but never checked
a field against its siblings, so a schema-valid spec could still be physically impossible — a
5.2mm stone in a 3.0mm head. The ticket's own scope note asked to "audit the schema for other
dimension pairs with a physical containment or clearance relationship" and fix each.

The obvious reading of that sentence is a table: enumerate the containment pairs
(stone height/setting height, halo gap/accent diameter, accent height/setting height, …) and
write a coercion for each, in `classify.py`, next to the clamping it already does.

That table was not written. `validate_castability` (`ringcad/ringspec/castability.py`) already
*is* that audit — nine rules, each returning a `Violation` that names the offending `field`, the
`limit_mm` it must clear, and the `actual_mm` it's at. Restating those rules as a second table in
`classify.py` would recreate exactly the drift ADR-0002 is about: a check and a builder (here, a
check and a *repairer*) reading the same fact from two places, which stay in sync only by
discipline. RNG-19 alone added three gate rules (`_halo_web`, `stone_curvature`,
`side_stone_channel_fit`/`_floor`) after the castability module existed; a parallel table would
have needed hand-editing for every one.

## Decision

**`ringcad/ringspec/coherence.py`'s `make_coherent` repairs whatever `validate_castability`
itself flags, keyed on `Violation.code`, not on a hand-maintained list of field pairs.** A repair
table entry reads the field to move and the value it must reach off the `Violation`, not off a
restated constant. A gate rule added later is covered here for free — no second edit — down to
the one exception (a rule with no repairable move, e.g. one that needs a structural change) which
degrades to the fallback chain rather than being silently unrepairable.

This is a general move, not RNG-32-specific: **whenever a validator and a repairer both need to
agree on "what wrong looks like," the repairer should consume the validator's own structured
output, not re-derive the same fact.** The alternative (a parallel table) looks simpler on day
one and is the one that drifts.

## Consequence found along the way: repair alone cannot promise convergence

Driving repair off arbitrary gate output means the repair function inherits whatever the gate can
express, including relationships between violations that a hand-picked list of "pairs" would
never have surfaced. One turned up during Verify's fuzz testing: `min_prong_tip` wants
`stone_diameter` **above** some size for the given prong count; `stone_exceeds_bore` wants it
**below** a smaller one for the given `inner_diameter`/`length_ratio`. When both fire on the same
spec, no value of `stone_diameter` satisfies both — the repair loop correctly oscillates rather
than converging, and terminates at its pass budget (`MAX_PASSES`) by design rather than looping
forever.

**`make_coherent` alone therefore only guarantees termination, not convergence.** The actual
castability guarantee for a user-facing spec comes from the three-tier fallback chain one level
up (`ClassifyResult._coherent_spec`: detected archetype repaired → solitaire from the same shared
estimates repaired → pure-default solitaire, the last tier proven castable by construction). Any
future caller of `make_coherent` — the function is public, on `ringcad.ringspec`, and documented
as reusable beyond this ticket — must re-check `is_castable` on the result and have its own
fallback; the function's docstring says so explicitly. A 5000-sample fuzz of the real production
path (`ClassifyResult.to_spec()` across the full schema-legal input space) found this specific
oscillation unreachable there today, because `_stone_shape()` normalises `length_ratio` to 1.0 on
every non-oval assembly — but that is a property of `classify.py`'s current normalisation, not of
`make_coherent`, and should not be assumed by a future caller that skips it.
