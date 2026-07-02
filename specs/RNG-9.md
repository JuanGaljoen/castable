# RNG-9: Halo ring style (parametric, castable)

**Type:** feature
**Status:** Planned, build-ready
**Depends on:** RNG-16 (module library), RNG-17 (watertight by construction). Both Done.
**Blocks (soft):** RNG-10 (trilogy) and RNG-11 (pave/channel) reuse the accent
primitives this ticket introduces.

> Planning note (2026-07-02): the prior RNG-9 branch and its spec were discarded
> (built during a rate-limited window, trust unclear). This is a fresh plan. The
> earlier Jira comment (id 10233) is superseded by this spec. The core design
> decisions were re-derived on their merits, not inherited, and two were locked
> live: accent construction (Option A) and the RingSpec structure (discriminated
> union).

## Problem

The app can build only the solitaire archetype today. Progress toward the "any
ring" goal advances by growing the module vocabulary and composition rules, not
by piling up monolithic per-style templates. The halo is the first archetype
built on the RNG-16 module library and the first to require real per-accent
settings: a center stone ringed by small accent stones, each held in its own
real bearing by real (shared) prongs.

It is also the first non-solitaire commitment to RingSpec as the API contract:
halo, and every archetype after it (including the RNG-12 vision layer), is
requested as a full structured RingSpec JSON. RNG-16 and RNG-14 both deferred
the true discriminated-union shape of RingSpec to "the first archetype ticket";
this is that ticket.

When this is done, a user can select the Halo style, set the halo parameters,
and download a castable STL (and STEP) of a real halo ring whose accent stones
sit in real per-accent bearings held by shared common-prongs. Before this, the
only archetype was the solitaire and there was no structured path for an
archetype carrying fields beyond the solitaire-7.

## Decisions locked in planning

1. **Accent construction: per-accent bearings + shared common-prongs (Option A,
   the real cast-halo technique).** Each accent stone gets its own cut
   seat/bearing and is held by real prongs, shared common-prong style between
   neighbours. This introduces two reusable primitives, `accent_seat` and
   `accent_prong`, that RNG-10 (side-stone settings) and RNG-11 (many small
   shared-prong pave seats) reuse. Rejected: a shared grooved collar (a shortcut
   that yields no real per-accent settings and nothing reusable for RNG-10/11)
   and isolated micro-baskets (an un-castable anti-pattern: many isolated
   sub-0.7mm features and a fragile fuse). Rationale: "any ring" is a vocabulary
   problem; only Option A adds reusable words. RNG-17 was sequenced before RNG-9
   precisely so real per-accent settings build on a watertight-by-construction
   foundation, and a halo is the forgiving case (accents spaced around a center,
   not jammed edge-to-edge) in which to prove the accent primitives before
   RNG-11 stresses them.

