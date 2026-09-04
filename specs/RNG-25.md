# RNG-25 — Shank profile family (cross-section)

**Type:** feature · **Branch:** `feature/rng-25-shank-profile-family` · **Frozen:** 2026-09-04

Classification: **feature** — full spine, three checkpoints at module seams.

## Problem

The band is roughly half a ring's visual mass and ours has exactly one shape. `_common._band_section`
builds a single hardcoded `Ellipse(th/2, w/2)` at each of 96 ring angles and pairwise-lofts them, so
every ring the app has ever generated has the same cross-section whatever the photo showed. This is
the spec-widening half RNG-19 explicitly fenced off, because it touches the contract vision populates.

## What research changed (docs/research/shank-cross-section-profiles.md)

Three corrections to the ticket as written. All three are load-bearing.

1. **Comfort fit is not an outer shape.** It is *purely* a domed inner surface, and the trade pairs it
   with every outer profile independently — Stuller stocks "Half Round Comfort Fit" and "Comfort-Fit
   Heavy Knife Edge" as separate SKUs. The ticket's four names are a 2x2 of outer x inner. **Settled**,
   four independent sources including a wire-stock manufacturing definition.
2. **Our current ellipse is "court"** — domed outside, domed inside. Today's geometry already has a
   trade name, so the defaults preserve it by construction rather than by special case.
3. **"Graduated" is not a band silhouette.** It conventionally describes accent-*stone* sizing along a
   band. The term for a narrowing band is "tapered" = `Shank.shank_taper`, already shipped. **That
   scope item is dropped, not built** — it becomes a `CLAUDE.md` vocabulary note.

`docs/reference/band-profiles.png` (added 2026-09-04) confirms all of the above and **corrected the
schema on its first read**: it draws a THIRD axis, the band's side walls (`Flat Sided Court` differs
from `Court` only in flat vs rounded edges; `Soft Square` is the same on `Flat`). Deliberately out of
scope — filed as **RNG-42**.

## Scope

**In:** the cross-section family as two orthogonal axes across every archetype; the knife-edge apex
made castable by construction; vision reporting it; the form exposing it.

**Out, filed:** cathedral shoulders (**RNG-43** — an understructure that must integrate with the
`gallery` connectivity standard; setting attachment, not band shape). Side-wall axis (**RNG-42**).
"Graduated" — dead by research.

## Success criteria (the bar Verify checks)

- [ ] Every outer x inner combination generates a single **raw** watertight manifold, zero non-manifold
      edges, no repair — asserted on `to_stl_bytes(compose(spec))` directly (the RNG-17 bar).
- [ ] Omitting both fields yields geometry **bit-identical** to pre-RNG-25 for solitaire, halo, trilogy
      and side-stone (the golden validations).
