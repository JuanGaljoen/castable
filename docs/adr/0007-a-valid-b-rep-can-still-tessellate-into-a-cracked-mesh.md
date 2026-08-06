# 0007 — A valid B-rep can still tessellate into a cracked mesh

**Date:** 2026-08-05
**Status:** Accepted
**Context:** RNG-19 CP2 (claw finishing)

## What happened

Tapering the centre claws meant removing a tip node that was a sphere of
`tip_r * 1.45` — a ball wider than its own shaft. Removing it split one claw's
upper half off as a separate solid at `stone_diameter=2.0`.

The cause was not the taper. Those oversized tip balls were **1.16mm across a
0.92mm gap** between adjacent claws, so they had been overlapping *each other*
into a ring, welding all six claws together at the top. Every claw joint below
was only ever **tangent** — cone rim landing exactly on the node sphere's
equator — and the accidental weld had been carrying connectivity past it.

The obvious fix made things worse. Giving cone and sphere a genuine overlap,
first by thinning the cone radially, then by extending it along its axis, left
the B-rep **valid, single-solid, and correct** while the exported STL cracked:

```
solids 1 · is_valid True · 74 faces   ->   non_manifold_edges 265
```

Radial inset failed on 2 of 18 grid points; axial extension failed on 6 of 7
sampled. Equal radii make the cone tangent to the sphere and OCCT **merges the
two surfaces into one smooth face**. Give them a real intersection and you get an
intersection *circle* — small, high-curvature, and exactly what the tessellator
cracks along.

## The lesson

**This construction depends on tangency to tessellate.** That inverts the usual
rule. `docs/adr/0001` and the RNG-17 work taught us to avoid tangency and prefer
volumetric overlap, because tangency leaves seams in the *fuse*. Both are true,
and they pull in opposite directions for a sphere-and-cone chain:

| | tangent joins | overlapping joins |
|---|---|---|
| fuse | may leave a seam | reliable |
| tessellation | clean (surfaces merge) | cracks on the intersection circle |

So when a joint must be robust, the answer is **fewer joints, not
better-overlapped ones**. Dropping the claw's mid node — leaving base → girdle →
tip, which is what a cast claw actually does — removed the failing joint
entirely and made all 18 grid points single-solid and watertight.

## How this differs from ADR 0005

`docs/adr/0005` is "a passing fuse can still have DROPPED bodies": the mesh
reports watertight and the metal is simply gone. This is the mirror image —
**the solid is perfect and the mesh is wrong.** They need different instruments:

- 0005 → assert **volume** on the mesh.
- 0007 → check `len(solid.solids())` and `solid.is_valid` on the **B-rep**, then
  check watertightness on the **mesh**, and treat a disagreement between them as
  a tessellation problem rather than a geometry one.

Checking only one side hides the other. In this case the mesh said "not
watertight" while the geometry was flawless, and three separate fix attempts were
aimed at geometry that was never broken.

## Consequences

- `prong_setting` claw node radii **must equal** the radii of the cones meeting
  there. This is load-bearing, not incidental, and is commented as such.
- When watertightness fails, establish **which representation is wrong** before
  changing geometry: `solid.is_valid` and `len(solid.solids())` first, mesh
  second.
- Prefer removing a joint over reinforcing one.
