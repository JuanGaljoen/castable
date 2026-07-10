# RNG-11: Side-stone band style — channel accents (parametric, castable)

**Type:** feature
**Status:** In progress — Design frozen, Checkpoint 1 next
**Depends on:** RNG-16 (module library), RNG-9 (`accent_seat` primitive). Done.
**Relates to:** RNG-19 (aesthetic refinement, final polish after vision).

> Status note (2026-07-10): Understand + Design complete on branch
> `feat/rng-11-side-stone-band`. This spec freezes the decisions so a fresh
> session resumes a checkpoint directly from here, not the conversation. Three
> checkpoints, each its own PR (the RNG-10 rhythm). Jira RNG-11 stays In
> Progress until Checkpoint 3 lands.

## Problem

The app builds solitaire, halo, and trilogy. Side-stone is the fourth
archetype and the first to use a **different connectivity mode**: accents set
INTO the band, retained by a continuous channel and connected to the ring
THROUGH the shank itself — not elevated on a `gallery`/post (the RNG-9 CP3
boundary: "pave / side-stone sets accents into the band; elevated settings use
the gallery family"). It is the hardest archetype to keep castable (many small
seats + continuous walls), so v1 ships the sturdier retention mode first.

When this is done, a user can select the Side-stone band style, keep a normal
solitaire centre, add a symmetric row of channel-set accents marching down each
shoulder, and download a castable STL (and STEP) that is a single watertight
manifold.

## Decisions locked in planning

1. **Channel retention only in v1; pave deferred behind the `retention`
   switch.** The ticket flags pave beads (many tiny shared-prong unions) as the
   watertightness risk and says "favour channel first." So v1 implements
   `retention="channel"` and nothing else. `retention` is typed
   `Literal["channel"]` (Decision 5) so a `"pave"` value is a clean schema
   rejection, not a shipped-but-broken option; widening the literal to add
   `"pave"` later is purely additive.

2. **Composition = solitaire centre + accented band.** `ARCHETYPES["side_stone"]
   = ["shank", "seat", "prong_setting", "side_stone"]` — the whole solitaire
   centre is reused (as halo/trilogy do), and the new `side_stone` module adds
   the shoulder accents + channel walls. A recognisable accented engagement
   ring, not a standalone eternity band. (Standalone band / centre toggle is
   out of scope for v1.)

3. **Channel retention uses WALLS, not prongs — so NO `accent_prong` here.** A
   channel setting holds each stone between two continuous rails, not with
   claws. So the module places `accent_seat` beads (bearings) seated into the
   band, flanked by two channel-wall rails per shoulder — and never an
   `accent_prong`. This is simpler than trilogy in claw terms.

4. **Connectivity: weld through the shank, NO gallery.** Each `accent_seat`'s
   bearing plunges transversally into the band (a deep volumetric overlap, not
   a tangent graze — the recurring OCCT non-manifold trap), and the channel
   walls union into the band's outer surface. Everything is therefore one
   manifold through the shank; no gallery rail, no post. This is the
   "connect-through-the-shank" mode the RNG-9 CP3 comment reserved for
   pave/side-stone.

5. **Field contract — a `SideStone` group (CP1):** `accent_stone_diameter`,
   `accent_stone_height` (bearing depth), `accent_count_per_side` (int;
   symmetric, so total accents = 2×), `accent_gap` (edge-to-edge spacing along
   the shoulder), `retention` (`Literal["channel"]`). The angular span each row
   occupies is DERIVED from count + diameter + gap (like halo derives its
   spacing), not a separate field.

6. **Placement: accents march down each shoulder from just off the head.** For
   shoulder `sign ∈ {+1, -1}`, accent `k` sits at ring-angle
   ```
   a_k = sign * (A_START + k * dphi)          # k = 0 .. count-1
   dphi = (accent_diameter + accent_gap) / band_outer_r   # arc → angle
   ```
   where `A_START` clears the centre head and `band_outer_r = inner_r + bt`.
   Each seat sits on the band's outer surface with its axis pointing radially
   out (table faces away from the finger), seated `accent_stone_height` into the
   band. The row must stop before the ring base (see castability). Accents stay
   on the band centreline in width (global Z=0), between the two walls.

