# OpenSCAD Parametric Solitaire Ring Template

## Ticket
RNG-1 (Jira project RNG) — *blocks* RNG-2 (Flask backend)

## Problem
Hand-modelling a castable solitaire ring in CAD is slow and error-prone, and the
output often violates lost-wax casting constraints (thin walls, fragile prongs,
non-manifold geometry) — defects that only surface at the caster, wasting time
and metal. A parametric OpenSCAD template makes the ring geometry *correct by
construction*: every ring generated from 7 numeric parameters is guaranteed
watertight and within casting limits. It is the reliable geometry foundation the
rest of the app (backend, viewer, photo flow) builds on.

## Users
No human edits the `.scad` file directly.

- **Primary (production, machine):** the Flask backend (RNG-2), at generation
  time — injects the 7 parameters via OpenSCAD `-D` command-line overrides, runs
  OpenSCAD headless via `subprocess`, and gets an STL back on each
  `/generate-ring` request.
- **Secondary (this phase, human):** the developer, running OpenSCAD from the
  CLI/GUI to eyeball geometry, tweak a parameter, and confirm the model is a
  proper solitaire ring within casting limits before any UI exists.
- **Ultimate downstream beneficiary:** the **jeweller**, who uploads a photo or
  fills the form and — through later tickets — has this template turn their input
  into castable geometry. They never see the SCAD.

## Success
Running OpenSCAD headless on `scad/solitaire.scad` with any valid set of the 7
parameters produces a single watertight STL of a recognisable solitaire ring — a
round band, four or six prongs holding an (empty) seat for the stone, on a
gallery/setting — such that:

- mesh is **watertight** with **zero non-manifold edges**;
- **no wall is thinner than 0.8mm** and **no prong tip is narrower than 0.7mm**,
  anywhere — guaranteed by construction (`max()` clamps), not by post-hoc
  measurement;
- all four modules (`shank`, `gallery`, `prongs`, `seat`) are fused into **one
  connected solid** (nothing floating or merely touching);
- changing **any** parameter regenerates correctly-updated geometry with the same
  guarantees (no broken/self-intersecting mesh).

Concretely, "done" = a committed `scad/solitaire.scad`, a reusable `trimesh`
mesh validator, and an automated parameter-sweep test proving the guarantees
across representative parameter sets.

## Acceptance Criteria
- [ ] AC1: `scad/solitaire.scad` defines four separate modules — `shank()`,
      `gallery()`, `prongs()`, `seat()` — that `union()` into a single solid.
- [ ] AC2: All 7 parameters are wired through and overridable via OpenSCAD `-D`
      on the command line: `inner_diameter`, `band_width`, `band_thickness`,
      `stone_diameter`, `stone_height`, `prong_count`, `setting_height`.
- [ ] AC3: Minimum wall thickness **0.8mm** is enforced by construction — a
      deliberately too-thin input (e.g. `band_thickness=0.3`) still renders a
      band that respects the 0.8mm floor.
- [ ] AC4: Minimum prong tip diameter **0.7mm** is enforced by construction —
      prong tips never render below 0.7mm regardless of input.
- [ ] AC5: `prong_count` only supports **4 or 6**; any other value snaps to **4**
      and emits an OpenSCAD `echo` warning.
- [ ] AC6: An **oversized stone** (`stone_diameter`/`stone_height` too large for
      the band) renders valid (still watertight, single-body) geometry and emits
      an `echo` warning; no hard clamp on stone size.
- [ ] AC7: A reusable `trimesh`-based mesh validator asserts: `is_watertight`,
      zero non-manifold edges, exactly **one connected component**.
- [ ] AC8: An automated **parameter-sweep** test renders a matrix of
      representative parameter sets — {4,6} prongs × {child / average / large
      finger} × {thin / thick band} + one oversized-stone case — and runs the
      validator on every rendered mesh; all pass.
- [ ] AC9: Each render in the sweep completes within a sane time budget and
      produces a reasonable STL size; `$fn` (facet resolution) is pinned to a
      value that is smooth yet fast enough for per-request backend rendering.
- [ ] AC10: A pinned **golden default ring** renders from defaults
      (`openscad -o output/ring.stl scad/solitaire.scad`) with no errors and
      passes the validator — usable as a smoke test and the reference mesh for
      RNG-4's viewer.
