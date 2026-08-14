# RNG-32 — Vision estimates fields independently, producing specs the casting gate rejects

**Type:** fix · **Branch:** `fix/rng-32-vision-cross-field-coherence` · **Frozen:** 2026-08-14

## Problem

`ClassifyResult.to_spec()` clamps each estimate to its own range, reading bounds off the
RingSpec models. Nothing couples a field to its siblings, so vision can emit a spec that is
schema-valid and individually defensible but physically impossible — a 5.2mm stone inside a
3.0mm head. `to_spec` catches only pydantic `ValidationError`; **the casting gate is never
consulted at assembly.** The user uploads a photo and gets an error instead of a ring.

RNG-19 tightened the gate, so this now bites harder: two of the five corpus ring photos are
rejected outright.

### Found while designing: the defaults are not a safe backstop

A pure-defaults spec with **no vision input at all** is uncastable for one archetype:

| archetype | `validate_castability` on `_assemble(arch, {})` |
|---|---|
| solitaire | clean |
| halo | clean |
| trilogy | clean |
| **side_stone** | **`side_stone_channel_fit`** — 2.2mm band, 3.1mm needed |

`channel_band_width(1.5, 0.8) == 3.1`, and `_SHARED_DEFAULTS["band_width"]` is 2.2. This is
the exact arithmetic RNG-19 CP3 called out. Consequences: the side-stone corpus photo cannot
generate whatever vision says, and "fall back to defaults" is not by itself a valid last
resort. The repair engine must be able to fix it, and the fallback must be *verified* castable
rather than assumed.

## Approach — gate-driven repair, not a parallel rule table

**Decision (D1): repair is driven by `validate_castability`'s own `Violation`s.**

The ticket's scope says "audit the schema for other dimension pairs". The gate *is* that audit,
already written and already the thing that rejects us. Restating containment rules inside
`classify.py` would recreate exactly the ADR-0002 drift RNG-19 found (a check and a builder
disagreeing about the shank taper, so setting the field moved one and not the other). A rule
added to the gate tomorrow is covered here for free — RNG-19 added three and this file would
need zero lines.

It is viable because every `Violation` is already machine-actionable: it carries `code`, the
`field` path to move, `limit_mm` and `actual_mm`. `halo_web` even computes the maximum accent
count that fits.

**Decision (D2): when two fields conflict, move the one vision was least sure about.**

`RingConfidence` is collected per shared dim and currently only draws an amber marker. This
gives it a second, load-bearing job. Confidence covers the six shared dims only — group dims
(halo count, accent gap) have none, so those use the fixed victim in the table below. Ties and
missing confidence fall back to the fixed victim.

**Decision (D3): `inner_diameter` never moves.** It is finger size, never estimated from a
photo (the RNG-6 rule). `stone_exceeds_bore` therefore always shrinks the stone.

## The seam

New module **`ringcad/ringspec/coherence.py`** — spec-layer, depends on `castability`, knows
nothing about vision:

```python
def make_coherent(spec: dict, confidence: dict | None = None
                  ) -> tuple[dict, list[Adjustment]]
```

Assembles → validates → repairs the named fields → re-validates, to a bounded pass count.
Returns the coherent spec plus what it changed. It lives in `ringspec/` rather than
`classify.py` because "make this spec castable" is not a vision concern; putting it there keeps
it reusable (a future "fix this for me" button in the UI) and unit-testable with no API key.

`classify.py` calls it and does nothing else new.

## Repair table (keyed on `Violation.code`)

| code | field named | repair | victim |
|---|---|---|---|
| `min_wall` | the thin field | raise to `limit_mm` | fixed (only one field) |
| `stone_exceeds_head` | `stones.stone_height` | raise `setting_height` **or** lower `stone_height` | **confidence** |
| `stone_exceeds_bore` | `stones.stone_diameter` | shrink stone to clear the bore | fixed (D3) |
| `min_prong_tip` | `setting.prong_count` | 6→4 **or** grow `stone_diameter` | **confidence** |
| `stone_curvature` | `stones.length_ratio` | reduce ratio to `semi_minor / collar_r` | fixed |
| `halo_overcrowding` | `halo.halo_stone_count` | reduce to `perimeter // diameter` | fixed |
| `halo_web` | `halo.halo_stone_count` | reduce to `perimeter // needed` | fixed |
| `trilogy_overcrowding` | `trilogy.side_stone_gap` | raise gap until chord clears | fixed |
| `side_stone_overcrowding` | count *or* gap | reduce count / raise gap as flagged | fixed |
| `side_stone_channel_fit` | `shank.band_width` | raise to `limit_mm` | fixed |
| `side_stone_channel_floor` | `shank.band_thickness` | raise to `limit_mm` | fixed |

