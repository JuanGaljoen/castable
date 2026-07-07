# 1. Fuse leaf solids in one general fuse; join transversally, never graze

- **Status:** Accepted
- **Date:** 2026-07-07
- **Context ticket:** RNG-9 CP3 (halo composition); builds on RNG-17
  (watertight by construction)

## Context

The RNG-17 bar is *raw* watertight geometry — a single manifold body with zero
non-manifold edges, with **no** reliance on the trimesh auto-repair gate. RNG-9
CP3 (the halo: a center setting plus a ring of accent settings tied down by a
`gallery`) was the first archetype complex enough to stress this: many small
build123d primitives — a gallery rail, hub and struts, N accent seats, N shared
prongs, the center shank/seat/prongs — must fuse into one watertight body across
the whole in-range parameter band.

Early CP3 geometry failed in ways that *looked* like several unrelated OCCT/mesh
bugs — a null-shape fuse, a compose producing 13 solids with negative-volume
fragments, 47 then 13 non-manifold edges as parameters shifted. Mapping the whole
band **in one parallel pass** (rather than chasing one config per slow build)
showed a single root cause: **the geometry relied on OCCT resolving tangential
curved-surface contacts and on fusing heavy pre-fused bodies — both of which OCCT
does unreliably.** Tolerance tuning did not help (fuzzy `tol=` made it worse); the
problem is topological, not numerical.

## Decision

Two construction rules, enforced in the module library:

### 1. Fuse leaf solids in ONE general fuse — never pairwise-fuse pre-fused bodies

`compose()` collects each module's **leaf** solids via `Module.parts()` and runs a
single general fuse, `leaves[0].fuse(*leaves[1:])`. Simple modules yield one leaf
(their fused `build`); heavy modules like `halo` yield many via `halo_parts`.

OCCT's boolean is far more robust over many small primitives at once than over two
already-fused **compound** bodies. A heavy pre-fused body in a downstream boolean
can make OCCT **silently drop** the op — returning the untouched first operand or
zero/negative-volume garbage, not raising. (Symptom: pairwise-fusing a pre-fused
halo into the center → 13 solids; flattening to one general fuse → one clean
solid.) A module's *own* internal pre-fusion (e.g. `gallery` fusing rail + hub +
struts) is fine; expose leaves only at the seam that crosses into `compose`. This
is the mitigation named in RNG-17 risk #1 ("single-manifold fuse of many small
parts"): additive-only, one general fuse.

### 2. Every joint is transversal or a deep volumetric overlap — never a graze

OCCT slices cleanly through **transversal** overlaps but slivers or drops bodies
where two **curved** surfaces meet **tangentially**; STL meshing emits
non-manifold edges at those grazes and at **coincident planes**. Therefore:

- Join a curved tube (a `Torus` rail) with **flat-faced** feet/struts (a `Box`)
  that punch *through* the tube core — flat planes cut a torus along clean seams.
  (Both `gallery`'s bridge struts and `halo`'s shared-prong feet do this.)
- Keep visible curved features (a `Cone` claw) *above* the curved backbone so no
  curved-on-curved graze exists.
- Never let a derived coordinate land a part's face **exactly** on another's plane
  — a bead-rail top that computed to `== girdle plane` at one height spawned 47
  non-manifold edges. Overlaps must be volumetric with a positive margin scaled to
  feature size.

**Corollary — don't add a second connector where one already welds.** CP3 briefly
carried a bead-rail `Torus` beside the accent seats "to weld the ring." The
`gallery` rail already welded every seat (each accent bearing plunges
`RAIL_OVERLAP` into it), so the bead-rail welded nothing new and only added a
curved-on-curved interface — the *sole* source of every CP3 non-manifold failure.
Removing it made the whole band watertight and ~9x faster. Fewer primitives =
fewer tangency classes. The `gallery` is the connectivity standard for elevated
settings (halo now; trilogy/cathedral next); reach for it before inventing a
bespoke bridge.

## Consequences

- **`Module` grows an optional `parts()`**; `compose` fuses the flat leaf set.
  Solitaire is unchanged (one leaf per module, identical fuse).
- **New modules must follow both rules.** RNG-10 (trilogy) reuses the `gallery`
  and inherits them; any elevated setting should connect through the gallery, not
  a new curved bridge.
- **Debugging discipline** for manifold/fuse failures:
  - Validate via the authoritative path — `to_stl_bytes` → `trimesh.load(
    force="mesh")` → `validate_mesh` (which `merge_vertices()`), i.e.
    `tests.conftest.validate_raw_solid`. `trimesh.is_watertight` on a **raw** STL
    lies (per-triangle duplicate vertices).
  - Map the **whole** parameter band **in parallel** in one pass; fix by
    principle. Separate-looking failures are usually one root cause.
  - Fast signals: assert `len(solid.solids()) == 1` first; a fuse with ~zero
    **delta volume** = a silently-dropped boolean; bound non-manifold edges to a
    spatial region to name the offending interface.
- **Gotcha:** `ringcad/geometry/__init__.py` re-exports `halo` (the function),
  shadowing the submodule — `import ringcad.geometry.halo as H` gives the
  function. Use `importlib.import_module("ringcad.geometry.halo")` for the module.
