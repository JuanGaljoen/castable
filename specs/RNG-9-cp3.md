# Feature Spec: RNG-9 Checkpoint 3 — reusable `gallery` primitive + halo composition

**Type:** feature (checkpoint 3 of 4 for the halo archetype; parent: specs/RNG-9.md)
**Depends on:** RNG-9 CP1 (RingSpec union, merged), CP2 (accent_seat + accent_prong,
merged), RNG-16 (compose/ARCHETYPES), RNG-17 (watertight by construction).
**Blocks:** CP4 (endpoint + frontend). **Reused by:** RNG-10 (trilogy) via the gallery.
**Status:** Planned, build-ready (geometry sub-details are architect decisions).

## Problem

CP2 gave us reusable accent primitives but nothing places them. A halo is a ring
of accents sitting a real `halo_gap` away from the center stone, so left alone it
is a FLOATING ring, not one watertight castable body. CP3 delivers (a) the
placement/composition that rings the accents around the center, and (b) the
connectivity that makes the whole thing a single manifold.

When this is done, `compose(halo_spec)` returns a single watertight halo ring
(center setting + accent ring on a gallery) with `X-Mesh-Repaired: false` on the
golden halo. The endpoint and frontend stay untouched (CP4).

## Decisions locked in planning

1. **Connectivity via a REUSABLE `gallery` primitive, not a halo-specific bridge.**
   Elevated settings (halo, trilogy, cathedral) all sit off-center and must fuse
   into one body; connectivity is an every-archetype problem. CP3 introduces a
   reusable `gallery` primitive (the understructure that carries an elevated
   setting and ties it to the shank/center) as the connectivity STANDARD. Halo is
   its first customer; RNG-10 reuses it. See
   [[2026-07-04-gallery-connectivity-standard]]. Rejected: a halo-only bridge (a
   monolithic-template trap) and beads-overlap-center (makes halo_gap cosmetic).
   Boundary: gallery = elevated settings only; pave/side-stone (RNG-11) sets
   accents INTO the band (connects through the shank), a separate mode.
2. **Shared common-prongs at inter-accent midpoints** (carried from CP2 planning):
   one prong at each inter-accent gap (N prongs for N accents), each accent
   retained by its two flanking shared prongs. The real cast-halo technique.
3. **Halo as a composition:** `ARCHETYPES["halo"] = ["shank", "seat",
   "prong_setting", "halo"]`; the `halo` module builds the accent ring + shared
   prongs seated on the gallery and fuses. compose() does the rest. No monolith.

## Acceptance Criteria

- **CP3-1 (reusable gallery primitive).** A `gallery` builder in
  `ringcad/geometry/gallery.py` produces the understructure (a ring rail beneath
  the accents + inward bridge(s) to the center setting) as a single watertight
  solid, PARAMETRIC (ring radius, height, attachment geometry) and NOT
  halo-hardcoded, so RNG-10 can reuse it. Its in-kernel `check_gallery` enforces
  the min-wall floor on the rail/bridge. Registered in `MODULES` only if it needs
  to be a composable unit; otherwise a reusable builder consumed by `halo`.
- **CP3-2 (halo module + registration).** `ringcad/geometry/halo.py` builds the
  accent ring: N `accent_seat` + N shared `accent_prong` placed at
  `theta_k = 2*pi*k/N` around the center stone axis (+X head axis) at radius
  `R = center_stone_r + halo_gap + accent_r`, seated on the `gallery`, all fused
  into one solid. Registered as `MODULES["halo"]` and `ARCHETYPES["halo"] =
  ["shank","seat","prong_setting","halo"]`. Reuses `_common.clamps()/placement()`
  for the center frame.
- **CP3-3 (single watertight golden halo, RNG-17 bar).** For the golden halo
  (solitaire defaults + halo defaults), `to_stl_bytes(compose(halo_spec))` is
  watertight, zero non-manifold edges, single body, asserted WITHOUT
  `validate_and_repair`. Assert B-rep `.solids()==1` before the raw watertight
  check (per the RNG-17 reframing). No floating ring; the gallery makes it one body.
- **CP3-4 (castable across the range).** Across the in-range halo band
  (diameter/count/gap/height), the per-module self-checks (accent_seat,
  accent_prong, gallery) return no violations on raw geometry, and the fused halo
  stays a single watertight body. Casting floors single-sourced.
- **CP3-5 (isolation).** `compose(halo_spec)` works, but `/generate-ring`
  dispatch and the frontend are NOT wired (CP4). Solitaire composition + parity
  unchanged. Full existing suite green.

## Approach

