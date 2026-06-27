# RNG-13 — build123d proof-of-parity for the solitaire

**Date:** 2026-06-27
**Outcome:** ✅ **GO** — adopt build123d (OpenCASCADE B-rep) as the geometry kernel.
**Location:** `spikes/rng13/` — `oracle.py`, `b123d_solitaire.py`,
`run_parity.py`, and this `FINDINGS.md`. `out/` holds the STL/STEP artifacts.

This is the *empirical* spike the earlier read-only research note
(`decisions/2026-06-27-adopt-build123d-kernel`) deferred. It ports the existing
solitaire to build123d and runs it head-to-head against the OpenSCAD output.

## How to reproduce

```bash
.venv/bin/python spikes/rng13/run_parity.py
```

Builds the build123d solitaire from the same 7 params, renders the OpenSCAD
oracle (cached after first run — the SCAD `hull()`s take ~70s at `$fn=32`),
and prints PASS/FAIL for each AC. Artifacts land in `spikes/rng13/out/`.

## Results

| AC | Metric | OpenSCAD | build123d | Verdict |
|----|--------|----------|-----------|---------|
| **AC1 parity** | bbox (mm) | (27.795, 21.283, 7.500) | (27.810, 21.288, 7.500) | Δ ≤ 0.015mm ✅ |
| | volume (mm³) | 383.58 | 389.56 | Δ **1.6%** ✅ |
| **AC2 shell()** | 0.8mm wall vol | — | 289.5 (= exact) | ✅ exact |
| **AC3 STL** | non-manifold edges | 0 | 12 raw → **0 post-gate** | ✅ |
| **AC3 STEP** | valid CAD file | n/a (STL-only) | 2.1 MB, re-imports vol>0 | ✅ net-new |

All four acceptance criteria are met. **GO.**

## What was proven

- **Dimensional parity is essentially exact.** The bounding box matches to
  within 0.015mm on every axis; solid volume is within 1.6%. The kernels were
  asked for the identical ring (same 7 params, same casting clamps).
- **`shell()`/`offset()` enforces a real 3D wall.** Hollowing a 10×10×6 block
  by `offset(amount=-0.8)` yields exactly the analytic 0.8mm-wall shell volume.
  This is the load-bearing capability OpenSCAD CSG cannot do, and it works
  cleanly on the B-rep — castability *by construction*, not post-hoc checking.
- **STEP export is real.** `export_step` writes a 2.1MB STEP that `import_step`
  reads back as a positive-volume solid — true CAD interchange, net-new vs the
  STL-only OpenSCAD path.
- **The existing castability gate carries over unchanged.** `validate_and_repair`
  (the same `ringcad.mesh_validator` gate the OpenSCAD path ships through)
  consumes the build123d STL directly and produces a watertight, 0-nme,
  single-body mesh — with **zero volume change** (389.555 → 389.555), i.e. it
  only welds seams, it doesn't reshape geometry.

## Geometry construction notes (for RNG-15)

The port (`b123d_solitaire.py`) mirrors the SCAD module structure: `_band`,
gallery peg, seat torus, prong claws → one fused solid. Three OCCT lessons that
will save RNG-15 time:

1. **Tapered band = pairwise lofts, not one call.** OCCT could neither loft a
   *closed* loop nor multisection-`sweep` the varying ellipse wires
   ("incompatible wires"). The robust path is to `loft` between each adjacent
   pair of oval sections and `fuse` the wedges — the direct B-rep analog of the
   SCAD swept polyhedron.
2. **Section orientation is the silent killer.** A cross-section's plane normal
   must be the **sweep tangent** `(-sin θ, cos θ, 0)`, not global Z. Get it
   wrong and the ellipse lies flat in the XY plane, the loft degenerates, and
   you get **zero volume with no error**. This one bug accounted for the early
   "volume 38% low / not watertight" readings.
3. **Single batch `fuse`, deduped nodes.** Building claws as sphere→body→sphere
   per segment leaves coincident caps at shared endpoints; incremental `+`
   unions leave seams. Placing one sphere per claw *node* and doing a single
   `solids[0].fuse(*rest)` dropped raw non-manifold edges 24 → 12.

## Honest gaps / residue

- **12 raw boolean-tangency non-manifold edges** remain on the open-basket
  claws (where prong wires meet the seat torus tangentially). They are **fully
  closed by the existing repair gate** with no geometry change, so the shipped
  STL is clean — exactly how the OpenSCAD path already works. Driving them to
  zero *by construction* (guaranteed overlap at each junction, or filleted
  joins) is a tractable polish item for RNG-15, not a blocker.
- **Band shoulder flare** is reproduced (tapered band, volume within 1.6%); no
  outstanding taper gap. The earlier research note's "didn't measure a shelled
  wall / no parity harness" caveat is now resolved by this spike.
- **OpenSCAD oracle is slow** (~70s at `$fn=32`) because of the claw `hull()`s —
  irrelevant post-cutover (build123d builds the ring in ~25s and is in-process),
  but note it if you re-run the oracle.
- **Licensing:** confirm `cadquery-ocp` (OCCT) LGPL terms are compatible before
  ship, per the prior decision note. Not a geometry risk; a compliance checkbox.

## Recommendation

**GO.** build123d reproduces the solitaire to sub-tolerance accuracy, adds the
two capabilities the "any ring" roadmap requires (`shell()` and STEP), and slots
into the existing castability gate without change. Proceed to **RNG-14**
(RingSpec v1) and **RNG-15** (OpenSCAD → build123d cutover). The cutover should
fold the three construction lessons above into the production `shank()` /
`prong_setting()` / `seat()` modules and add the by-construction manifold polish.