- [ ] AC11: Clamp/snap warnings are emitted on OpenSCAD **stderr** and asserted
      by the test suite (the exact surface RNG-2 forwards to the UI).
- [ ] AC12: The sane parameter ranges discovered during the sweep are recorded
      (in this spec / a notes file) to feed RNG-3's form defaults and bounds.

## Edge Cases
- **Sub-minimum thickness** (`band_thickness=0.3`, thin gallery/prong values):
  clamp silently up to the 0.8mm / 0.7mm floors; geometry stays castable.
- **`prong_count` ∉ {4,6}** (5, 0, float): snap to **4** and `echo` a warning;
  never render a broken setting.
- **Oversized stone** (`stone_diameter` ≥ `inner_diameter`, huge `stone_height`):
  render valid-but-ungainly geometry + `echo` warning; treated as valid, not an
  error.
- **Zero / negative / non-numeric params:** clamp to a small positive minimum so
  the mesh is never degenerate, empty, or non-manifold.
- **Very small `inner_diameter`** (child size, ~14mm) and **very large** (~23mm):
  band stays a closed, single-body ring at both extremes.

## Out of Scope
- **Placeholder preview stone** — a nice future add-on once the base works. Would
  be non-cast, preview-only geometry kept *separate* from the watertight casting
  mesh so it can never break the manifold guarantee. **Not built in RNG-1.**
- Flask backend / `subprocess` integration (RNG-2).
- Trimesh **auto-repair** (RNG-5) — RNG-1 only *detects*/validates; the validator
  is written to be extended by RNG-5.
- Any UI, viewer, or photo-classification work (RNG-3 / RNG-4 / RNG-6).

## Preserved Behaviour
Greenfield — no runtime behaviour to protect yet. The frozen **contracts** that
downstream tickets depend on:

- The **7 parameter names** exactly as specified — they become the backend's
  JSON keys; renaming breaks RNG-2.
- The **four module names** (`shank`, `gallery`, `prongs`, `seat`) and their
  union into one manifold.
- Stable file path **`scad/solitaire.scad`**, driveable **headless via CLI** with
  **`-D name=value`** overrides (the backend's integration mechanism).
- **STL** as the export format.
- The non-negotiable **casting constraints** (0.8mm wall, 0.7mm prong tip,
  watertight, zero non-manifold edges) hold for every future change.

## Manual Test Steps
1. **Default render:** `openscad -o output/ring.stl scad/solitaire.scad` →
   completes with no errors.
2. **Visual check:** open `output/ring.stl` → visibly a solitaire ring (round
   band, raised setting, prongs around an empty seat).
3. **6-prong override:**
   `openscad -D 'prong_count=6' -D 'inner_diameter=18' -D 'stone_diameter=7' -o output/ring6.stl scad/solitaire.scad`
   → 6 prongs, larger finger size, larger seat.
4. **Automated suite:** `pytest tests/test_geometry.py` → parameter sweep +
   validator all green.
5. **Trigger clamps/snaps:**
   `openscad -D 'band_thickness=0.3' -D 'prong_count=5' -o output/ring_clamp.stl scad/solitaire.scad`
   → stderr shows warnings; test confirms band meets 0.8mm floor and prong count
   snapped to 4.
6. **Extremes sweep:** render `inner_diameter=14` and `inner_diameter=23` → both
   stay closed, single-body, watertight.

## Verification Approach (bigger-picture rationale)
Built as a **reusable harness**, not throwaway manual checks, because RNG-2 and
RNG-5 repeat this exact "render → validate mesh" loop on every request:

1. **Shared `trimesh` validator** = single source of truth for "is this mesh
   castable"; RNG-5 extends it with auto-repair, RNG-2 calls it before returning
   STL. Not buried inside a test.
2. **Parameter-sweep test** (matrix, not single renders) = regression net
   protecting casting guarantees against arbitrary user/photo-derived inputs.
3. **Render cost treated as production concern** — pin `$fn`, assert render time
   and STL size, to pre-empt RNG-2 timeouts.
4. **Assert on stderr** — pins the exact warning surface RNG-2 forwards to the UI.
5. **Golden default ring** — smoke test + reference mesh for RNG-4's viewer.
6. **Record sane parameter ranges** — feeds RNG-3 form defaults/bounds from
   reality, not guesses.
Manual visual eyeballing remains the final 10% (a mesh test can't confirm it
*looks* like a ring).
