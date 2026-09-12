# RNG-24 — Composable features: retire the archetype union
Classification: feature

## Success criteria (the bar Verify checks)

- [ ] A single spec expresses **halo + side-stone shoulders**, and it generates as one
      **raw** watertight manifold (the RNG-17 bar). This is the evidenced combination:
      three separate corpus photos were read correctly as halo-with-pave-shoulders and
      had the shoulders discarded by the union.
- [ ] Any subset of `{halo, trilogy, side_stone}` is **expressible** in the contract.
      Combinations that cannot be built honestly are rejected **before geometry** with a
      `Violation` naming the offending feature — not forbidden by the schema. (The schema
      enumerating legal combinations would be the archetype union wearing a hat.)
- [ ] **Overcrowding composes.** Casting invariants hold across combinations, not merely
      within each feature alone.
- [ ] Existing solitaire / halo / trilogy / side-stone specs generate **byte-identical**
      geometry, SHA-256 compared against this tree (the RNG-25 precedent). RNG-24 changes
      *dispatch*, not construction, so identity should fall out; a deviation is a bug to
      chase, not a criterion to relax.
- [ ] The flat-7 solitaire back-compat path is untouched and still routes correctly.
- [ ] Vision emits a feature set; a photo showing halo + pave shoulders produces both.
- [ ] Frontend is feature toggles rather than a single style dropdown; WCAG 2.1 AA.
- [ ] An ADR records the model change and why the union was retired.
- [ ] **No regression:** full suite green.

## Approach

### The finding that decides the shape

The composition layer is **already feature-shaped**. `ARCHETYPES` (`geometry/module.py:150`)
is literally `["shank", "seat", "prong_setting"]` plus at most one feature name, and
`compose` fuses whatever list it is handed — it does not care that the list came from an
archetype. The four `*Spec` classes are identical apart from one optional group. All six
`archetype == "X"` branch sites are **presence guards** wearing a discriminator's clothes.

So the contract change is largely deletion. The real work is the castability gate.

### The currency for cross-feature checks

`_side_stone_overcrowding` already reasons in **angular spans on the shank**
(`_SIDE_STONE_A_START_DEG = 10.0`, `_SIDE_STONE_A_MAX_DEG = 110.0`), and
`_trilogy_overcrowding` already derives an angular offset `phi = arc / head_r`. The features
already share a coordinate system; nothing new has to be invented to make them comparable.

`_SIDE_STONE_A_START_DEG` means *"far enough round to clear the centre head."* Under
composition that stops being a constant and becomes **derived from whatever else is on the
ring** — a halo pushes the row further round than a bare centre does. That single constant
becoming a function is the cross-feature problem in miniature.

**Each feature answers one question: what annular sector do you occupy?**

    Footprint = (angle_start, angle_end, r_inner, r_outer)

measured about the ring axis, symmetric about the head at theta = 0. Two features collide iff
their **angular** ranges overlap **and** their **radial** ranges overlap, with `MIN_WALL`
clearance. Both halves are load-bearing: a halo plate sits up at setting height while a
channel is cut into the band, so they can share an angle without touching — an angle-only
model would reject valid rings.

One generic pairwise check consumes footprints, so a fourth feature gets its cross-checks for
free. This is the ADR-0009 move (drive from one shared mechanism rather than restating a
parallel table) applied to composition, and it is what CLAUDE.md means by "growing the
composition rules, not piling up per-style templates."

