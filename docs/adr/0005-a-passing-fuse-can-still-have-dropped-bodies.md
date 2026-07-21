# 5. A fuse that "passes" can still have silently dropped bodies — assert volume, not just watertightness

- **Status:** Accepted
- **Date:** 2026-07-21
- **Context ticket:** RNG-23 CP2 (oval centre stone); refines
  `0001-fuse-leaves-not-compounds.md`

## Context

RNG-23 CP2 made `prong_setting` build claws at the stone's girdle points instead of at a
fixed radius rotated into place, so that an elliptical girdle could vary the reach per
claw. One configuration then produced a setting with **no claws at all**: a 6-prong oval at
`length_ratio` 1.3 returned volume **5.65** where 39.02 was expected — the bare gallery peg.

What makes this worth an ADR is how it presented. OCCT did **not** raise. The result was a
single valid solid. `is_watertight` was true. `non_manifold_edges` was zero. Every
castability floor held, because the metal that would have violated them no longer existed.
The only reason it was caught is that the orphaned seat had nothing left to fuse to, pushing
`body_count` to 2 — a second-order symptom of the real failure.

ADR-0001 already established that OCCT booleans are fragile and prescribed the mitigation:
*fuse leaf solids in ONE general fuse; never pairwise-fuse pre-fused bodies.* The code that
failed here **was already following that rule** — a single general fuse over 43 leaves (four
node spheres and three segment bodies per claw, plus the peg). So rule 1 is necessary but
not sufficient: a single general fuse over *many* leaves can also drop bodies once the
leaves stop being congruent copies of one another.

The distinguishing factor was regularity. Under the old construction every claw was the
same solid rotated, so all 43 leaves met at congruent angles. On an ellipse each claw sits
at a different radius and a different relative angle to its neighbours, and that irregularity
is what tipped the boolean over.

## Decision

**1. Group leaves into semantic sub-bodies, then run ONE general fuse over the groups.**

`prong_setting` now pre-fuses each claw (7 leaves) into a single body and then does one
general fuse of `peg + claws`. This is *not* a contradiction of ADR-0001: that ADR
explicitly sanctions "a module's own internal pre-fusion", and forbids the *pairwise*
accumulation (`out = out.fuse(next)` in a loop) which is deliberately avoided here. Both
orderings were measured and give identical volumes; the single general fuse is chosen
because it keeps to ADR-0001.

**2. Assert volume or a positive lower bound on it — never watertightness alone.**

Watertightness, manifold-edge count and body count can all be satisfied by geometry that has
quietly lost most of its mass. Any test that guards a fuse must pin something proportional to
the metal actually present. `body_count == 1` is a useful fast signal but, as here, can pass
while a body is missing (the drop only became visible because a *separate* module was left
orphaned).

## Consequences

- Module builders that fuse many small primitives should group them by the feature a human
  would name (one claw, one accent setting, one rail) before the final general fuse. Groups
  also localise the blast radius when a boolean does fail.
- Geometry tests should include at least one volume-bearing assertion per archetype.
  `tests/test_oval_geometry.py` asserts `body_count == 1`, which caught this case only by
  luck; a volume floor would have named it directly.
- **Known signal, deliberately accepted:** the new construction emits eight
  `UserWarning: Boolean operation unable to clean` from build123d on round configurations
  (CP1 emitted none). The affected solids are still single-body, watertight, zero
  non-manifold, and within 2e-7 of their previous volume, so the warning reflects OCCT
  skipping its cleanup pass rather than producing wrong geometry. Given this ADR's own
  subject, it is recorded rather than dismissed: if manifold failures ever appear in the
  claw region, this warning is the first place to look.
- Round `prong_setting` output is no longer bit-identical to pre-RNG-23 (~2e-7 relative,
  from `cos`/`sin` placement replacing a rotation matrix). The seat's `Torus` path *is*
  exactly preserved. Restoring exact parity would require branching on stone shape inside
  `prong_setting`, defeating the outline abstraction; the parity tests pass and the
  looser criterion was adopted knowingly (see `specs/RNG-23.md`).
