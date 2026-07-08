# 3. Classify a field as placement or wall before writing a castability proxy for it

- **Status:** Accepted
- **Date:** 2026-07-08
- **Context ticket:** RNG-10 CP1 (trilogy RingSpec contract).

## Context

RNG-10 CP1's Design phase named a planned check, `_trilogy_spacing`, shaped exactly like the
`_halo_wall` proxy that ADR-0002 (`0002-model-level-checks-must-track-real-geometry.md`) had just
retired one ticket earlier: `side_stone_gap >= MIN_WALL_MM`. Working the geometry during Forge
caught this before it shipped. The side setting's post (CP2) will size its wall from a fixed
construction margin, independent of `side_stone_gap` — exactly like the gallery's rail wall was
independent of `halo_gap`. Shipping that check would have reintroduced the identical anti-pattern
a second time, on a second archetype, one ticket later.

The root confusion: a field named or described as a "gap" between two decorative elements (stone
to stone) is easy to mentally conflate with "the metal wall thickness that occupies that gap." But
in every archetype built so far, the load-bearing metal (gallery rail, gallery post) sits *below*
the stones, sized from its own fixed construction minimum — not derived from the visual spacing
field at all. The spacing field only ever controlled placement (a radius or an angle), never a
wall's thickness.

ADR-0002 documented *when to retire* a proxy that construction has since superseded. It did not
say how to avoid *shaping the proxy wrong in the first place* — this is that missing half, caught
before shipping rather than after.

## Decision

Before writing a model-level castability proxy for a field, classify it first:

- **Does construction size a wall or tip from this field's value?** Then a proxy on this field may
  be legitimate — temporarily, pending real geometry, per ADR-0002's retire-when-superseded
  lifecycle.
- **Does this field only control placement** (a radius, an angle, a position), while the actual
  wall is sized from an independent fixed construction margin elsewhere? Then a wall-thickness
  proxy on this field is a category error. If a genuine cross-field geometric risk exists, check
  the real placement math instead — e.g. trilogy's chord-vs-arc collision check
  (`_trilogy_overcrowding`), which verifies the *stones* don't collide, not that a *wall* is thick
  enough.

Rule of thumb: a "gap"/"spacing" field between two decorative elements is a placement input.
Reach for it in a stone-collision or placement check, never a wall-thickness check — unless a
specific module's construction is confirmed (by reading the geometry code, not assumed from the
field's name) to derive a wall directly from that field's value.

## Consequences

- RNG-10 CP1 shipped `_trilogy_overcrowding` (chord distance vs. combined stone radii) instead of
  a `side_stone_gap >= MIN_WALL_MM` proxy.
- Future archetypes — RNG-11 (side-stone/pave) is next in line — should run this classification
  check before shaping any new spacing-adjacent castability rule, rather than pattern-matching on
  the previous archetype's field names.
