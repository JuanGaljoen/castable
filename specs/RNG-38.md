# RNG-38 — Vision estimates that miss the number inputs' 0.1 step grid block Generate

**Type:** fix · **Branch:** `fix/rng-38-vision-estimate-step-mismatch` · **Frozen:** 2026-08-20

## Problem

Every dimension field in the form (`templates/index.html`) has `step="0.1"` (counts have
`step="1"`, already satisfied by construction). Nothing rounds a value to that grid before
writing it into the field, so the browser's native number-input validation silently blocks
Generate whenever the value isn't an exact multiple of 0.1 from the field's `min`.

Two independent sources produce off-grid values:

1. **Vision's raw estimate** (`_clamp`, `_clamp_bounds`, `_stone_shape` in `ringcad/classify.py`)
   — confirmed present on `main` before RNG-32, unrelated to it.
2. **RNG-32's coherence repair** (`ringcad/ringspec/coherence.py`) — found while scoping this
   ticket. Its overshoot margins (`+0.05`, `*1.03`, etc.) almost always produce a non-round
   float, so a repaired field trips this bug more reliably than an unrepaired one.

Decision (Understand, 2026-08-20): fix both in this ticket, in one rounding pass over the fully
assembled spec, rather than patching three upstream call sites and leaving the repair-introduced
case for later. Manual entry is out of scope — the browser validating a value the *user* typed is
existing, expected behaviour; this ticket is only about what the app hands the user unasked.

## The risk this design exists to avoid

Rounding a repaired field is not free: RNG-32's repairs land deliberately close to a boundary
(`_MARGIN_GROW`/`_MARGIN_SHRINK` = 1.03/0.97, chosen to clear it by a little, not a lot).
Naively rounding to the *nearest* 0.1 can round back across that boundary and silently reintroduce
the violation the repair just fixed — e.g. a repair landing on 3.641mm to clear a 3.64mm floor
rounds to 3.6mm, right back under it.

## Design

**One rounding pass, then re-repair, then re-check — reusing RNG-32's own machinery rather than
inventing rounding-direction logic per field.**

In `ringcad/classify.py`:
- `DIMENSION_STEP = 0.1` — matches every stepped float input in the template (confirmed uniform
  across all 16 float fields via the template's own `step=` attributes).
- `_round_to_step(spec: dict) -> dict` — walks the group dicts that carry dimensions (`shank`,
  `setting`, `stones`, and whichever of `halo`/`trilogy`/`side_stone` is present), rounds every
  `float` leaf to the nearest `DIMENSION_STEP`, leaves `int` and `str` leaves untouched. No
  per-field allowlist — a generic type-driven walk, since every float field in these groups is a
  stepped dimension and every int field is already step-aligned by construction
  (`_snap_prong`/`_group_estimates`'s `int()` cast).

In `ClassifyResult._coherent_spec` (`ringcad/classify.py`), inside the existing per-archetype
attempt loop, after a `make_coherent` result already passes `is_castable`:

```python
coherent, adjustments = make_coherent(spec, self.confidence)
if is_castable(validate_spec(coherent)):
    rounded = _round_to_step(coherent)
    if rounded != coherent:
        rounded, more = make_coherent(rounded, self.confidence)
        adjustments = adjustments + more
    if is_castable(validate_spec(rounded)):
        return rounded, adjustments
    # rounding broke it and re-repair couldn't recover -- fall through,
    # same as any other non-convergence, to the next fallback tier.
```

`make_coherent` is already proven (RNG-32 Verify: mutation-tested, fuzz-tested) to terminate and,
when it converges, to fix exactly the violation it's handed — feeding it the *rounded* spec is a
second ordinary call, not new logic. A rounding-induced violation is marginal (at most half a
step, 0.05mm, stacked on top of a repair margin already sized to clear its boundary) so it
converges in one pass in every case found so far; if it somehow doesn't, the existing fallback
chain (already tested for exactly this shape of failure) absorbs it — nothing new to prove there.

The pure-default last resort (`_SHARED_DEFAULTS`, `DEFAULT_INNER_DIAMETER`) is already step-aligned
(2.2, 1.9, 6.5, 4.0, 6.0, 16.5 — all exact multiples of 0.1); rounding it is a no-op, included
anyway rather than special-cased out, since the type-driven walk doesn't know or care which tier
produced the spec.

## Checkpoints

- [ ] **CP1 — `_round_to_step` + wiring.** Pure function, unit tested (float rounds, int/str
      untouched, nested groups only). Wired into `_coherent_spec`'s per-attempt check. A test
      proving the "rounding undoes a repair, re-repair recovers" path, not just the common case.
- [ ] **CP2 — regression test for the reported repro.** `length_ratio` (and the `setting_height`
      case found during scoping) not landing on 0.1 no longer happens; the exact photo/estimate
      shape from manual QA reproduced as an offline unit test (no API key needed — this bug lives
      entirely in `classify.py`'s post-processing, not in what vision returns).

Small enough that both may land as one commit if the diff stays this contained; split only if CP1
turns out to need iteration.

## Success criteria

- [ ] A vision estimate that doesn't land on its field's 0.1 step no longer blocks Generate
- [ ] A coherence-repaired field that doesn't land on its field's 0.1 step no longer blocks Generate
- [ ] Every rounded spec that reaches the frontend still passes `validate_castability`
- [ ] Manual entry (typing an off-grid value by hand) is unaffected — still the browser's own
      validation, not silently overridden
- [ ] Arrow-key increment behaviour on the affected inputs is unaffected (no HTML/step changes)
- [ ] Full suite green

## Out of scope

- Changing any input's `step`/`min`/`max` in `templates/index.html`.
- Rounding confidence values, `motifs`, or any non-dimension field.
- Snapping a value the user typed in by hand.