Every repair clamps to the field's own schema bounds, so a repair can never produce a
schema-invalid spec. A repair that would need to exceed its bound is a failed repair, not a
silent clip past the contract.

**Convergence.** Repairs move monotonically in the direction the gate asked for, and the loop
re-validates because one repair can trip another rule. Budget: **6 passes**. Exhausting it, or
meeting a code with no repair, drops to the fallback.

**Fallback chain:** repaired archetype spec → repaired solitaire → defaults solitaire. The last
link is asserted castable by test, so the chain cannot end on an uncastable spec.

## Checkpoints

- [x] **CP1 — the repair engine.** `ringcad/ringspec/coherence.py` + `tests/test_ringspec_coherence.py`
      (24 tests). Pure, offline, no key, no network. `make_coherent(spec, confidence)` assembles
      → validates → repairs the field each `Violation` names → re-validates, bounded at 6 passes.
      All 11 gate codes covered. The defaults-castable assertion for all four archetypes passes
      (side_stone's 2.2mm-band case is repaired to 3.1mm by the same `side_stone_channel_fit`
      repair a real photo would trigger — Risk #3 resolved by repairing, not by changing
      `_SHARED_DEFAULTS`). One deviation found empirically: multiplicative scaling
      (`new = current * limit/actual`) is exact for fields that ARE the measured quantity or
      scale it linearly, but undershoots badly for a small field feeding a larger trig-derived
      quantity (`side_stone_gap`/`trilogy.side_stone_gap` feeding a chord) — added an `additive`
      repair mode with a generous fixed overshoot for those two. Full suite green: 3512 passed
      (3488 + 24), 668s.
- [x] **CP2 — wire into the vision layer.** `ClassifyResult._coherent_spec()` runs the fallback
      chain (detected archetype repaired -> solitaire from the same shared estimates repaired ->
      pure-default solitaire); `to_spec()` and the new `to_json()["adjustments"]` both read from
      it. `_assemble` gained an `estimates` override for the last-resort link (bypasses a bad
      vision shape reading too, not just bad dims). One existing RNG-12 test
      (`test_group_dims_clamped_to_model_bounds`) asserted schema-clamp-only behaviour that
      coherence now legitimately overrides (24 halo accents at the clamped 0.9mm minimum still
      overcrowd); split into a unit test of `_group_estimates` alone plus a new integration test
      of the final castable count. **RNG-22 probe against the real corpus: 5/5 generated, 5
      pass, 0 fail** (up from 3/5 before RNG-32), including `halo-round.png`, the ticket's own
      counterexample. The one `warn` is vision reading side-stone as solitaire — RNG-34's known
      nondeterminism, unrelated to coherence, and still castable. Full suite green.
- [ ] **CP3 — tell the user what moved.** The form marks which estimates were adjusted to make
      the ring buildable, alongside the existing amber low-confidence markers. Confirmed in
      scope on 2026-08-14: adjusting silently contradicts the app's "estimates only, verify
      before generating" framing, and the marker machinery already exists. WCAG 2.1 AA, so the
      marker is announced, not colour-only.

## Success criteria

- [ ] All **5** ring photos in the RNG-22 corpus assemble a castable spec and generate.
      (The ticket says 4/4; that predates the fifth entry and the RNG-19 rejections. Bar
      raised deliberately, per the Understand call.)
- [ ] Coherence is enforced before `/generate-ring` ever sees the spec, so the gate receives an
      already-consistent spec.
- [ ] Every gate rule with a repair is covered by an offline test; a rule with no repair
      degrades to the fallback rather than raising.
- [ ] The defaults spec is castable for all four archetypes.
- [ ] The solitaire fallback still applies when coherence cannot be reached.
- [ ] Full suite green; never-500 discipline preserved.

## Out of scope

- Guaranteeing every conceivable photo generates. The casting gate stays the backstop.
- Changing the gate's rules or the geometry. If a rule is wrong, that is its own ticket.
- Prompt engineering the model into coherence — the ticket's evidence is that it is
  intermittent, so a prompt cannot be the guarantee.

## Risks

1. **A repair oscillates** — raising A trips B, whose repair lowers A. Mitigated by the pass
   budget and the fallback; a test drives a known oscillating pair.
2. **Repair degrades fidelity.** Adjusting means the model matches the photo less well. That is
   the ticket's stated preference (a ring beats an error), but the probe should be eyeballed
   after, not just counted.
3. **The side_stone default fix may belong in the defaults, not the repairer.** Repairing every
   side-stone spec up to 3.1mm hides a bad default. Decide during CP1 whether
   `_SHARED_DEFAULTS` should carry an archetype-aware band width instead.
