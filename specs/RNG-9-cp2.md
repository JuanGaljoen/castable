# Feature Spec: RNG-9 Checkpoint 2 — accent primitives (accent_seat + accent_prong)

**Type:** feature (checkpoint 2 of 4 for the halo archetype; parent spec: specs/RNG-9.md)
**Depends on:** RNG-9 CP1 (RingSpec union, merged), RNG-16 (module library), RNG-17
(watertight by construction). **Blocks:** CP3 (halo composition), and reused by
RNG-10 (trilogy) and RNG-11 (pave/channel).
**Status:** Planned, build-ready.

## Problem

CP1 delivered the halo *contract*. Every geometry module in the library today
(`shank`/`seat`/`prong_setting`/`bezel`) builds for the SINGLE center stone at one
position via the shared `placement(c)` transform. A halo needs many small accent
stones, each in its own real bearing held by real prongs. CP2 introduces the two
reusable primitives that make that possible: `accent_seat` and `accent_prong`.

When this is done, the library has two position-agnostic accent builders that CP3
places in a ring, RNG-10 places at two shoulders, and RNG-11 places in a row. No
geometry is wired into an archetype yet (that is CP3).

## Decisions locked in planning

1. **Position-agnostic builder functions, not archetype modules.**
   `accent_seat(accent_r, height, loc)` and `accent_prong(accent_r, height, loc)`
   each build ONE accent's geometry in a local +Z frame and apply `loc` (a
   build123d Location) last, exactly as the center modules apply `placement(c)`.
   Placement (how many, where) is the CALLER's job. They are NOT added to
   `ARCHETYPES["halo"]` and need not be top-level `MODULES` entries. This is what
   makes them reusable by trilogy (2 at shoulders) and pave (a row); a whole-ring
   module would be halo-only and was rejected.
2. **Additive bead/collar bearing.** The accent bearing is built additively (a
   small metal bead/collar sized by `height` for real bearing depth), mirroring
   the center `seat` torus. Watertight by construction, no boolean thin-wall risk
   at sub-2mm scale. A boolean-cut conical seat was rejected (fights the RNG-17
   zero-repair bar).
3. **Shared common-prongs are a CP3 placement concern.** `accent_prong` builds
   ONE closed prong claw. CP3 places prongs at the inter-accent midpoints so
   neighbours share them (the real cast-halo technique). Keeping sharing out of
   the primitive is what lets trilogy/pave reuse it.
4. **Closed by construction (RNG-17 lesson).** Accent prongs use capped /
   sphere-node claws (like the RNG-17-fixed center prongs in `prong_setting`),
   never open-ended cones, with epsilon-overlap readiness so a placed group fuses
   into one watertight body with zero repair.

## Acceptance Criteria

- **CP2-1 (accent_seat).** `accent_seat(accent_r, height, loc)` returns a single
  watertight build123d solid: an additive bead/collar authored in a local +Z
  frame, sized so the bearing depth tracks `height`, then transformed by `loc`.
  Positive volume; single body.
- **CP2-2 (accent_prong).** `accent_prong(accent_r, height, loc)` returns a single
  watertight solid: one closed prong (capped / sphere-node, no open ends) whose
  tip is >= MIN_PRONG_TIP_MM by construction, authored in a local frame and
  transformed by `loc`.
- **CP2-3 (self-checks).** `check_accent_seat` and `check_accent_prong`
  (in `ringcad/geometry/_castability.py`, matching the existing `check_*` pattern)
  probe the REAL produced geometry via planar sections and return `[]` for
  in-range accents; they return a structured `Violation` (single-sourced
  MIN_WALL_MM / MIN_PRONG_TIP_MM, reusing `ringspec.Violation`) when an accent is
  driven below a casting floor. Field names point at the halo fields
  (`halo.halo_stone_diameter` / `halo.halo_stone_height`).
