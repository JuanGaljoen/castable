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

- [x] **CP1 — proportions.** Band taper curve in `_common.py` (`SHANK_TAPER`,
      `_head_t`, `_band_section`) plus the trilogy span defect above. Carries the
      parity rebaseline, since this is the checkpoint that moves the numbers.

  **Landed 2026-08-05.** Two changes, both at the module level:

  - **The shank tapers in width only.** `_band_section` applied one factor to
    both axes; now `SHANK_WIDTH_TAPER = 1.35` drives width and
    `SHANK_THICKNESS_TAPER = 1.15` drives thickness. Both live in
    `ringspec/models.py`, not in `geometry/`, because `castability.py` also
    derives `head_r` and `ringspec` cannot import `geometry` — a geometry-side
    constant would have forced the check to keep its own copy. **That drift had
    already happened**: the builder used a module constant while the check read
    the `shank_taper` *field*, so a user setting `shank_taper` moved the check
    and not the geometry (docs/adr/0002). Fixed as a side effect.
  - **The trilogy's side settings no longer splay.** `_side_loc` rotated the
    whole frame by the placement angle; position now keeps the full offset (it
    is a clearance requirement `_trilogy_overcrowding` guards) while the
    orientation eases to `SIDE_TILT_FRACTION = 0.35` of it — ~18° on the corpus
    trilogy's 51° offset.

  Measured on the five saved specs, all raw watertight, `X-Mesh-Repaired: false`:

  | archetype | volume | bbox |
  |---|---|---|
  | halo-oval | 399.8 → 326.4 (−18.4%) | 26.8×20.5 → 25.9×19.9 |
  | halo-round | 433.8 → 340.0 (−21.6%) | 27.0×21.0 → 26.0×20.3 |
  | side-stone | 225.5 → 225.5 (0.0%) | unchanged |
  | solitaire-round | 338.7 → 244.9 (−27.7%) | 28.0×21.0 → 27.0×20.3 |
  | trilogy-oval | 476.1 → 380.8 (−20.0%) | 29.0×**32.8** → 28.0×**27.2** |

  Side-stone at exactly 0.0% is the control: it builds on `FLAT_TAPER`, so a
  correct change must leave it untouched.

  **Process note worth keeping.** The regeneration loop reported the trilogy
  unchanged twice before the real result appeared — the Flask dev server runs
  with reload off, so it kept serving pre-change code, and a `pkill` that
  reported success left the process alive holding port 5000 (which macOS
  ControlCenter also listens on). **Verify the server is younger than the edit
  before trusting a before/after.**
- [x] **CP2 — claw finishing.** Continuous taper, domed tips, claw-to-seat join in
      `prong_setting.py` and `accent_prong.py`. Highest risk: this is RNG-17's
      module. Volume assertion mandatory (ADR 0005).

  **Landed 2026-08-05.** Claws now run base → girdle → tip with radii stepping
  down continuously, finishing in a dome the shaft's own width; `accent_prong`'s
  straight cylinder became a taper, so halo shared-prongs and trilogy side
  settings inherit it. Cross-sections up one claw:

      pre-CP2   4.58 · 4.18 · 3.80 · 4.71 · 6.32    taper, then balloon
      post-CP2  3.92 · 3.61 · 3.32 · 3.13 · 3.05    monotonic

  The base cross-section *shrank*, so nothing got thicker — the research found
  our ~1.0mm claw diameter was already correct trade practice, making this a
  shape fix only. Volumes moved −0.2% to −2.7% across the five saved specs, all
  raw watertight with `X-Mesh-Repaired: false`.

  **The expensive part, recorded in `docs/adr/0007`.** Removing the oversized tip
  ball broke watertightness at `stone_diameter=2.0`: those balls were 1.16mm
  across a 0.92mm gap, so they had been overlapping *each other* into a ring and
  welding all six claws together at the top, carrying connectivity past joints
  that were only ever tangent. Then the obvious fix made it worse — giving the
  cone and sphere a genuine overlap (radially, then axially) left the B-rep
  valid and single-solid while the STL tessellator cracked along the new
  intersection circles: 265 non-manifold edges off a perfectly good 74-face
  solid. **This construction depends on tangency to tessellate**, which inverts
  ADR-0001's prefer-overlap rule, so the fix was fewer joints rather than
  better-overlapped ones: dropping the mid node, which is also what a cast claw
  does. All 18 grid points single-solid and watertight.

