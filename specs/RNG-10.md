# RNG-10: Three-stone (Trilogy) ring style (parametric, castable)

**Type:** feature
**Status:** In progress — Checkpoint 2 of 3 done
**Depends on:** RNG-9 (accent_seat, accent_prong, gallery primitives). Done.
**Blocks (soft):** RNG-11 (pave/channel) may reuse the trilogy placement pattern
for a small fixed accent count; not a hard dependency.

> Status note (2026-07-09): Checkpoint 2 (composition) is committed on branch
> `feat/rng-10-trilogy` (`ringcad/geometry/trilogy.py`, `check_trilogy`,
> `MODULES["trilogy"]`/`ARCHETYPES["trilogy"]`, `tests/test_trilogy.py` — 20
> tests, golden + curated band raw-watertight, side floors held). Full suite:
> 3224 passed (was 3204 at CP1). One CP2 deviation from the original plan
> worth flagging for CP3 debugging: `check_trilogy` does NOT hand
> `check_accent_seat`/`check_accent_prong` the fused `solid` argument directly
> — those checks derive their probe plane from the solid's own bounding box,
> which only means "this one accent's extent" when the solid IS that isolated
> accent; against the fused multi-accent trilogy body it read the whole
> compound's extent instead (caught by `test_trilogy_side_floors_hold`, a
> spurious `min_prong_tip` violation at 0.083mm). Fix: `check_trilogy` rebuilds
> each isolated leaf at its real `_side_locs` location and checks that,
> instead of slicing the passed-in fused solid — same real geometry
> `trilogy()` fuses, just probed pre-fuse. Remaining: Checkpoint 3 (wire-up —
> frontend fields, backend/frontend tests, CLAUDE.md note).

## Problem

The app builds solitaire and halo. Trilogy is the second archetype to reuse the
RNG-9 accent primitives rather than introduce new geometry: a center stone
(unchanged solitaire center: `shank` + `seat` + `prong_setting`) flanked by two
symmetric side stones, each in its own real bearing held by real prongs.

Unlike halo (a full ring of many accents needing a new `gallery` rail +
`halo` composition module), trilogy places exactly two accents at fixed
symmetric positions. The RNG-9 CP3 planning comment anticipated reusing the
`gallery` primitive verbatim for this; working the geometry in Design showed
the gallery's 360-degree rail-around-a-hub topology fits a halo's ring but
degenerates under a single flanking stone (see Decision 2). Because trilogy
needs no new reusable primitive, it collapses to 3 checkpoints instead of
halo's 4 (contract, composition, wire-up — no separate primitive checkpoint).

When this is done, a user can select the Trilogy style, set the three side-stone
parameters, and download a castable STL (and STEP) of a real trilogy ring whose
side stones sit in real bearings held by their own prongs, connected to the
shank by a gallery-post pedestal.

## Decisions locked in planning

1. **Side settings reuse `accent_seat` + `accent_prong` verbatim (RNG-9 CP2),
   not the center's `prong_setting` module and not new bespoke geometry.**
   `prong_setting` is pinned to the head via `placement(c)` and would need
   refactoring to be position-agnostic before it could sit on a shoulder;
   the accent primitives already take an arbitrary `loc`, which is exactly
   what a shoulder placement needs. Each side stone = one `accent_seat` + 4
   `accent_prong` (4 prongs fixed for v1, not a field).

2. **Connectivity: a gallery POST, not the verbatim gallery primitive.**
   `gallery(ring_r, rail_top_z, hub_r, loc=...)` (RNG-9 CP3) is built for a
   360-degree rail carrying many ring-spaced accents around a central hub. A
   single flanking stone has no ring and no center-peg beneath it, so the
   verbatim primitive would leave the stone cantilevered off-axis on a
   near-empty rail. The sound reduction is the gallery's **hub alone** — a
   short cylindrical post plunging from the shank shoulder up into the side
   `accent_seat`'s bearing, the same fixed-construction-margin wall discipline
   as the gallery hub (not derived from any spec field). This keeps trilogy on
   the "elevated settings use the gallery family" standard (`CLAUDE.md`)
   while being geometrically honest about what a single bead needs. Rejected:
   the verbatim rail+hub+bridges gallery (baroque for one stone, cantilevered);
   a bare weld with no post (breaks the "elevated setting tied to the shank"
   standard).