- **CP2-4 (raw watertight, RNG-17 bar).** For representative in-range accents,
  `to_stl_bytes` of each primitive alone AND of two accents placed side by side
  and fused (an adjacency smoke) is watertight, zero non-manifold edges, single
  body, asserted WITHOUT calling `validate_and_repair`. Reuse the RNG-17
  boundary-edge diagnostic (count open edges via trimesh) as the pass/fail signal.
- **CP2-5 (isolation).** The primitives are importable/registered for reuse but
  NOT wired into `ARCHETYPES["halo"]`, `/generate-ring`, or the frontend (CP3/CP4).
  No existing module (`shank`/`seat`/`prong_setting`/`bezel`) changes behavior.
  Full existing suite green; solitaire parity unchanged.

## Approach

Two new files `ringcad/geometry/accent_seat.py` and `accent_prong.py`, each a
free function returning one fused solid, reusing `_common` helpers (`body_solid`,
`_rot_between`, capped-primitive patterns) and build123d primitives. Add
`check_accent_seat` / `check_accent_prong` to `_castability.py`. Local-frame
authoring + `loc` applied last, mirroring `placement()` so CP3 can drive a ring.
Tests in a new `tests/test_accent_primitives.py` (+ split if over 300 LOC).

Build as ONE checkpoint commit (per the checkpoint rule): primitives + checks +
tests green, no archetype wiring.

## Edge Cases

- Accent at schema-minimum size (diameter 0.9, height 0.8): primitive still
  produces a single watertight solid; `check_accent_prong` MAY flag tip < 0.7mm
  (that is the real-geometry floor doing its job, distinct from the CP1 spec-level
  proxy). Assert watertightness regardless of the castability verdict.
- Two accents placed with near-touching bearings: the adjacency-smoke fuse must
  stay a single watertight body (epsilon overlap), not two shells or a
  non-manifold seam.
- `loc` at an arbitrary rotation/position (not just the origin): geometry stays
  watertight and the check still reads the real feature sizes (checks must be
  placement-invariant, or applied in the local frame before `loc`).

## Constraints

- build123d only; no new dependencies. Casting constants imported from
  `ringcad.mesh_validator`, never duplicated.
- Watertight BY CONSTRUCTION: raw STL clean with zero repair (RNG-17 bar). No
  reliance on `validate_and_repair`. No open-ended primitives.
- Max 300 non-blank LOC per source file.
- Scope: ONLY the two new geometry files + `_castability.py` additions + tests.
  Do NOT touch `module.py` ARCHETYPES, `app.py`, `templates/`, `static/`, or the
  existing center modules. Do NOT build the halo composition (CP3).
- mm units, floats throughout.

## Scope Boundaries

**In scope:** `accent_seat.py`, `accent_prong.py`, `check_accent_seat` /
`check_accent_prong` in `_castability.py`, and their tests.

**Out of scope (later):** the `halo` composition module + `ARCHETYPES["halo"]` and
shared-prong placement (CP3); `/generate-ring` dispatch + frontend (CP4); trilogy
(RNG-10) and pave (RNG-11) placement of these primitives.

## Success Metrics

- Each primitive: single watertight solid (0 open edges) by construction across
  the in-range accent size band.
- Adjacency smoke (two placed + fused): single watertight manifold, zero
  non-manifold edges, no repair.
- Self-checks return `[]` in-range and a named `Violation` when starved;
  constants single-sourced.
- Full existing suite green; solitaire parity and CP1 contract untouched.

## Risks

1. **Tiny-feature watertightness** (the RNG-17 failure mode, now at accent scale).
   Mitigate: additive-only, closed-by-construction claws, epsilon overlap; use the
   boundary-edge diagnostic as the build's fast pass/fail loop.
2. **CP1 proxy vs CP2 real geometry disagree at the boundary.** Expected: CP1's
   `min(diam,height)*0.5` is a coarse spec-level proxy; CP2 measures real geometry.
   Do NOT couple CP2 checks to the CP1 proxy; each verifies its own layer.
3. **Placement convention.** `loc` must be a build123d Location applied last so CP3
   can lay accents into a ring; define and test placement-invariance of the checks.
