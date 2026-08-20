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

**Built differently than originally planned here — see "Deviation" below.** The plan called for
round-then-re-repair via `make_coherent`. Built first, exactly as written; it doesn't terminate.
`stone_exceeds_head`'s `+0.05` margin against an already-aligned base (e.g. `stone_height=5.2`)
lands EXACTLY on a half-step tie (`5.25`). Nearest-rounding drops it to `5.2` — equal to
`stone_height`, still a violation — and re-repairing that reproduces `5.25` again, forever: a real
period-2 cycle, not a hypothetical (found while wiring this in, then reproduced as
`test_settle_on_step_grid_falls_back_to_ceil_on_an_exact_tie`).

**What actually ships:** `_settle_on_step_grid(coherent) -> dict | None` in `ringcad/classify.py`,
called from `_coherent_spec` in place of a bare `is_castable` check:

```python
coherent, adjustments = make_coherent(spec, self.confidence)
if is_castable(validate_spec(coherent)):
    stepped = _settle_on_step_grid(coherent)
    if stepped is not None:
        return stepped, adjustments
    # none of nearest/ceil/floor landed castably -- fall through, same as
    # any other non-convergence, to the next fallback tier.
```

`_settle_on_step_grid` tries `_round_to_step(coherent, direction)` for `"nearest"`, `"ceil"`,
`"floor"` in order and returns the first one that's still castable — three direct re-checks, not
another repair pass, so it provably terminates regardless of why nearest failed. `None` means the
same "coherence cannot be reached" case `_coherent_spec`'s fallback chain already exists for.

The pure-default last resort (`_SHARED_DEFAULTS`, `DEFAULT_INNER_DIAMETER`) is already step-aligned
(2.2, 1.9, 6.5, 4.0, 6.0, 16.5 — all exact multiples of 0.1); rounding it is a no-op, included
anyway rather than special-cased out, since the type-driven walk doesn't know or care which tier
produced the spec.

## Checkpoints

- [x] **CP1 — `_round_to_step` + `_settle_on_step_grid` + wiring.** Pure functions, unit tested
      (float rounds, int/str untouched, nested groups only, already-aligned spec unchanged).
      Wired into `_coherent_spec`'s per-attempt check. The planned "re-repair" test became
      `test_settle_on_step_grid_falls_back_to_ceil_on_an_exact_tie`, proving the real
      nearest→ceil→floor mechanism resolves the oscillation the original plan's mechanism could
      not — mutation-checked (dropping the ceil/floor fallback turns it red) to confirm it
      exercises the real code path, not a stale one.
- [x] **CP2 — regression tests for the reported repro.** `length_ratio` (vision's raw estimate)
      and `setting_height` (a coherence-repaired field, the case found during scoping) both
      covered as offline unit tests, no API key needed.

Landed as two commits (design freeze, then implementation) rather than one — the mid-Forge
mechanism swap made "everything in one commit" less honest than showing the working state.

## Success criteria

- [x] A vision estimate that doesn't land on its field's 0.1 step no longer blocks Generate
      (`test_coherent_spec_length_ratio_lands_on_the_step_grid`; confirmed against the real API,
      3 live `/classify-ring` calls, zero off-grid dimension fields)
- [x] A coherence-repaired field that doesn't land on its field's 0.1 step no longer blocks
      Generate (`test_coherent_spec_repaired_field_also_lands_on_the_step_grid`; confirmed live
      with a real repaired `setting.setting_height`)
- [x] Every rounded spec that reaches the frontend still passes `validate_castability` (every
      `_settle_on_step_grid` return is gated on `is_castable`; `None` on failure, never a
      silently-uncastable spec)
- [x] Manual entry (typing an off-grid value by hand) is unaffected — nothing added on the
      frontend; the browser's own validation on user-typed values is untouched
- [x] Arrow-key increment behaviour on the affected inputs is unaffected — zero changes to
      `templates/index.html`
- [x] Full suite green — 3533 passed (3526 baseline + 7 new)

## Out of scope

- Changing any input's `step`/`min`/`max` in `templates/index.html`.
- Rounding confidence values, `motifs`, or any non-dimension field.
- Snapping a value the user typed in by hand.