2. **RingSpec grows via a Pydantic discriminated union keyed on `archetype`.**
   Split the single `RingSpec` model into per-archetype models
   (`SolitaireSpec`, `HaloSpec`) under `Annotated[Union[...],
   Field(discriminator="archetype")]`. Each archetype carries exactly its own
   fields; no ring accumulates another archetype's optional fields. RNG-10/11
   become "+1 union member." Rejected: an additive `halo: Halo | None` optional
   group on the single model (lower risk tonight, but every future archetype
   bolts on another optional group plus a cross-field "required-when" validator,
   and by archetype 6 the model carries everyone's fields as optionals). This is
   the cheapest moment to establish the union (only 2 members).

3. **New Halo field group** exposes `halo_stone_diameter`, `halo_stone_count`,
   `halo_gap`, `halo_stone_height`, so accents get real, controllable bearing
   depth and spacing. Casting floors stay in `castability.py`, not on the model
   (per the RNG-14 split: the model enforces structural validity only, so a
   well-formed-but-uncastable spec can be constructed and then flagged).

## Acceptance Criteria

1. **Halo as a composition, not a monolith.** The halo archetype is expressed as
   an ordered list of library modules in `ARCHETYPES["halo"]` (reusing `shank`,
   `seat`, `prong_setting` for the center; adding `accent_seat` and
   `accent_prong` for the ring), fused by the existing `compose()`. No bespoke
   monolithic halo builder. Verified by a test asserting `ARCHETYPES["halo"]` is
   a composition and that `compose(halo_spec)` returns a single solid.
2. **RingSpec discriminated union.** `RingSpec` is a discriminated union over
   `archetype`. A halo spec validates into a `HaloSpec` carrying a `Halo` group;
   a solitaire spec still validates into `SolitaireSpec`. A halo spec missing the
   `halo` group, or a solitaire spec carrying one, is rejected with a field-level
   error naming the offending field. Extra fields still forbidden. The flat-7
   `from_params`/`to_params` round trip stays lossless and defaults to solitaire
   (exact-equality property test still green).
3. **Halo fields documented.** `halo_stone_diameter`, `halo_stone_count`,
   `halo_gap`, `halo_stone_height` are added with the ranges and defaults below,
   documented in `docs/parameter-ranges.md`, and reflected in the regenerated
   JSON Schema under `docs/ringspec/`.
4. **Castable by construction across the range.** For all in-range halo inputs:
   min wall 0.8mm, min accent tip 0.7mm, min prong tip 0.7mm hold. The per-module
   in-kernel self-checks (`accent_seat`, `accent_prong`) return no violations on
   raw geometry across the parametric range (the RNG-17 bar, not repair-into-
   castability).
5. **Raw watertight golden halo.** The raw (pre-repair) STL for the golden halo
   (solitaire defaults + halo defaults) is watertight, zero non-manifold edges,
   single body, asserted directly on `to_stl_bytes(compose(halo_spec))` without
   calling `validate_and_repair`.
6. **Endpoint returns a clean halo.** `POST /generate-ring` with a halo RingSpec
   returns a trimesh-loadable binary STL with `X-Mesh-Repaired: false` on the
   golden halo; `?format=step` returns STEP. Castability violations and malformed
   halo specs return a 400 JSON error naming the field.
7. **Frontend exposes halo fields.** When the halo archetype is active, the form
   shows the four halo fields (pre-filled with defaults, editable) and hides them
   for solitaire. Archetype selection drives which fields render. WCAG 2.1 AA
   holds (labels, contrast, keyboard, the mesh indicator conveys state by
   text/icon as well as color).

## Approach

Compose over the RNG-16 library; add the two accent primitives and the union.
Build in four checkpoints, each a trustworthy commit (tests green, no
half-written module), per the CLAUDE.md checkpoint-at-module-seams rule:

- **Checkpoint 1 (contract).** Refactor `RingSpec` into the discriminated union
  (`SolitaireSpec`, `HaloSpec`), add the `Halo` group, extend `castability.py`
  with halo floors, keep `from_params`/`to_params` defaulting to solitaire for
  the flat-7 back-compat, regenerate the JSON Schema and `docs/parameter-
  ranges.md`. Existing suite + round-trip property test green. No geometry yet.
- **Checkpoint 2 (accent primitives).** Add `accent_seat` and `accent_prong`
  modules (build + in-kernel `check`), register in `MODULES`, own tests
  (parametric range, castability floors, raw per-solid watertightness). Reusable
  by RNG-10/11.
- **Checkpoint 3 (composition).** Add the `halo` placement module (rings the
  accents around the center, shares common-prongs between neighbours) and
  `ARCHETYPES["halo"]`; epsilon-overlap fuse; golden-halo raw watertight test;
  `X-Mesh-Repaired: false`.
- **Checkpoint 4 (wire-up).** `/generate-ring` halo dispatch (validate through
  the union, 400 naming the field on bad input) and the frontend halo fields with
  archetype-driven rendering. Browser QA.

New modules follow the existing `SimpleModule` adapter pattern; placement math
reuses `_common.clamps()`/`placement()`. Shared-prong count/geometry between
neighbouring accents is a build-time design detail for the architect, bounded by
the 0.7mm tip and 0.8mm wall floors.

## Halo field ranges + defaults

Sized for a ~6.5mm (approximately 1ct round) center stone.

| field                 | min | max | default | notes                                                        |
|-----------------------|-----|-----|---------|--------------------------------------------------------------|
| `halo_stone_diameter` | 0.9 | 2.5 | 1.3     | accent melee; floor keeps the accent tip >= 0.7mm castable   |
| `halo_stone_count`    | 8   | 24  | 14      | single row around a 6.5mm center at ~1.3mm accents           |
| `halo_gap`            | 0.3 | 1.5 | 0.5     | center-girdle to halo-ring spacing; guards the 0.8mm wall    |
| `halo_stone_height`   | 0.8 | 3.0 | 1.2     | real bearing depth for the accents                           |

`halo_stone_count` is an int; categorical snapping from noisy input is a vision
concern (RNG-12), not this contract. Ranges are structural caps on the model;
the casting floors that couple these fields (wall between center and accents,
accent tip vs. `halo_stone_height`) are enforced in `castability.py`.

## Edge Cases

- **`halo_stone_count` at bounds (8, 24):** valid; both must produce a watertight
  golden-style ring.
- **`halo_gap` at min (0.3):** if the resulting wall between the center seat and
  the halo ring would drop below 0.8mm for the given center + accent sizes,
  `validate_castability` returns a violation naming `halo_gap` (a 400, not a
  silent clamp).
- **Small accents (`halo_stone_diameter` near 0.9):** the accent bearing/tip must
  still resolve to >= 0.7mm by construction, or a castability violation is raised.
- **Accents crowd the ring (large count + large diameter at small gap):**
  neighbouring bearings would overlap through the center; `validate_castability`
  flags the geometric impossibility, naming the field.
- **Solitaire spec sent with a `halo` group, or halo spec missing it:** schema
  rejection with a field-level error (union discriminator).
- **`prong_count` (center) still constrained to {4, 6}:** unchanged; halo does
  not relax it.
- **Malformed/empty body:** existing top-level 400 behavior preserved.

## Constraints

- Casting floors are non-negotiable: min wall 0.8mm, min accent/prong tip 0.7mm,
  single watertight manifold, zero non-manifold edges on export.
- RNG-17 bar: raw (pre-repair) golden-halo STL is watertight;
  `X-Mesh-Repaired: false` on canonical input. `validate_and_repair` stays as the
  safety net, not a crutch.
- Max 300 non-blank LOC per source file; split modules if needed (the union
  refactor may push `models.py`; split into a package if it exceeds the cap).
- No new top-level dependencies (Pydantic and build123d already present).
- No JS frameworks; vanilla JS only. WCAG 2.1 AA for the new form fields.
- Solitaire behavior unchanged: parity (RNG-13 bbox/volume tolerances) and the
  flat-7 round trip must stay green.
- mm units, floats throughout; casting constants referenced from their single
  source, never duplicated.

## Scope Boundaries

**In scope:** the `HaloSpec`/`SolitaireSpec` discriminated union + `Halo` group;
`accent_seat` + `accent_prong` primitives; the `halo` composition module and
`ARCHETYPES["halo"]`; halo castability rules; `/generate-ring` halo dispatch;
frontend halo fields; JSON Schema + `docs/parameter-ranges.md` updates; tests.

**Out of scope (deferred):**
- Vision-driven population of the halo archetype (RNG-12).
- Trilogy (RNG-10) and pave/channel (RNG-11), which will reuse the accent
  primitives introduced here.
- Mixing halo with other archetypes in a single ring.
- Double halos / multi-row halos (single accent row only in v1).

## Success Metrics

- Golden halo raw STL: watertight, zero non-manifold edges, single body,
  `X-Mesh-Repaired: false`.
- Castability floors hold for 100% of in-range halo inputs (property/range test).
- 100% of malformed halo specs rejected with a named offending field.
- Solitaire parity and flat-7 round-trip identity still hold (no regression).
- Full existing suite green after each checkpoint.

## Design Notes + Dependencies

- Builds on RNG-16 (`Module` Protocol, `MODULES`/`ARCHETYPES`, `compose`) and
  RNG-17 (watertight by construction; the accent primitives must meet that bar on
  raw geometry).
- New geometry files: `ringcad/geometry/accent_seat.py`,
  `ringcad/geometry/accent_prong.py`, `ringcad/geometry/halo.py`, plus
  `_castability.py` check functions and `MODULES`/`ARCHETYPES` entries.
- RingSpec changes: `ringcad/ringspec/models.py` (union + `Halo`),
  `ringcad/ringspec/castability.py` (halo floors), `adapters.py` (unchanged
  behavior, defaults to solitaire), regenerated schema under `docs/ringspec/`.
- Endpoint: `ringcad/app.py` halo dispatch through the union.
- Frontend: `templates/index.html`, `static/app.js`, `static/styles.css`
  (archetype selector drives field visibility).
