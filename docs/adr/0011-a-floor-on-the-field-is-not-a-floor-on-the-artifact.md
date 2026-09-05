# 11. A floor checked on the field is not a floor checked on the artifact

- **Status:** Accepted
- **Date:** 2026-09-05
- **Context ticket:** RNG-25 (shank profile family), found at Design while
  scoping the knife-edge castability rule.

## Context

`_min_wall` (`ringcad/ringspec/castability.py`) has always checked
`shank.band_thickness >= MIN_WALL_MM` and treated that as "the band's wall
clears the casting floor." It does not, and never has: `_band_section`
(`ringcad/geometry/_common.py`) builds the shank's cross-section as a full
`Ellipse(th/2, w/2)`, whose thickness is `sqrt(1-s^2) * th` across the band —
exactly `th` at the centreline, but tapering smoothly to **zero** at the
band's own edges (`s = +-1`). Every ring this app has ever generated has
knife-thin edges on its band, on both sides, all the way round.

This is not a manufacturing defect — `docs/reference/band-profiles.png` (a
real trade cross-section chart, added for RNG-25) draws exactly this shape
under the name "Court," and it is a normal, castable, everyday wedding-band
profile. But it means RNG-25's own ticket, as written, asked for an
invariant that was already false: "min wall 0.8mm holds across the full
in-range parameter space" cannot mean "everywhere in the section," because
the section this app has always built violates that at two points on every
single ring, by design, and nobody had noticed.

The gate never caught it because `_min_wall` checks the **field**
(`band_thickness`, a number in the spec) rather than the **artifact** (the
built B-rep's actual minimum wall anywhere in the cross-section). A field
check can only ever be as honest as the shape it's implicitly assuming; here
it assumed uniform thickness, and the shape was never uniform.

## Decision

State the invariant on the quantity it actually is: `band_thickness` means
the section's thickness **at the band's centreline**, and that is what
`_min_wall` checks and what stays true. No new "minimum wall anywhere in the
section" rule was added — writing one would immediately reject the golden
solitaire, halo, trilogy and side-stone specs this app already ships and
calls correct.

When RNG-25 added a genuinely new zero-thickness risk (a knife edge's ridge,
which the old ellipse-only geometry had no equivalent of), the fix was not a
new gate check on that shape either — it was to make the unsafe value
**inexpressible by construction** (`sections.knife_edge_apex_fraction`
sizes the flat crown to always be exactly `MIN_WALL_MM` wide, whatever the
band width). See ADR-0008 for the general form of that move.

## Consequences

- Anyone adding a new shank cross-section, or a new castability rule that
  talks about "wall thickness," must ask *which* wall thickness: the field
  value, or the minimum anywhere the built section actually reaches. They are
  not the same question, and the field is the wrong one to answer it with.
- This is the same shape of drift as ADR-0002 (a check and the geometry it
  guards silently disagreeing) and ADR-0006 ("validation gates need auditing
  more urgently than builders, because a wrong builder is visible and a wrong
  gate is silent") — a third instance of the same root cause, this time
  found by tracing the math at Design rather than by a failing render.
- `specs/RNG-25.md` records this as a deliberately corrected acceptance
  criterion, not a shipped defect: the ticket's "holds across the full
  parameter space" was rewritten to name the centreline explicitly before any
  code was built against it.
