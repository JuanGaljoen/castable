# RNG-23 — Stone shape and cut in RingSpec (oval)
Classification: feature

## Success criteria (the bar Verify checks)

- [ ] RingSpec expresses centre-stone shape; specs without it remain valid and mean round
      (no breaking change, no v2)
- [ ] An oval centre stone generates a single **raw** watertight manifold, zero non-manifold
      edges (the RNG-17 bar: castable by construction, not repair-reliant)
- [ ] Casting invariants hold across the full in-range parameter space for oval:
      min wall 0.8mm, min prong tip 0.7mm
- [ ] Prong placement is shape-appropriate: no prong sits on the tip of the long axis
- [ ] An uploaded photo of an oval solitaire produces an oval model
- [ ] Frontend control present, editable, WCAG 2.1 AA
- [x] **No regression:** existing parity, watertightness and golden tests untouched
      and green

      *Criterion corrected during CP2 (was: "round geometry is bit-identical").*
      The seat's `Torus` path IS exactly preserved (12.990866793 before and after).
      `prong_setting` is not: building claws at girdle points replaces a rotation
      matrix with `cos`/`sin`, moving round volumes by ~2e-7 relative
      (38.268503476 -> 38.268510607). Every parity test passes. Bit-identity was
      achievable only by branching on shape inside `prong_setting`, which is the
      scattering the outline exists to prevent, so the looser-but-true criterion
      was adopted deliberately rather than the promise being quietly reinterpreted.

## Approach

### The abstraction

Today `c["stone_r"]` is a scalar and six sites assume the girdle is a circle. Replace it with
a **stone outline** (`ringcad/geometry/outline.py`) — one small interface, all per-shape maths
behind it. Round is the degenerate case *inside* the abstraction, never a branch beside it.

Consumers split into two kinds, and the interface serves each with only what it needs:

- **Curve-walkers** (`seat`, `bezel`, `prong_setting`, `halo`) place geometry *around* the
  girdle. They need the path and frames along it.
- **Width-consumers** (`trilogy`, `castability` overcrowding) need one number: how far the
  stone reaches toward the flank. Handing them a curve would be a fake dependency.

```
class StoneOutline(Protocol):
    def wire(self)                  -> Wire     # girdle path (sweep/loft along this)
    def prong_angles(self, n)       -> [float]  # where N prongs sit (radians)
    def frame_at(self, theta)       -> (Vector, Vector)   # point + outward normal
    def half_width(self, axis)      -> float    # "x" = across band, "y" = along band
    def min_curvature_radius(self)  -> float    # tightest bend, for castability
```

`RoundOutline(r)` and `OvalOutline(semi_minor, semi_major)`.

### Orientation (derived, not guessed)

`placement()` maps local +Z to the global +X head axis via `Rot(0, 90, 0)`, so **local Y is
global Y is the band-tangential direction** — along the finger. An oval is set N-S by
convention, so the **semi-major axis lies along local Y**. Consequence worth stating: the
trilogy's side stones flank along that same axis, so an oval centre consumes *more* clearance
than a round one of the same `stone_diameter` and can trip overcrowding. That is correct
behaviour, and the check will now say so instead of silently building a collision.

### Prong placement rule

"Off the tips" generalises cleanly: **place prongs so the tips fall exactly midway between two
adjacent prongs.**

    theta_k = tip_angle + (k + 0.5) * 2*pi/n

- n=4 -> 45/135/225/315 (the conventional 10-2-4-8 oval layout)
- n=6 -> 0/60/120/180/240/300 (tips at 90/270 sit 30 degrees clear of any claw)

One formula, no per-count special-casing, and it keeps every claw off the high-curvature apex
where the min-tip floor is hardest to hold. For a round outline the tip angle is meaningless,
so `RoundOutline` returns the existing even spacing `k * 2*pi/n` and geometry is unchanged.

### Schema

`Stones` gains two fields, both defaulted so every existing spec is untouched:

- `shape: Literal["round", "oval"] = "round"`
- `length_ratio: float = 1.0` (ge 1.0, le 2.5) — long axis / short axis

`stone_diameter` keeps its meaning as the **width** (short axis); length is
`stone_diameter * length_ratio`. Chosen over an explicit `stone_length` because a ratio is what
vision can actually see in pixels (it feeds RNG-26 directly) and because `length_ratio = 1.0`
makes round fall out of the same code path.

### No-regression strategy

`RoundOutline` builds the seat with the **existing `Torus`** call, not a sweep. Only
`OvalOutline` sweeps. So round output is bit-identical and the parity/golden suites cannot
regress on a refactor.

## Checkpoints

- [x] CP1 — contract + outline primitive; no consumer changes yet ·
      files: `ringcad/ringspec/models.py`, `ringcad/geometry/outline.py` (new),
      `docs/parameter-ranges.md`, `tests/test_stone_outline.py`, `tests/test_ringspec_schema.py`
- [x] CP2 — centre-stone geometry consumes the outline + castability generalised to curvature ·
      files: `ringcad/geometry/_common.py`, `seat.py`, `prong_setting.py`, `bezel.py`,
      `ringcad/ringspec/castability.py`, `tests/test_oval_geometry.py`,
      `tests/test_oval_castability.py`
- [ ] CP3 — halo walks the outline (arc-length spacing, not equal-angle) ·
      files: `ringcad/geometry/halo.py`, `tests/test_oval_halo.py`
- [ ] CP4 — wire-up: vision reports shape + ratio, frontend control ·
      files: `ringcad/classify.py`, `templates/index.html`, `static/app.js`,
      `tests/test_classify.py`, `tests/test_frontend.py`

## Risks

1. **Curved-on-curved fuse slivers.** The RNG-9 CP3 lesson (`halo.py` docstring): OCCT drops or
   slivers bodies on *tangential* grazes of two curved surfaces. A swept elliptical seat has a
   different surface than a torus, so every claw/rail joint must stay transversal or deeply
   volumetric. Mitigation: reuse the existing overlap discipline; watertightness asserted on raw
   STL per checkpoint, not at the end.
2. **Min-wall at the tips.** An oval's apex curvature is tighter than any round stone's, so the
   seat wall and any bead near the tip is the thinnest metal in the model. This is exactly what
   `min_curvature_radius()` exists to catch; expect to clamp `length_ratio` harder than 2.5 if
   the check says so.
3. **Halo bunching.** Accents at equal *angle* crowd at the tips of an ellipse. CP3 must space by
   **arc length**, which changes `_ring_angles` — a function halo currently shares with nothing,
   so blast radius is contained.

## Out of scope

- Faceting or modelling the gemstone itself (we build metal; the stone is a void).
- Non-round accent/side stones.
- Emerald / cushion / pear / marquise — the cornered and pointed families need a different prong
  primitive (V-prongs) and are a follow-up on this seam.