**The footprint formulae are to be MEASURED against real geometry, not derived on paper.**
The halo's is the awkward one: a plate at setting height projected into the band's angular
coordinate. This repo's record on eyeballed numbers is bad enough to be written up twice
(RNG-19's halo web and plate rim; ADR-0011). Build the geometry, measure the sector it
actually occupies, then write the formula.

### Migration: accept and translate at the edge

`validate_spec` keeps accepting `archetype: "halo"` and translates it into the matching
feature group, so every existing spec, the vision layer, the probe manifest and the flat-7
path keep working untouched. The field stops existing inside the model. `spec_errors` loses
its `ARCHETYPE_TAGS` loc-stripping along with the union tag.

**The landmine:** `app.py:71` discriminates the flat-7 back-compat path with
`"archetype" in body`. Once `archetype` is optional, a structured feature-spec that omits it
is misread as a flat-7 solitaire request — the same silent-wrong-path class of bug that bit
RNG-23 (the default style discarding the chosen shape). Discriminate on the presence of any
RingSpec group key (`shank`/`setting`/`stones`/`halo`/`trilogy`/`side_stone`) or `version`,
not on `archetype`.

### Why CP1 is trustworthy on its own

Collapsing the contract makes multi-feature specs *expressible* one checkpoint before they are
*validated*. Rather than leave that window open, CP1 ships a temporary
`multi_feature_unvalidated` violation rejecting more than one feature. CP2 deletes it and puts
the real cross-checks in its place. Each checkpoint is independently green and shippable, per
the repo's checkpoint rule.

## Checkpoints

- [x] **CP1 — contract + migration.** One `RingSpec` with optional `halo`/`trilogy`/
      `side_stone` groups; legacy `archetype` translated at the edge; six `isinstance`
      guards become presence guards; endpoint discriminator fixed; temporary
      `multi_feature_unvalidated` gate; golden geometry hash-compared. Full suite green
      (3924 passed, 1 skipped).
      · files: `ringcad/ringspec/models.py`, `ringcad/ringspec/castability.py`,
      `ringcad/ringspec/coherence.py`, `ringcad/geometry/_common.py`, `ringcad/app.py`,
      `probes/fidelity_probe.py`, `requirements.txt`, `docs/ringspec/contract.md`,
      `docs/ringspec/ringspec.schema.json`, plus 8 rewritten `tests/test_ringspec_*.py`
      files and the new `tests/test_ringspec_composable_identity.py` golden-hash pin.

      **Deviations from the frozen plan, all found by the full-suite run:**
      - `RingSpec.archetype` became a **derived read-only property** (single active
        feature's name, or `"solitaire"`), not dropped outright — `module.py`'s
        `compose(spec)` still reads `spec.archetype` to pick a module list, and CP1
        deliberately left `module.py` untouched (that rework is CP2's). Documented in
        the model's own docstring as meaningful only while <=1 feature is present.
      - `coherence.make_coherent`'s returned dict re-adds an `"archetype"` key (from the
        derived property) before returning. `RingSpec.model_dump()` no longer has an
        `archetype` field to round-trip, but `classify.py`'s `to_spec()` and its tests
        still key the JSON contract on one — that migration is CP3's, not CP1's.
      - Found via that fix: the legacy-tag translation in `validate_spec` originally
        checked group *presence* as `group in data`, which misfires against a dumped
        spec where absent features are `None`-valued keys rather than missing ones.
        Fixed to `data.get(group) is not None`.
      - `probes/fidelity_probe.py`'s `supported_archetypes()` reflected on the (former)
        `RingSpec` union via `typing.get_args`; retired in favour of importing
        `classify.SUPPORTED_ARCHETYPES` directly — one source of truth instead of two,
        rather than reinventing a way to reflect archetype tags off a plain model.
      - `pydantic_core` added to `requirements.txt`: `models.py` constructs synthetic
        `ValidationError`s for the legacy-tag translation via `pydantic_core.
        from_exception_data`/`PydanticCustomError`, both already installed transitively
        by `pydantic` but not previously a direct import (`test_requirements.py`,
        RNG-18, requires every direct import declared).
      - `SolitaireSpec`/`HaloSpec`/`TrilogySpec`/`SideStoneSpec` kept as thin factory
        *functions* over `RingSpec` (not the plan's silent deletion) — a large existing
        test/geometry surface used them as pure constructors with no `isinstance` check;
        keeping the call shape avoided touching files the plan never listed. The
        `isinstance` call sites (all confined to the `test_ringspec_*.py` contract
        tests) were rewritten to presence checks, which is the honest signal the union
        is actually gone.

- [x] **CP2 — composition + cross-feature castability.** `compose` builds from the feature
      set; `Footprint` seam + one generic pairwise check; `_SIDE_STONE_A_START_DEG` becomes
      derived; temporary gate removed. Full suite green (3928 passed, 1 skipped). The
      evidenced AC holds: a halo + side-stone spec generates as one **raw** watertight
      manifold, no repair (`tests/test_ringspec_cross_feature.py`).
      · files: `ringcad/geometry/module.py`, `ringcad/ringspec/castability.py`,
      `ringcad/ringspec/footprint.py` (new), `ringcad/geometry/side_stone.py`,
      `ringcad/ringspec/models.py` (`effective_thickness_taper`), `ringcad/geometry/_common.py`,
      `docs/ringspec/contract.md`, `tests/test_ringspec_cross_feature.py` (new)

      **The footprint formulae were measured, not derived on paper** (the design's own
      Risk #1), via a throwaway script building the real `compose()`d golden halo/
      trilogy geometry and reading bounding-box corners as (r, θ) about the ring axis —
      `ringspec` cannot import `geometry` (docs/adr/0002), so the resulting closed-form
      approximations, widened by a measured `SAFETY_MARGIN`, are encoded once in
      `footprint.py` rather than computed from real geometry at validation time.

      **Two modeling bugs found by that same measurement, both fixed before landing:**
      - The naive `arc/head_r` angular estimate under-reported a raised feature's true
        reach by up to ~25% — its nearest bounding-box corner sits closer to the axis
        than `head_r`, so the same tangential extent subtends a wider angle than the
        naive formula assumed. Fixed with the measured `SAFETY_MARGIN` (1.3x).
      - **The real bug:** modelling `side_stone`'s two shoulders as one symmetric
        interval `[-end, +end]` made it report a collision with EVERY halo regardless
        of size, since a halo centred on the head always falls inside that interval —
        even though nothing is actually built in the gap between the shoulders.
        `side_stone_footprints` now returns two disjoint per-shoulder `Footprint`s.
        Caught by testing the evidenced positive case (halo + side-stone golden
        defaults) and finding it failed when the design predicted it should pass.

      **`_SIDE_STONE_A_START_DEG` is genuinely derived now** (`side_stone_start_deg`):
      widened past whichever of halo/trilogy is present, by a measured margin (not a
      bare touch) so the two clear by construction rather than by chance — read by
      BOTH the gate (`_side_stone_overcrowding`) and the builder (`side_stone.py`'s
      `_accent_angles`), closing the drift class ADR-0002 warns about before it could
      open. `effective_thickness_taper` (models.py) is the same move applied to the
      pre-existing `t_taper` duplication between `_common.clamps` and
      `_side_stone_overcrowding`/`_trilogy_overcrowding` — found while wiring the
      footprint currency, fixed as part of the same single-source pass.

      **Negative case, not just positive:** halo + trilogy at golden defaults IS
      flagged (`cross_feature_overcrowding`, naming both features) — both are fixed at
      the head and neither can move for the other, so this is the genuine case the
      design's own note anticipated, not a gate that only ever says yes.

- [x] **CP3 — vision + UI.** `classify.py` emits a feature set (not an archetype enum);
      the form stops offering a style choice at all.
      · files: `ringcad/classify.py`, `ringcad/ringspec/coherence.py`, `static/app.js`,
      `static/photo.js`, `templates/index.html`, `static/styles.css`,
      `probes/fidelity_probe.py`

      **The UI half was rescoped mid-checkpoint, by the ticket's owner, after
      looking at it.** The plan said "feature checkboxes with an `active` set". Built
      that; the objection was that hand-picking features reads as a product
      CONFIGURATOR, and that meeting a parts-picker above the dimensions puts style
      selection in front of the photo. Rebuilt behind an "Add a feature" disclosure at
      the foot of the form; that was rejected too. **Final shape: the form offers no way
      to add a feature at all.** The photo is the only thing that puts one on a ring;
      each feature's fieldset carries a Remove, because vision is not always right and
      the user needs to be able to drop something that isn't there. The asymmetry
      (remove, but never add) is the design.

      Worth recording because the *backend* half was never in question: retiring the
      union is what lets a photo of a halo-with-shoulders produce both. The picker was
      a thin layer on top, built twice and discarded twice, and neither version was
      load-bearing. **Scope the UI for a photo-reproduction tool, not a configurator.**

      **A real 500, found by the first real upload, behind a fully green suite.**
      CP1 had `make_coherent` re-attach a single `archetype` label to the dumped spec,
      as back-compat for callers that still keyed on one. On a genuinely multi-feature
      spec that label is just `"halo"` — and re-validating that dict then hits the
      LEGACY exclusive-archetype rule, which rejects a "halo" spec for also carrying
      `side_stone`. **The spec poisoned itself passing back through its own validator.**
      CP1's own notes called the label "meaningful only while at most one feature is
      present" and then kept it anyway; CP3 is exactly when that stopped being true.
      No test caught it because every fixture had at most ONE feature — the suite
      tested the shape it was written against, not the shape the ticket creates.
      Shim removed; `probes/fidelity_probe.py` derives its single-name label from the
      groups actually present (`archetype_label`), which reads identically for a
      one-feature ring and honestly as `halo+side_stone` for a combined one.

      **`coherence.py` needed no repair changes.** `cross_feature_overcrowding` has no
      dedicated repair and should not have one: when two features simply do not fit
      together there is no single obvious field to move. It falls through to the
      fallback chain like any other unrepairable violation, which is the honest answer.

      **Copy, twice corrected by the owner.** `_note` announced "also building side
      stone" against a photo described as "pave band shoulders" — internal vocabulary,
      matched by substring against free text, about a substitution that never happened.
      It is now the estimates caveat only; describing the photo is `style`'s job, and
      `style` is now prompted for a jeweller's sentence or two rather than a terse
      category label. The status line keeps only what is actionable for that run.

      **Filed, not built: RNG-44 (pave retention).** The corpus photo's shoulders are
      pave-set and `SideStone.retention` is `Literal["channel"]`, so the app sets them
      the wrong way. Vision reads it correctly and says "pave" twice. Out of scope here
      (RNG-11 deferred pave deliberately); the evidence is recorded on the ticket.

## Tests (seams, not internals)

- **Contract seam** (`validate_spec`): a legacy `archetype` body round-trips to the right
  feature set; a feature body with no `archetype` validates; a body with both that disagree
  is rejected naming the field; `extra="forbid"` still holds.
- **Endpoint seam** (`POST /generate-ring`): flat-7 still routes flat-7; a structured body
  without `archetype` routes structured (the CP1 landmine, pinned by a test).
- **Identity seam**: SHA-256 of the exported STL for the golden solitaire / halo / trilogy /
  side-stone, compared against this tree.
- **Gate seam** (`validate_castability`): a halo + side-stone spec that overcrowds is
  rejected naming the offending feature; the same spec with room passes.
- **Composition seam** (`compose`): halo + side_stone yields one watertight solid, body
  count 1, volume > 0 (ADR-0005 + ADR-0008 — assert what the boolean produced).

## Risks

1. **The halo footprint is an approximation.** Projecting a plate at setting height into the
   band's angular coordinate is the one formula here that cannot be read off existing code.
   Measure it; do not invent it.
2. **Byte-identity may not survive `compose`'s fuse order.** The fuse is order-sensitive, so
   the feature list must reproduce today's exact module order for single-feature specs.
3. **`coherence.make_coherent` repairs field-by-field from `Violation`s.** A cross-feature
   violation names a feature, not a scalar field — the repair loop may have no obvious victim
   to move. CP3 problem, but it is the one most likely to need a design change mid-flight.