3. **Field contract — a `Trilogy` group (shipped in CP1):**
   `side_stone_diameter`, `side_stone_height`, `side_stone_gap` (mm,
   edge-to-edge spacing between center and each side stone, mirroring
   `halo_gap`'s role). Side count fixed at 2 (symmetric), side prongs fixed at
   4. No `side_prong_count` field in v1 — standard three-stone sides don't need
   the extra surface area.

4. **Placement: the center's own `placement(c)` rotated by the derived
   angular offset.** A side setting's location is
   ```
   side_loc(sign) = Rot(0, 0, sign * phi_deg) * placement(c)      # sign = +1/-1
   phi = (stone_r + side_stone_gap + side_r) / head_r              # radians
   ```
   `placement(c)` already lays local +Z onto the radial head axis; rotating
   the whole placement by ±phi about global Z slides the setting along the
   shoulder while keeping its axis radial. Sides stay at head radius for v1
   (graduated/lower side stones are future work, not this ticket).

5. **Castability: no wall-thickness proxy on `side_stone_gap`.** An early plan
   named a `side_stone_gap >= MIN_WALL_MM` check (mirroring the pattern
   `docs/adr/0002` had just retired for halo). Design/Forge caught this: the
   post's wall (Decision 2) is a fixed construction margin, independent of
   `side_stone_gap`, exactly like the gallery hub is independent of
   `halo_gap`. `side_stone_gap` is a placement field, not a wall field.
   Shipped instead: `_trilogy_overcrowding` (in `ringcad/ringspec/
   castability.py`, landed in CP1) — checks the real chord (straight-line)
   distance between the center and side stone positions against their
   combined radii, since the placement math in Decision 4 uses an arc-length
   approximation of the gap that diverges from the true chord at larger
   offsets. Same class of check as `_halo_overcrowding`. General rule written
   up in `docs/adr/0003` for RNG-11 to apply before shaping a similar check.

## Acceptance Criteria

1. **Trilogy as a composition, not a monolith.** `ARCHETYPES["trilogy"] =
   ["shank", "seat", "prong_setting", "trilogy"]`; a new `trilogy` module
   places the two side settings and fuses via the existing `compose()`. No
   bespoke monolithic builder.
2. **RingSpec union member (done, CP1).** `TrilogySpec` validates a `trilogy`
   spec; a spec missing the `trilogy` group, or a solitaire/halo spec carrying
   one, is rejected naming the offending field. Additive — solitaire/halo
   behavior and the flat-7 round trip are unaffected.
3. **Trilogy fields documented (done, CP1).** `side_stone_diameter`,
   `side_stone_height`, `side_stone_gap` ranges/defaults in
   `docs/parameter-ranges.md` and `docs/ringspec/contract.md`; JSON Schema
   regenerated.
4. **Castable by construction across the range.** For all in-range trilogy
   inputs: min wall 0.8mm, min prong tip 0.7mm hold via the reused
   `check_accent_seat`/`check_accent_prong` self-checks on both side settings,
   plus a new `check_trilogy` aggregate. Raw geometry, not repair-into-
   castability (the RNG-17 bar).
5. **Raw watertight golden trilogy.** The raw (pre-repair) STL for the golden
   trilogy (solitaire defaults + trilogy defaults) is watertight, zero
   non-manifold edges, single body (`.solids() == 1`), asserted directly on
   `to_stl_bytes(compose(trilogy_spec))` without `validate_and_repair`.
6. **Endpoint returns a clean trilogy.** `POST /generate-ring` with a trilogy
   RingSpec returns a trimesh-loadable binary STL; `?format=step` returns
   STEP. No `app.py` changes needed — the structured dispatch path (RNG-9 CP4)
   is already archetype-generic. Castability violations and malformed specs
   return a 400 naming the field (already true for any registered archetype;
   verified live in CP1 that an unregistered "trilogy" archetype currently
   fails cleanly with a 400 `unknown archetype 'trilogy'`, not a 500).
7. **Frontend exposes trilogy fields.** When the trilogy archetype is active,
   the form shows the three trilogy fields (pre-filled with defaults,
   editable) and hides them otherwise. WCAG 2.1 AA holds.

## Approach

Three checkpoints (fewer than halo's four — no new reusable primitive needed),
built straight through in one session per Understand's locked decision, commit
at each seam:

- **Checkpoint 1 (contract) — DONE.** `Trilogy` group + `TrilogySpec` union
  member, `_trilogy_overcrowding` castability check, docs/schema/example, and
  `docs/adr/0003` (the spacing-vs-wall lesson). One commit on branch
  `feat/rng-10-trilogy`; full suite green (3204 passed at commit time).
- **Checkpoint 2 (composition) — NEXT.**
  - `ringcad/geometry/trilogy.py` (new): `trilogy_parts(spec, c)` /
    `trilogy(spec, c)`, mirroring `halo.py`'s shape — `trilogy_parts` returns
    UN-fused leaves `[post_left, seat_left, *prongs_left, post_right,
    seat_right, *prongs_right]` so `compose()` flat-fuses them alongside the
    center's leaves in one general fuse (the RNG-17/halo robustness lesson:
    never hand `compose` a pre-fused compound for a heavy module). The post is
    a `Cylinder` plunging deep into the shank band (transversal join, not a
    tangent graze — the CP3 non-manifold trap) up into the `accent_seat`
    bearing above it, sized from a fixed margin off `MIN_WALL`, independent of
    `side_stone_gap` (Decision 2/5). Side locations from Decision 4's
    `side_loc(sign)`.
  - `ringcad/geometry/_castability.py`: `check_trilogy(solid, spec, clamps)`
    reusing `check_accent_seat`/`check_accent_prong` over both side settings
    (undo each side's `loc`, section in the local frame — same
    placement-invariant convention as `check_gallery`).
  - `ringcad/geometry/module.py`: register `MODULES["trilogy"]` (`_build`,
    `_check=check_trilogy`, `_parts=trilogy_parts`) and `ARCHETYPES["trilogy"]
    = ["shank", "seat", "prong_setting", "trilogy"]`.
  - `ringcad/geometry/__init__.py`: export `trilogy`.
  - `tests/test_trilogy.py` (new): golden trilogy watertight, `.solids()==1`,
    zero non-manifold edges, asserted WITHOUT `validate_and_repair`; full
    in-range band; side floors via the reused accent checks; center/solitaire
    parity unaffected.
- **Checkpoint 3 (wire-up).**
  - `templates/index.html`: `<option value="trilogy">` + a `#trilogy-fields`
    fieldset (3 inputs, hints, ARIA), mirroring the halo fieldset.
  - `static/app.js`: `TRILOGY_NUMBER_KEYS`, `gatherTrilogyBody()`, extend
    `gatherRequestBody`/`applyArchetypeVisibility`/`clearFieldErrors` (light
    generalization across archetypes to avoid a growing if-chain, since this
    is now the second non-solitaire archetype).
  - `CLAUDE.md`: note trilogy in the archetype list.
  - `tests/test_backend.py` (trilogy → 200 STL trimesh-loadable + X-Mesh
    headers; `?format=step`; malformed → 400 named field; not-castable → 400)
    and `tests/test_frontend.py` (option present; fields toggle
    visible/required; body shape). **No `app.py` changes** — confirmed in CP1
    that structured dispatch is already archetype-generic (AC6).

## Trilogy field ranges + defaults (shipped in CP1)

Sized for a ~6.5mm (approximately 1ct round) center stone; side stones smaller,
per trilogy convention.

| field                 | min | max | default | notes                                                          |
|-----------------------|-----|-----|---------|-----------------------------------------------------------------|
| `side_stone_diameter` | 0.9 | 6.0 | 2.5     | side stone; prong tip held >= 0.7mm by construction              |
| `side_stone_height`   | 0.8 | 4.0 | 1.8     | side-seat bearing well depth                                     |
| `side_stone_gap`      | 0.3 | 2.0 | 0.6     | centre-to-side spacing; `trilogy_overcrowding` guards collision  |

## Edge Cases

- **Oversized side stone on a small ring:** `_trilogy_overcrowding` flags
  `trilogy.side_stone_gap` when the chord distance between centre and side
  falls below their combined radii (see CP1 tests for concrete fixture
  values).
- **`side_stone_gap` at min (0.3) with a large `side_stone_diameter` (near
  6.0):** may or may not flag depending on `head_r`; verified case-by-case by
  the CP1 castability tests, not a blanket rejection.
- **Post-to-shank weld (CP2):** must be a deep transversal plunge; verify raw
  watertight, not relying on `validate_and_repair`.
- **Side-prong vs. center-claw collision at small gaps (CP2):** mitigated by
  `_trilogy_overcrowding` at the spec level; verify no interference across the
  in-range band in geometry tests.
- **Solitaire/halo specs carrying a `trilogy` group, or a trilogy spec missing
  it:** schema rejection with a field-level error (union discriminator; tested
  in CP1).
- **Unregistered "trilogy" archetype pre-CP2:** confirmed live in CP1 — a
  schema-valid, castable trilogy spec currently 400s cleanly with "unknown
  archetype 'trilogy'" via `compose()`'s `UnknownArchetypeError`, not a 500.
  This resolves itself once CP2 registers the module; not a bug to fix.

## Constraints

- Casting floors non-negotiable: min wall 0.8mm, min prong tip 0.7mm, single
  watertight manifold, zero non-manifold edges on export.
- RNG-17 bar: raw (pre-repair) golden-trilogy STL is watertight; no reliance
  on `validate_and_repair` as anything but a safety net.
- Max 300 non-blank LOC per source file.
- No new top-level dependencies (build123d, Pydantic already present).
- No JS frameworks; vanilla JS only. WCAG 2.1 AA for the new fields.
- Solitaire and halo behavior unchanged; full existing suite stays green after
  each checkpoint.
- mm units, floats throughout; casting constants referenced from their single
  source (`ringcad.mesh_validator`), never duplicated.

## Scope Boundaries

**In scope:** `TrilogySpec`/`Trilogy` group (done, CP1); `_trilogy_overcrowding`
(done, CP1); the `trilogy` composition module + `ARCHETYPES["trilogy"]` (CP2);
`/generate-ring` trilogy dispatch, already generic (verify only, CP3); frontend
trilogy fields (CP3); docs/schema (done, CP1); tests throughout.

**Out of scope (deferred):**
- Vision-driven population of the trilogy archetype (RNG-12).
- Graduated/lower side stones (side stones at a different height/radius than
  the center); v1 keeps both at head radius.
- `side_prong_count` as a field; fixed at 4.
- Pave/channel (RNG-11), which may reuse the trilogy placement pattern but is
  a separate ticket.

## Success Metrics

- Golden trilogy raw STL: watertight, zero non-manifold edges, single body,
  `.solids() == 1`.
- Castability floors hold for 100% of in-range trilogy inputs.
- 100% of malformed trilogy specs rejected with a named offending field.
- Solitaire and halo parity unaffected (no regression).
- Full existing suite green after each checkpoint (3204 at CP1).

## Design Notes + Dependencies

- Builds on RNG-9's `accent_seat`, `accent_prong` (CP2) and `gallery` (CP3,
  reduced to its hub — see Decision 2).
- New geometry file: `ringcad/geometry/trilogy.py`, plus `_castability.py`
  (`check_trilogy`) and `MODULES`/`ARCHETYPES` entries (CP2).
- RingSpec changes (done, CP1): `ringcad/ringspec/models.py` (`Trilogy`,
  `TrilogySpec`), `ringcad/ringspec/castability.py`
  (`_trilogy_overcrowding`), regenerated schema under `docs/ringspec/`.
- Endpoint: no changes — `ringcad/app.py`'s structured dispatch is already
  archetype-generic (confirmed live in CP1).
- Frontend: `templates/index.html`, `static/app.js` (CP3).
- Related ADRs: `docs/adr/0002` (retire proxies superseded by real geometry),
  `docs/adr/0003` (classify a field as placement vs. wall before writing a
  proxy for it — the lesson this ticket generalized from 0002).