- [ ] **CP3 — side-stone channel accents.** Deferred here by RNG-11's closing
      comment ("making the accents read more prominently as fine jewelry is
      deferred to RNG-19"). `docs/jewelry-design-principles.md` §Channel finds this
      is the one archetype **wrong in kind**, not merely unrefined.

  **The defect.** Channel setting means stones sit in a groove cut into the band
  between two walls, with seats cut into the walls' inner faces — **no prongs and
  no per-stone collar at all; that is the definition.** We place an `accent_seat`
  (a `Torus` collar deliberately proud of the band, `ACCENT_EMBED = 0.1`, commented
  "a visible bead") at each stone, retained by two `Torus` rails sitting *on* the
  surface. That is correct halo geometry reused where its premise does not hold —
  a row of raised donuts instead of stones recessed between two rails.

  **The arithmetic that explains RNG-11's shortcut.** A channel groove runs across
  the band's width axis, so it needs `accent_d + 2·MIN_WALL` = 1.5 + 1.6 =
  **3.1mm**. The corpus side-stone spec supplies `band_width: 2.0`. Even the
  smallest legal accent (0.9mm) needs 2.5mm, and the research's own shank table
  puts typical bands at 1.5–3mm. **Real channel-set bands are wide because the
  geometry forces it; our schema lets you ask for a channel on a band that cannot
  physically have one.** RNG-11's raised beads were not only a shortcut — they are
  the only thing that fits in 2.0mm. So CP3 is not a rendering change; it is a
  constraint the archetype has never satisfied.

  **The construction: cut the stones out of the metal.** We render metal only
  (§"The metal-only caveat"), so a channel row *is* the negative of its stones.
  Rather than model a setting, model the band and subtract:

  1. Flat band (`FLAT_TAPER`) — unchanged, now correct for the stated reason.
  2. **Cut the groove** — swept along the accent arc, clear span
     `accent_d − 2·GIRDLE_PENETRATION`, inward from the outer surface. The walls
     are the band's own metal, not rails on it.
  3. **Cut each stone** — a solid of revolution of radius `accent_r` at that
     stone's girdle plane. At 1.5mm across a 1.1mm clear span it bites exactly
     0.2mm into each wall's inner face: **the bearing seats, at the research's
     stated penetration, fall out of the subtraction for free.**
  4. Delete `accent_seat` and both `Torus` rails from `side_stone` entirely.

  **Why this is castable where the additive version was not.** It is purely
  subtractive, so ADR-0007's tessellation cracking (fusing near-tangent bodies)
  has no tangency to crack along — the stone tool overlaps the groove by 0.4mm,
  nowhere near a sliver. Watertightness holds by construction: a cut cannot open a
  solid unless it severs it, and the floor rule forbids that. The ~0.25mm undercut
  never exists as a feature; the smallest cutting tool is a 1.5mm sphere.

  **Three derived castability rules, no schema change:**

      walls   band_width     >= accent_diameter + 2 * MIN_WALL
      floor   band_thickness >= groove_depth    +     MIN_WALL
      depth   groove_depth   >= pavilion clearance, clamped to the floor budget

  **Accepted consequence:** narrow bands are now rejected rather than silently
  built wrong. The fidelity corpus side-stone spec (2.0mm) will fail to generate
  until its band widens — a real red entry, per RNG-22's rule that a declared
  manifest entry with no valid result is reported, not hidden.

  **New seam — subtractive modules.** `compose` is additive-only: it collects
  leaves and fuses, and `DegenerateModuleError` rejects a module contributing zero
  volume. A cut-only `side_stone` contributes no leaves. So the module Protocol
  gains an optional `cuts(spec, c)`, subtracted after the single general fuse, and
  the degeneracy guard accepts a module that declares cuts instead of parts.

  **Landed 2026-08-05.** Built as designed; `accent_seat` and both `Torus` rails
  are gone from `side_stone`, which is now the library's first subtractive module.
  Verified on the REAL path (the RNG-23 lesson), not only in tests:

  | request | result |
  |---|---|
  | stock 2.2mm band | **400**, `shank.band_width`, "needs a 3.100mm band" |
  | fitted 3.1mm band | **200**, raw watertight, `X-Mesh-Repaired: false` |
  | corpus photo's own spec, band widened to 3.1mm | **200**, watertight, no repair |

  The other four saved specs are byte-comparable to their post-CP2 numbers —
  CP3 touches no other archetype, since every non-`side_stone` module declares
  no cuts.

  **A default that would have 400'd.** The form ships `band_width` 2.2mm, so
  selecting Side-stone with stock values posted a spec the new gate rejects —
  the same shape of defect as RNG-23's (the *default* path was the broken one).
  `static/app.js` gains `fitBandToChannel()`, which widens the band to fit when
  the archetype or accent size changes. A user who narrows it back still gets
  the server's violation, which names the field and the required width.

  **Two checks measure the same rule, deliberately.** `_side_stone_channel`
  (ringspec) gates the spec arithmetic before geometry runs; `check_side_stone`
  (in-kernel) measures the CONSTRUCTED cut. The second is not redundant: it
  catches the two drifting apart — a construction that cuts deeper or wider than
  the rule it was cleared against, which is docs/adr/0002's failure mode.

  **A measurement bug worth remembering.** The first `check_side_stone` read
  radial reach off the cut's BOUNDING BOX corners and reported a −3.001mm floor
  on geometry that was fine. A bbox corner is not a point on a solid of
  revolution — it sits well inside the true radius. Measuring over `vertices()`
  is both correct and honest, because those are points the geometry actually
  has. **When a check measures a curved solid, measure its geometry, not its
  bounding box.**

  **Accepted, and now real:** the fidelity corpus's side-stone entry is red. A
  real photo's vision output (2.0mm band) is rejected — a second concrete
  instance of **RNG-32** beyond the tall-stone one, and worth a comment there.

  Still unaddressed from `docs/jewelry-design-principles.md`, out of CP3's scope
  by decision: the trilogy GAP (CP1 eased the tilt but left `side_stone_gap` at
  2.0mm, so the three stones still do not read as one line — the research's
  primary recommendation) and the unenforced "keep >= 2mm at the narrowest"
  shank rule.

### Cut from this pass (2026-08-05)

**Seat / collar / gallery surface blends are deferred.** The ask is proportions
and claw finishing, not "reads as a real ring" — that bar is not being attempted
yet. The blend work is also the half that flat shading and validation-grade
tessellation hide, so it would be unjudgeable until RNG-27 lands. Everything kept
in CP1/CP2 is visible in the viewer as it stands today.

## Success criteria

- [ ] Refinements at the MODULE level; no per-archetype bespoke shaping.
- [ ] All five saved specs regenerate raw watertight, zero non-manifold edges,
      `X-Mesh-Repaired: false` — the RNG-17 bar.
- [ ] Min wall 0.8mm and min prong tip 0.7mm hold across the in-range space.
- [ ] No RingSpec schema change.
- [ ] Full suite green (3443 baseline), parity rebaselined only in CP1 and only
      deliberately.
- [ ] Proportions read correctly and claws read as cast rather than assembled,
      judged at checkpoint boundaries. **Not** "indistinguishable from a real
      ring" — that bar belongs to RNG-25/27/33 and is not attempted here.