New files `ringcad/geometry/gallery.py` and `ringcad/geometry/halo.py`; add
`check_gallery` (+ any halo aggregate check) to `_castability.py`; register
`MODULES["halo"]` (and `gallery` if composable) + `ARCHETYPES["halo"]`. Ring
placement math around the +X head axis reuses `placement(c)`; each accent gets a
per-accent `loc` (rotate `theta_k` about the stone axis + radial offset `R`), and
the CP2 primitives take that `loc`. Shared prongs at midpoint angles
`theta_k + pi/N`. Gallery rail is a thin ring beneath the accents with inward
bridge(s) to the center seat/gallery so the fuse is a single manifold. Epsilon
overlap (reuse `ACCENT_FUSE_EPS`) at every joint for single-body fusion.

Build as ONE checkpoint commit: gallery + halo + registration + tests green,
no endpoint/frontend.

## Architect / brainstorm sub-decisions (geometry detail, bounded by the ACs)

- Exact gallery PROFILE (solid rail vs openwork arches; how many inward bridges;
  how the rail meets the center seat vs the shank). Bounded by min-wall 0.8mm and
  the raw-watertight bar. Keep it reusable/parametric for RNG-10.
- Accent ORIENTATION (flat, axis parallel to the center stone axis, is the default;
  outward tilt is out of scope for v1).
- Whether `gallery` is a registered MODULE (in ARCHETYPES) or a builder consumed
  by `halo`. Prefer the builder unless composition cleanliness argues otherwise;
  it must stay reusable by RNG-10 either way.
- Prong length/where the shared prong grips two neighbours; bounded by 0.7mm tip.

## Edge Cases

- Max count + max diameter at min gap: accents crowd; the CP1 castability
  overcrowding rule already flags the spec; geometry must still fuse to one body
  (or the golden-band tests restrict to castable inputs).
- Min accent size on the gallery: gallery rail wall must stay >= 0.8mm.
- N odd vs even: shared-prong midpoint placement must handle both (N prongs for N
  gaps regardless of parity).
- The ring must close (accent N-1 shares a prong with accent 0).

## Constraints

- build123d only; no new deps. Casting constants single-sourced from
  `_common`/`mesh_validator`. Reuse `ACCENT_FUSE_EPS`.
- Watertight BY CONSTRUCTION (RNG-17 bar): raw STL clean, zero repair, assert
  `.solids()==1` before the watertight check. Epsilon is for single-body fusion.
- Placement-invariant checks convention (guard empty sections, feature-derived
  probe offsets, local-frame sectioning) per
  [[in-kernel-castability-check-conventions]].
- Max 300 non-blank LOC/file. Gallery MUST be reusable/parametric (RNG-10), not
  halo-hardcoded.
- Scope: gallery.py + halo.py + `_castability.py` checks + MODULES/ARCHETYPES
  registration + tests. Do NOT touch `app.py`, `templates/`, `static/` (CP4), the
  existing center modules' behavior, or export.py.

## Scope Boundaries

**In scope:** `gallery.py`, `halo.py`, their `_castability` checks,
`MODULES`/`ARCHETYPES["halo"]` registration, tests, and (if needed) a golden-halo
example. **Out of scope:** `/generate-ring` halo dispatch + frontend (CP4);
trilogy/pave placement of the gallery (RNG-10/11); vision (RNG-12).

## Success Metrics

- `compose(halo_spec)` for the golden halo: single watertight body, 0 non-manifold
  edges, `X-Mesh-Repaired: false` equivalent (raw), no floating ring.
- Castability floors hold across the in-range halo band; self-checks green on raw.
- Gallery is demonstrably reusable (parametric; a test builds it standalone at a
  non-halo radius/config).
- Solitaire parity + full existing suite green.

## Risks

1. **Single-manifold fuse of many small parts** (N accents + N prongs + gallery +
   center) is the RNG-17 risk at its worst. Mitigate: assert `.solids()==1` first
   (disambiguate fuse-count from exporter), epsilon overlap at every joint,
   additive-only, the boundary-edge diagnostic as the fast loop.
2. **Gallery-to-center connectivity** — if the inward bridge does not truly
   interpenetrate the center seat, the halo floats (2 bodies). Test `.solids()==1`
   on the full compose, not just the halo module in isolation.
3. **Ring placement math around +X** — off-by-one/parity in midpoint prong
   placement, or a frame error tilting accents. Test accent count == N and the
   ring closes (accent N-1 <-> accent 0 share a prong).
4. **Over-generalizing the gallery** — do not build speculative parameters RNG-10
   might want; make it parametric enough to reuse, verified by one standalone
   non-halo test, no more.
