# RNG-33 — Stone cuts beyond round and oval (cushion, emerald, pear, marquise)
Classification: feature

## Success criteria (the bar Verify checks)

- [ ] RingSpec expresses cushion, emerald, pear and marquise; specs without a `shape`
      remain valid and still mean round (no breaking change, no v2)
- [ ] Each cut generates a single **raw** watertight manifold, zero non-manifold edges
      (the RNG-17 bar: castable by construction, not repair-reliant)
- [ ] **Body count == 1 and volume > 0** asserted per cut, not only watertightness
      (ADR-0005: a dropped body reports watertight; ADR-0008: so does a sealed void)
- [ ] Casting invariants hold across the in-range parameter space for every cut:
      min wall 0.8mm, min prong tip 0.7mm
- [ ] Prong placement is appropriate to each cut, not a circle stretched: emerald and
      cushion grip the corners; pear and marquise take a V-prong at each point
- [ ] An uploaded photo of a cushion-cut ring produces a cushion-cut model
- [ ] Frontend control present, editable, WCAG 2.1 AA
- [ ] **No regression:** parity, watertightness and golden tests green for round and oval

      *Deliberately "green", not "bit-identical".* RNG-23 had to correct exactly this
      criterion mid-flight: building claws at girdle points replaced a rotation matrix
      with `cos`/`sin` and moved round volumes by ~2e-7 relative. CP3 changes that same
      interface again (`prong_angles` -> `placements`), so the honest bar is stated up
      front rather than reinterpreted later. The seat's `Torus` path IS exactly preserved.

## Approach

### The end-goal test

Per `CLAUDE.md`, progress toward "any ring" is growing the module vocabulary, not piling up
per-style templates. At every fork here the choice is the one that **moves knowledge into the
outline and out of modules, gates and enums**. Today the outline owns its girdle path and
nothing else. After this ticket it also owns prong placement, prong type, its conventional
proportions and how its seat is cut. Modules and gates *ask*; they do not branch, and they do
not keep parallel tables.

### The dependency inversion that makes the gate honest

`castability.py` stays kernel-free and today **re-derives** the ellipse tip radius
(`semi_minor / ratio`), while `outline.min_curvature_radius()` has no production caller at
all. That is the drift ADR-0002 warns about, and four more cuts make it worse.

**New `ringcad/ringspec/cuts.py` — pure math, no `build123d` import.** One `CutProfile` per
cut owning: default ratio, plausible band, corner fraction / exponent, `half_width(axis)`,
`min_curvature_radius()`, `tip_wedge_angle()`, `prong_layout(n) -> [(theta, ProngType)]`.