7. **Castability: `_side_stone_overcrowding` (CP1), not a wall proxy.** Two real
   geometric constraints construction doesn't self-guard (same spirit as
   `docs/adr/0003`): (a) the row must fit the shoulder span —
   `A_START + (count-1)*dphi ≤ A_MAX` (base clearance), else the accents run
   onto the palm side of the ring; (b) adjacent accents' true CHORD distance at
   `band_outer_r` must clear their combined radii (the arc-length `accent_gap`
   over-reads separation at small radius / large stones, exactly the trilogy
   chord-vs-arc subtlety). Flags `side_stone.accent_count_per_side` or
   `side_stone.accent_gap`. NOT an `accent_gap >= MIN_WALL` proxy — the wall
   thickness is a fixed construction margin independent of the gap.

## Acceptance Criteria

1. **Composition, not a monolith.** `ARCHETYPES["side_stone"] = ["shank",
   "seat", "prong_setting", "side_stone"]`; a new `side_stone` module places the
   shoulder accents + channel walls and fuses via the existing `compose()`.
2. **RingSpec union member (CP1).** `SideStoneSpec` validates a `side_stone`
   spec; a spec missing the `side_stone` group, or another archetype carrying
   one, is rejected naming the offending field; a `retention` other than
   `"channel"` is rejected naming `side_stone.retention`. Additive — existing
   archetypes and the flat-7 round trip unaffected.
3. **Fields documented (CP1).** The five `side_stone` fields' ranges/defaults in
   `docs/parameter-ranges.md` and `docs/ringspec/contract.md`; JSON Schema
   regenerated; committed example under `docs/ringspec/examples/`.
4. **Castable by construction across the range.** For all in-range side_stone
   inputs: min wall 0.8mm, single watertight manifold, zero non-manifold edges,
   via reused `check_accent_seat` on every bearing + a channel-wall min-wall
   check (`check_side_stone`). Raw geometry, not repair-into-castability (the
   RNG-17 bar).
5. **Raw watertight golden band.** The raw (pre-repair) STL for the golden
   side-stone ring (solitaire defaults + side_stone defaults) is watertight,
   zero non-manifold edges, single body (`.solids() == 1`), asserted on
   `to_stl_bytes(compose(spec))` without `validate_and_repair`.
6. **Endpoint returns a clean band.** `POST /generate-ring` with a side_stone
   RingSpec returns a trimesh-loadable STL; `?format=step` returns STEP. No
   `app.py` change (structured dispatch already archetype-generic). Malformed /
   not-castable specs return a 400 naming the field.
7. **Frontend exposes the fields.** When side_stone is active, the form shows
   the accent fields + the `retention` control (channel), pre-filled with
   defaults, editable, hidden otherwise. WCAG 2.1 AA holds.

## Checkpoints

- [x] **CP1 — contract:** SideStone + SideStoneSpec, _side_stone_overcrowding, docs/schema, tests
- [x] **CP2 — composition:** side_stone.py (seats + channel walls), check_side_stone, registration, watertight tests
- [ ] **CP3 — wire-up:** frontend fields + retention control, backend/frontend tests, CLAUDE.md

## Approach

Three checkpoints (the RNG-10 rhythm), each a trustworthy commit + its own PR:

- **Checkpoint 1 (contract).** `SideStone` group + `SideStoneSpec` union member;
  `_side_stone_overcrowding` (Decision 7); ranges/defaults in docs; regenerated
  schema + committed example; `tests/test_ringspec_side_stone*.py`. No geometry.
