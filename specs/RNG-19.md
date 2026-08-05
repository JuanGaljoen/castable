# RNG-19 — Geometry aesthetic refinement

Make the generated rings read as jewelry rather than as fused parametric
primitives, by refining the **shared modules** so every archetype inherits the
improvement. No RingSpec schema change (that is RNG-25); no viewer/material work
(that is RNG-27).

## The two findings that shape the build

1. **The band has no sharp edges to fillet.** `_common.band()` lofts 96 `Ellipse`
   cross-sections and fuses the wedges, so the section is already oval. What makes
   it read as a swollen tube is the *proportion curve* — `SHANK_TAPER = 1.7`
   flaring the band 70% at the head, driven by `_head_t`'s `((1+cos)/2)**1.5`.
   The band lever is profile and taper, not fillets.
2. **The claws are a wire armature.** `prong_setting` builds each claw as spheres
   of constant `wire_r ≈ 0.5mm` joined by cones — a uniform-thickness tube with a
   ball at every joint. Real cast claws taper continuously from base to tip and
   dome over the girdle.

## The design principle: soften by construction, not by `fillet()`

There is not a single `fillet` or `chamfer` call in `ringcad/geometry/` today.
Adding them is the obvious reading of this ticket and the wrong one: OCC
filleting a 96-wedge fused loft is fragile, and it would put RNG-17's
by-construction watertightness back at risk in `prong_setting` — the exact module
RNG-17's diagnosis found was responsible for *all* of the non-manifoldness
(12 open edges from open-ended claw cones). Shaping the sections and node radii
achieves the same look while the raw-watertight bar holds by construction.

## How this is judged

Aesthetics cannot be asserted in a test, so the two halves are judged separately:

- **Castability + regression** — the fidelity harness, used the way
  `probes/README.md` §"A caveat when comparing before and after" prescribes:
  re-POST the **saved** `probes/output/*.spec.json` to `/generate-ring` rather than
  re-classifying. Vision wanders; geometry is deterministic given a spec. Costs no
  API calls and takes ~30s for all five.
- **Appearance** — human judgement on the geometry, at checkpoint boundaries only.
  Not per iteration, and not by driving the web app.

### Baseline (main @ 323f983, captured 2026-08-05)

Regenerated from the five saved photo-derived specs. All raw watertight,
`X-Mesh-Repaired: false`.

| archetype | volume mm³ | faces | bbox mm |
|---|---|---|---|
| halo-oval | 399.827 | 627514 | 26.8 × 20.53 × 12.3 |
| halo-round | 433.787 | 569388 | 27.04 × 21.03 × 11.8 |
| side-stone | 225.517 | 299292 | 28.08 × 20.1 × 9.5 |
| solitaire-round | 338.688 | 117816 | 28.04 × 21.03 × 9.5 |
| trilogy-oval | 476.054 | 292748 | 29.04 × 32.75 × 9.0 |

**Observation from the baseline:** trilogy spans 32.75mm along the finger axis —
wider than the ring is tall and 50% wider than the halo. The side settings sit
much further out than a real trilogy. A proportion defect found by the numbers
before anyone looked at a render (→ CP3).

## Decision: the parity test gets rebaselined

Ticket Scope says "tune default proportions"; ticket AC says "golden solitaire /
halo / trilogy still validate" against RNG-13's bbox/volume tolerances. These
conflict. **Resolution: rebaseline deliberately**, in the same commit as the
proportion change, with old and new numbers in the commit message. A
characterization test exists to catch *accidental* geometry change; when the
change is the point, updating it with the diff visible is honest, and a flag to
keep both would be ceremony the ticket never asked for.

Consequence: parity stops guarding during this ticket, so the castability
assertions carry that weight — raw watertight, zero non-manifold edges, and a
**volume** assertion per `docs/adr/0005` (a fuse that silently drops bodies still
reports watertight).

## Checkpoints

Per the repo's module-seam rule — each commit trustworthy on its own, tests green,
no half-written module.

- [ ] **CP1 — band.** Taper curve + section profile in `_common.py`
      (`SHANK_TAPER`, `_head_t`, `_band_section`). Most visual mass, lowest risk,
      touches every archetype.
- [ ] **CP2 — claws.** Continuous taper, domed tips, claw-to-seat join in
      `prong_setting.py` and `accent_prong.py`. Highest risk: this is RNG-17's
      module. Volume assertion mandatory (ADR 0005).
- [ ] **CP3 — seat / collar / gallery blends + proportions.** Includes the
      trilogy span defect above, and carries the parity rebaseline.

## Success criteria

- [ ] Refinements at the MODULE level; no per-archetype bespoke shaping.
- [ ] All five saved specs regenerate raw watertight, zero non-manifold edges,
      `X-Mesh-Repaired: false` — the RNG-17 bar.
- [ ] Min wall 0.8mm and min prong tip 0.7mm hold across the in-range space.
- [ ] No RingSpec schema change.
- [ ] Full suite green (3443 baseline), parity rebaselined only in CP3 and only
      deliberately.
- [ ] Each archetype reads as jewelry to the eye, judged at checkpoint boundaries.