`castability.py` asks a profile instead of re-deriving (ADR-0009's lesson, new target).
`outline.py`'s classes wrap a profile and add only what needs the kernel: `wire()`,
`frame_at()`, `seat_parts()` / `seat_cuts()`.

Spec layer owns the shape *facts*; geometry layer owns the *kernel construction*. One source.

### Prongs: the outline owns placement, type and count

`prong_angles(n) -> [float]` becomes `placements(n) -> [Placement(theta, type)]` where type is
`round | claw | V`. `prong_count` stays `Literal[4, 6]` and becomes a **preference the outline
may honour or override** — a pear asks for 5 because that is what a pear needs.

Prong **type** is the part that compounds. A V-prong is not a pear feature; it is what every
point and corner needs, so princess, heart, trillion and shield get it free later. Without it,
every pointed cut we ever add is wrong in the one place the trade is unanimous about.

### Seat: bore the negative (ADR-0008, third customer)

Sweeping a collar tube is a *round-stone* technique that survives an ellipse and breaks on
every cornered or pointed outline, permanently. Boring works for any closed outline, including
ones not yet invented. `module.py` needs no new machinery: `side_stone` is cut-only and `halo`
is parts-and-cuts, so `seat` becoming both is an existing shape.

Round and oval keep their existing `tube()` sweep because the parity and golden suites pin
them. **That is migration debt, not a design position** — see Out of scope.

ADR-0008's trap applies: a bore that fails to *open* becomes a sealed void that still reports
watertight, single-solid, all floors met. Assert body count and volume.

### Repair must not change what a thing *is*

`coherence.py` repairs `stone_curvature` by scaling `stones.length_ratio` inversely, so a
marquise at 1.95 can be repaired to 1.05 and handed back as a "marquise" that renders as a
lens. **Repair may change a thing's dimensions; it must not silently change its identity.**
Bound the ratio repair to the cut's own band; fall back to moving `stone_diameter` instead.

## The numbers, and which of them are ours

Per-cut L:W is mandatory, not cosmetic — one shared default makes three of four wrong on sight.

| Cut | Conventional range | Default |
|---|---|---|
| cushion | 1.00-1.05 (elongated cushion 1.20-1.30 is a separate segment) | 1.02 |
| emerald | 1.30-1.50 | 1.40 |
| pear | 1.45-1.75 | 1.60 |
| marquise | 1.75-2.30 | 1.95 |

GIA assigns **no cut grade to fancy shapes** (one is slated for 2027), so these are preference
bands, not standards. We pick a default; we do not call it correct.

**Outline maths (sourced).** Marquise is the intersection of two circular arcs: half-length
`a`, half-width `b`, arc radius `R = (a^2 + b^2) / (2b)`, centres `(0, +/-(R - b))`; the tip is
a **finite wedge**, `theta = 2*atan(a/(R - b))` — ~106 degrees at L:W 2.0, exactly 120 at the
vesica ratio sqrt(3). Emerald's four long sides are genuinely straight (a true octagon).
Cushion's sides genuinely bow *outward*; a superellipse `|x/a|^n + |y/b|^n = 1` models that and
degrades to the existing ellipse at `n = 2`.

**Casting floors confirmed, no change needed.** Our 0.8mm min wall matches Stuller's
structural-wall figure and Materialise's gold figure exactly. Our 0.7mm prong tip sits between
Stuller's 0.45mm prong minimum and Materialise's 0.8mm; Stuller's 0.2mm polishing allowance is
why it must not go lower (0.7 modelled finishes near 0.5).

**Prong conventions (sourced).** Emerald and cushion grip the cut/rounded **corners**, not the
flat sides. Pear takes a V-prong at the point; marquise at both. Stuller states the failure
mode outright: *"Cushions with rounded corners can easily rotate and fall out of a prong
setting"*, prescribing double prongs or a gallery rail. Evenly-spaced angles is precisely what
that warns against.

### Invented — no trade or standards figure found

The GIA G&G Fall 2024 study on these outlines proved unreachable (fetch timed out,
`web.archive.org` blocked, no full-text mirror). A dedicated research pass found **no published
figure anywhere** for the following. They are ours; the next reader may move them freely.

| Quantity | Our value |
|---|---|
| Pear belly position along the length | ~31% from the round end at L:W 1.6, from a tangent-semicircle construction |
| Pear wing transition | tangent continuation |
| Emerald corner truncation fraction | ~15% of the short axis |
| Cushion superellipse exponent | `n ~ 3` (antique/old-mine reads rounder, ~2.5) |
| Pear/marquise tip radius | none — the tip is a vertex, and a visible radius is graded a *defect* |
| V-prong wrap angle | computed from the outline's own tip wedge angle, not guessed |
| Angular positions of pear/marquise side prongs | ours |

Two sit a tier above pure invention, as **documented engineering assumptions** with partial
trade support but no gemological certification: the two-arc marquise construction, and the
45-degree emerald corner face.

**One trap.** A "0.227W" figure circulates in faceting sources for emerald and is **not** the
corner truncation — it is the target P3 *pavilion facet* width during cutting (Jeff Graham,
"Gram Easy Emerald"). Do not reuse it for the plan-view corner. It would have looked like a
cited number and been wrong.

## Checkpoints

- [ ] **CP1 — Cut vocabulary (contract + pure math).** `ringcad/ringspec/cuts.py` with four
      `CutProfile`s; `Stones.shape` widened; per-cut `length_ratio` defaults; `_stone_curvature`
      and `_min_prong_tip` rewritten to ask the profile. No geometry change.
- [ ] **CP2 — Outline classes + bored seat.** Four classes wrapping their profiles; `seat()`
      gains `_parts`/`_cuts`, registered in `MODULES`. Body count and volume asserted.
- [ ] **CP3 — Prong placement and type.** `placements()` replaces `prong_angles()`;
      `prong_setting()` builds a V-prong where the placement says V.
- [ ] **CP4 — Vision + UI wire-up.** `classify.py` schema/prompt/`_stone_shape`; the shape
      `<select>` and per-cut ratio default; `coherence.py` identity guard.

## The ADR-0006 audit (owed by this ticket)

The abstraction only protects consumers that adopt it. Every site still holding the old scalar,
decided in writing:

| Site | Status | Call |
|---|---|---|
| `castability.py:81` `_min_prong_tip` — `stone_diameter` alone, ignores `length_ratio` | **Live; wrong for every new cut** | Fix in CP1 |
| `bezel.py:35` — bore is `c["stone_r"] + _CLEARANCE`, a circle on the short axis | Latent: `bezel` is in `MODULES` but named by **no** archetype, so unreachable | File separately |
| `_castability.py:187` `check_gallery` — rail faces at a constant radius off `stone_r` | Latent: `halo` dropped its gallery; only tests call `gallery()` | File separately; revisit if CP3 uses a gallery rail for cushion |
| `prong_setting.py:48`, `halo.py:147` — peg / hub radii from `stone_r` | Legitimate scale values | Considered, keep |

## Verification

1. Offline suite green; parity and golden green for round and oval.
2. Raw watertight per cut on `to_stl_bytes(compose(spec))` *without* `validate_and_repair`;
   zero non-manifold edges; `X-Mesh-Repaired: false`; **body count 1, volume > 0**.
3. Casting invariants swept over `length_ratio` x `prong_count` x `stone_diameter` per cut.
4. **The real path, not stubs.** Every `classify` test stubs the client — that is how the
   RNG-21 bug shipped invisibly and how three RNG-23 defects passed a green 3413-test suite.
   Run `python probes/fidelity_probe.py` before and after; drive a real upload through the live
   dev server. **Verify the server process is younger than the edit** (RNG-19: "I see no
   change" was twice a stale process; reload is off).
5. Compare each render against `docs/reference/`. No RNG-19 defect was found by a test; all
   four came from a sketch comparison.

## Assets required before Verify (supplied by Juan)

Forge is not blocked; Verify is. Adding either is a file plus a table row, no code change.

- `probes/corpus/` — one real photo per cut (`solitaire-cushion.jpg`, `-emerald`, `-pear`,
  `-marquise`) plus a manifest entry each. Without these, the "cushion photo -> cushion model"
  criterion rests on `solitaire-round.jpg`, which vision happens to read as cushion.
- `docs/reference/` — semi-mount sketches, `pear.png` and `marquise.png` at minimum (the
  pointed cuts are hardest to judge by eye). Bare metal, no stones — what we actually render.

CP4 needs them. If they are not ready, Verify runs degraded and says so explicitly.

## Out of scope

- Faceting or modelling the gemstone itself. We generate the metal; the stone is a void.
- Non-round **accent** and side stones. Centre stone first.
- Widening `prong_count` to per-cut valid sets (5 for pear, 8 for doubled corners).
- Promoting corner fraction and cushion exponent to editable spec fields.
- Migrating round/oval off the swept collar onto the bored seat (one construction).
- `bezel` and `check_gallery` short-axis fixes — both latent, neither user-reachable.