- **Checkpoint 2 (composition) — the risky one.**
  - `ringcad/geometry/side_stone.py`: `side_stone_parts(spec, c)` returns
    UN-fused leaves `[*seats, *walls]` for both shoulders (compose flat-fuses
    them with the centre's leaves — the RNG-17/halo robustness lesson). Seats via
    `accent_seat` at Decision-6 locations, plunged transversally into the band.
    Channel walls: two rails per shoulder along the ±(w/2) Z-edges over the
    accent arc span, unioned into the band, rising a fixed margin above the
    surface to retain girdles. Walls overlap the band volumetrically (never a
    tangent graze).
  - `check_side_stone(solid, spec, clamps)`: reuse `check_accent_seat` per seat
    (rebuild each isolated leaf at its real `loc` before checking — the
    `check_trilogy` lesson: those checks read the solid's OWN bbox, valid only
    for an isolated primitive), plus a channel-wall min-wall section check.
  - Register `MODULES["side_stone"]` + `ARCHETYPES["side_stone"]`; export from
    `ringcad/geometry/__init__.py`.
  - `tests/test_side_stone.py`: golden + curated in-range band watertight WITHOUT
    repair, `.solids()==1`, side floors via the reused checks, solitaire parity.
  - **May sub-split** if the channel walls fight watertightness (ship a
    checkpoint at the seats-only or one-wall-mode boundary rather than a
    half-written module).
- **Checkpoint 3 (wire-up).** `templates/index.html` (`<option>` + a
  `#side-stone-fields` fieldset incl. the retention control), `static/app.js`
  (add to the `ARCHETYPES` registry from RNG-10 CP3 — one entry), `CLAUDE.md`
  note, `tests/test_backend.py` + `tests/test_frontend.py`. No `app.py` change.

## Field ranges + defaults (CP1)

| field                    | min | max | default | notes                                            |
|--------------------------|-----|-----|---------|--------------------------------------------------|
| `accent_stone_diameter`  | 0.9 | 2.5 | 1.5     | melee size; channel-retained, no prong tip floor |
| `accent_stone_height`    | 0.8 | 3.0 | 1.2     | bearing well depth                               |
| `accent_count_per_side`  | 1   | 8   | 3       | int; symmetric → total accents = 2×              |
| `accent_gap`             | 0.2 | 1.0 | 0.3     | edge-to-edge along the shoulder                  |
| `retention`              | —   | —   | channel | `Literal["channel"]`; pave is a future value     |

## Edge Cases

- **Too many accents / too-tight gap for the shoulder:** `_side_stone_overcrowding`
  flags `accent_count_per_side` (row overruns the base clearance) or
  `accent_gap` (adjacent chord distance below combined radii).
- **Channel wall min thickness:** a fixed construction margin, independent of
  `accent_gap` (Decision 7) — enforced by `check_side_stone`, not a spec proxy.
- **Accent seat / band weld (CP2):** must be a deep transversal plunge; verify
  raw watertight, not relying on `validate_and_repair`.
- **Wall / centre-setting collision near the head:** `A_START` clears the head;
  verify no interference with the centre claws across the in-range band.
- **Another archetype carrying `side_stone`, or a side_stone spec missing it, or
  `retention != "channel"`:** schema rejection with a field-level error.

## Constraints

- Casting floors non-negotiable: min wall 0.8mm, single watertight manifold,
  zero non-manifold edges on export. (No prong-tip floor — channel has no
  prongs.)
- RNG-17 bar: raw golden-band STL watertight; no reliance on
  `validate_and_repair` beyond a safety net.
- Max 300 non-blank LOC per source file. No new top-level dependencies.
- No JS frameworks; vanilla JS; WCAG 2.1 AA for new fields.
- Existing archetypes (solitaire/halo/trilogy) unchanged; full suite green after
  each checkpoint.
- mm units, floats; casting constants from `ringcad.mesh_validator` only.

## Scope Boundaries

**In scope:** the `SideStone`/`SideStoneSpec` contract + `_side_stone_overcrowding`
(CP1); the `side_stone` channel composition module + `ARCHETYPES` entry (CP2);
`/generate-ring` dispatch (already generic, verify only) + frontend fields (CP3);
docs/schema; tests throughout.

**Out of scope (deferred):**
- **Pave retention** — the second `retention` value; additive later.
- Vision-driven population of this archetype (RNG-12).
- Standalone accented band with no centre, or a centre on/off toggle.
- Graduated accents (varying size down the shoulder); v1 is uniform.
- Mixing side-stone with halo/trilogy in one ring.
- Aesthetic surface polish of the walls/seats (RNG-19).

## Success Metrics

- Golden side-stone raw STL: watertight, zero non-manifold edges, single body.
- Castability floors hold for 100% of in-range inputs.
- 100% of malformed side_stone specs rejected with a named offending field.
- Solitaire/halo/trilogy parity unaffected.
- Full existing suite green after each checkpoint.

## Design Notes + Dependencies

- Reuses RNG-9's `accent_seat` (CP2). Deliberately does NOT reuse `accent_prong`
  (channel = walls) or `gallery` (weld through the shank, Decision 4).
- New geometry: `ringcad/geometry/side_stone.py` + `check_side_stone` in
  `_castability.py` + `MODULES`/`ARCHETYPES` entries (CP2).
- RingSpec (CP1): `ringcad/ringspec/models.py` (`SideStone`, `SideStoneSpec`),
  `ringcad/ringspec/castability.py` (`_side_stone_overcrowding`), regenerated
  schema under `docs/ringspec/`.
- Endpoint: no change (structured dispatch archetype-generic since RNG-9 CP4).
- Frontend: `templates/index.html`, `static/app.js` (the CP3 `ARCHETYPES`
  registry gains one entry).
- Related ADRs: `docs/adr/0002` (retire proxies superseded by real geometry),
  `docs/adr/0003` (classify a field as placement vs. wall before a proxy).