- [ ] `band_thickness` (thickness at the band's centre line) still clears 0.8mm for every profile; the
      knife-edge apex is at least 0.8mm wide across the band, **by construction**.
- [ ] `head_r` is derived from the profile in ONE place, read by both the builder and the castability
      check — no ADR-0002 drift.
- [ ] The 7-param round trip stays lossless (`from_params` defaults, `to_params` drops).
- [ ] Vision reports the profile it sees; the form exposes it as an editable control, WCAG 2.1 AA.
- [ ] Full existing suite green.

## The profiles (6)

Two fields on `Shank`, both defaulted so pre-RNG-25 specs are untouched:

```python
outer_profile: Literal["domed", "flat", "knife_edge"] = "domed"
inner_profile: Literal["domed", "flat"] = "domed"
```

| `outer_profile` | `inner_profile` | Trade name | On the sheet |
|---|---|---|---|
| `domed` | `domed` | **Court** — *today's geometry* | ✅ |
| `domed` | `flat` | **D-section** (half-round) | ✅ |
| `flat` | `domed` | **Flat court** (US "comfort fit") | ✅ |
| `flat` | `flat` | **Flat** | ✅ |
| `knife_edge` | `flat` | **Knife-edge** | ✅ |
| `knife_edge` | `domed` | **Comfort-fit knife-edge** | — (Stuller SKU) |

Two enums rather than one five-name enum because the trade's own vocabulary is a product of two axes
(§1a of the research note), so vision answers two easy questions instead of one hard five-way one, and
RNG-42's third axis composes rather than multiplying an enum.

`inner_profile` is an enum, not a bool, so the research note's "shallow court" (eased edges only) is a
new value rather than a schema change from `bool` to `Literal`.

## Approach

**A `SectionProfile` in `ringcad/ringspec/sections.py`, kernel-free, mirroring `ringspec/cuts.py`.**
Spec layer owns the section FACTS; geometry layer owns the kernel CONSTRUCTION. Same split RNG-33 used
for `CutProfile` / `StoneOutline`, and for the same reason: the castability check and the builder must
ask one source rather than each deriving it (ADR-0002).

Rejected: branching on the profile inside `_band_section`. That scatters the same `if` across the
builder and the gate — exactly what `outline.py`'s own docstring rejects — and duplicates `head_r`.

### The section, parametrically

Let `s` in `[-1, 1]` be the across-band coordinate (`s = 2u/w`). A profile answers, in units of `th`,
the radial offset of its inner and outer boundary from `inner_r`:

```
inner_flat(s)  = 0
inner_domed(s) = 0.5 * (1 - sqrt(1 - s^2))
outer_flat(s)  = 1
outer_domed(s) = 0.5 * (1 + sqrt(1 - s^2))
outer_knife(s) = 1                        for |s| <= a
                 (1 - |s|) / (1 - a)      for |s| >  a
```

`domed` + `domed` reproduces the current ellipse exactly: `inner_r + th/2 -+ (th/2)sqrt(1-s^2)`.

**Every profile reaches full thickness `th` at mid-width** (`outer(0) = 1`, `inner(0) = 0`), so
`head_r = inner_r + bt * t_taper` is unchanged by the profile. Deriving it from `SectionProfile` is
therefore pure **de-duplication**, not a geometry move — which is what makes criterion 4 cheap.

### The knife-edge apex: by construction, not by gate

`a = MIN_WALL_MM / band_width` gives a flat crown exactly `MIN_WALL_MM` wide across the band, always.
**So there is no new castability rule and no new violation code.** The apex cannot be too sharp because
it is not expressible; that is the RNG-17 "castable by construction" bar rather than a gate that fires
after the fact, and it is strictly stronger than the rule the ticket asked for.

A consequence worth naming: as `band_width` approaches `MIN_WALL_MM`, `a` approaches 1 and the knife
edge degenerates smoothly into a flat band. That is geometrically correct and castable, so it is
allowed rather than rejected — refusing it would need an invented "how knife-edge is knife-edge
enough" threshold, and the research found no such figure.

**0.8mm is OUR number, not a trade figure.** No published knife-edge apex minimum exists; the
researcher checked retailer glossaries, UK profile manufacturers, CAD tutorials and one CAD design-floor
guide, and recorded where it looked. We take `MIN_WALL_MM` because a shank is a structural external wall
and our own cited classed-floors table puts those at 0.8mm (setting elements 0.5mm, micro-pave 0.35mm).
The note names one unsearched lead — Materialise / Shapeways "sharp edge / fin feature" minimums — if a
future pass wants it cited rather than chosen.

### What the min-wall invariant actually is

**Found at Design, and it changes a ticket AC.** `Ellipse(th/2, w/2)` is a FULL ellipse: at `s = +-1`
the section has **zero thickness**. Every ring we have ever shipped has knife-thin band edges, and the
trade sheet draws Court as exactly that lens. `_min_wall` never noticed because it checks the
`band_thickness` *field*, never the section.

So the ticket's "min wall 0.8mm holds across the full parameter space for every profile" is **already
false today**, at the section boundary, and correctly so. The invariant is therefore stated on a
defined measure: **`band_thickness` is the thickness at the band's centre line, and that is what clears
0.8mm.** The existing field-level check is right and stays unchanged. No new general section rule —
writing one would fail our own current geometry, which is the ADR-0002 failure in a new costume.

## Checkpoints

- [ ] **CP1 — contract + facts.** `SectionProfile` and the six profiles; `Shank.outer_profile` /
      `Shank.inner_profile`; `head_r` derived from the profile in one place.
      · files: `ringcad/ringspec/sections.py` (new), `ringcad/ringspec/models.py`,
      `ringcad/ringspec/castability.py`, `ringcad/ringspec/adapters.py`,
      `tests/test_sections.py` (new), `tests/test_ringspec_shank_profile.py` (new)
- [ ] **CP2 — geometry.** The section face, and `_band_section` delegating to it; court keeps its
      literal `Ellipse` call so circular sections stay bit-identical (the `RoundOutline` precedent).
      · files: `ringcad/geometry/section.py` (new), `ringcad/geometry/_common.py`,
      `tests/test_shank_profiles.py` (new)
- [ ] **CP3 — vision + UI wire-up.** Vision reports the two axes; the form exposes them under their
      trade names.
      · files: `ringcad/classify.py`, `templates/index.html`, `static/app.js`, `static/photo.js`,
      `tests/test_classify_schema.py`, `tests/test_classify.py`, `tests/test_backend.py`

## Tests, and the seams they pin

**CP1** — `sections.py` is a pure-function seam, so it is tested directly and offline:
boundary values at `s = 0, +-0.5, +-1` for all six profiles; `domed`+`domed` reproduces the ellipse
identity to floating tolerance; `outer(0) == 1` for every profile (the `head_r` invariant); the apex
fraction yields exactly `MIN_WALL_MM` of crown at several band widths; `a -> 1` degeneracy at
`band_width == MIN_WALL_MM`. Plus: defaults round-trip losslessly through `from_params`/`to_params`,
and `castability` and `_common` produce the *same* `head_r` for every profile (the anti-drift test).

**CP2** — through the public builder, never internals: `compose(spec)` for all six profiles is a single
raw watertight body with zero non-manifold edges and non-zero volume (ADR-0005: assert VOLUME and BODY
COUNT, not just watertightness); the default spec's STL bytes are unchanged against the golden
solitaire / halo / trilogy / side-stone.

**CP3** — `tests/test_classify_schema.py` guards ADR-0004 (both new fields required, no defaults, no
unions added — they are plain `str`, so the 16-union cap is untouched); `to_spec` maps them and falls
back to the court default on an unrecognised value; `/generate-ring` accepts the structured fields.

## Risks

1. **`head_r` de-duplication touches every archetype's `placement`.** Mitigated by the parametric fact
   that every profile reaches full `th` at mid-width, so the value should not move at all — the golden
   validations are the guard, and any movement is a red flag, not a rebaseline.
2. **Knife-edge on the side-stone channel band.** RNG-39 already documents degenerate geometry there
   with elongated centre stones; a ridged outer surface is a new stressor on the groove cut. The RNG-33
   guard (400 when the mesh comes back in pieces) already covers it; if it fires, that is RNG-39 reached
   by a new route, not a new defect.
3. **A defect that renders plausibly.** Getting an inner surface flat where it should be domed produces
   a perfectly castable, perfectly wrong band. `docs/reference/band-profiles.png` exists precisely for
   this, and Verify compares a render per profile against it — that, not the suite, is what caught every
   RNG-19 and RNG-33 defect (ADR-0008).

## Chronicle candidates

- The lens-tip finding: a floor that sounds strict, is universally believed, and is quietly violated by
  the geometry it guards — because it is enforced on the FIELD and not on the ARTIFACT. Sibling of
  ADR-0002 and of ADR-0006's "validation gates need it more urgently than builders".
- Castable **by construction** beating a gate rule: the apex needed no violation code because the
  unsafe value was made inexpressible.
