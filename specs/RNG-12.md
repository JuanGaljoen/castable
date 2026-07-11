# RNG-12 — Vision-driven style dispatch (photo → RingSpec + per-style estimates)

**Type:** feature · **Branch:** `feature/rng-12-vision-to-ringspec`
**Status:** frozen design, ready for Forge.

Promote the vision layer from a solitaire-only pre-fill helper into the front
door of "photo → castable model": an uploaded ring photo produces a **validated
RingSpec** (archetype + its groups + per-field confidence), and the frontend
becomes a structured editor over that spec — the detected archetype selected,
its fields pre-filled and fully editable, "Estimates only, verify before
generating" preserved.

Builds on RNG-6 (the `/classify-ring` endpoint + `classify.py` + `photo.js`) and
RNG-14 (RingSpec discriminated union + `FieldConfidence`, already defined).

## Constraints inherited (non-negotiable)

- **Never-500 / never-raise.** `classify_ring` still never raises; the endpoint
  keeps the RNG-6 discipline: 503 no-key, 502 vision failure, 400 bad upload.
- **Key stays server-side.** `ANTHROPIC_API_KEY` never reaches the browser or a
  result body/log line.
- **No new top-level dependency** (anthropic + pydantic already present).
- **No JS frameworks; vanilla only. WCAG 2.1 AA.**
- **Ranges single-sourced.** Clamp bounds come from the RingSpec `Field()`
  constraints / `docs/parameter-ranges.md`, never re-typed as literals.

## Decisions (locked in Understand)

1. **Detection returns both `detected_style` (free text) and `archetype`
   (strict enum over the 4 buildable).** The vision output schema constrains
   `archetype` to `Literal["solitaire","halo","trilogy","side_stone"]`, so the
   model always names a buildable archetype (the nearest-match is the model's
   job, not a brittle server-side `style→archetype` table). `detected_style` is
   the free-text description of what's actually in the photo. When the two
   diverge (detected style isn't the chosen archetype's canonical name), the
   note says so: *"Detected <style> — building the nearest supported style
   (<archetype>). Verify before generating."* This is the ticket's "graceful
   fallback with a clear note", done honestly without a mapping table.

2. **Confidence covers the shared 7 fields only** — the existing
   `FieldConfidence`. No RingSpec contract change. A photo yields near-noise
   confidence on sub-millimetre accent gaps, and RNG-19 explicitly says to keep
   contract-widening out of RNG-12. Group fields are pre-filled from
   model-informed defaults/estimates but carry no confidence value.

3. **`/classify-ring` returns a full, server-validated RingSpec.** The endpoint
   builds a concrete RingSpec (archetype + shared groups + archetype group +
   `confidence`), routes it through `validate_spec` (guaranteeing the frontend
   receives a spec that will pass `/generate-ring`), and returns it. `photo.js`
   selects the archetype and pre-fills every group field from it. This is the
   ticket thesis: "the form becomes a structured editor over that spec."

4. **UI flags low-confidence fields; it does not print numbers.** Fields whose
   confidence is below a threshold (`0.5`) get a subtle visual + `aria`
   marker ("low confidence — check this"). Users don't calibrate to "0.4"; a
   warning marker is more usable and WCAG-clean.

## Response contract (`/classify-ring`, 200)

```jsonc
{
  "ring_detected": true,
  "detected_style": "cathedral pavé halo",   // free text; "" when generic
  "note": "Detected cathedral pavé halo — building the nearest supported style (halo). Verify before generating.",
  "spec": {                                  // a valid RingSpec (validate_spec-checked)
    "version": "1.0",
    "archetype": "halo",
    "shank":   { "inner_diameter": 16.5, "band_width": 2.2, "band_thickness": 1.9 },
    "setting": { "prong_count": 6, "setting_height": 6.0 },
    "stones":  { "stone_diameter": 6.5, "stone_height": 4.0 },
    "halo":    { "halo_stone_diameter": 1.3, "halo_stone_count": 14, "halo_gap": 0.5, "halo_stone_height": 1.2 },
    "confidence": { "band_width": 0.6, "stone_diameter": 0.8, ... }   // 7 shared fields, nulls allowed
  }
}
```

- `ring_detected: false` → `{ring_detected:false, detected_style:"", note:"No ring detected…", spec:null}`.
  Frontend leaves the form as-is (manual entry).
- `inner_diameter` is **never estimated** (RNG-6 rule); it stays the RingSpec
  default and its confidence stays `null`.
- Non-detected shared/group fields fall back to the archetype's schema defaults,
  so `spec` is always complete and buildable.

## Clamping / snapping

- Shared 5 dims: clamp to `classify.CLAMP_BOUNDS` (unchanged).
- `prong_count`: snap to `{4,6}` (unchanged `_snap_prong`).
- Group dims: clamp to the RingSpec `Field()` bounds, **read from the model**
  (`model_fields[...].metadata` → ge/le), not re-typed. Group int counts
  (`halo_stone_count`, `accent_count_per_side`) clamp+round to int.
- Belt-and-braces: the assembled spec goes through `validate_spec`; if it ever
  raised (it shouldn't after clamping), fall back to a solitaire spec from the
  shared dims with a note. Preserves never-500.

## Files

**CP1 — backend (classify → validated RingSpec + endpoint):**
- `ringcad/classify.py` — extend `RingClassification` output schema (add
  `archetype` enum + `detected_style` + per-archetype group dims + optional
  confidence fields); add archetype-aware assembly into a RingSpec; replace
  `ClassifyResult.estimates`/`to_json` with a `spec` + `detected_style` + `note`
  shape (or add a `to_spec()`); group-field clamp helper reading model bounds.
- `ringcad/app.py` — `/classify-ring` returns the new contract (the 503/502/400
  branches unchanged).
- Tests: `tests/` — archetype detection maps to each of the 4; group clamp +
  int snap; unsupported `detected_style` → note names both; confidence surfaced;
  `ring_detected:false`; never-raise on malformed vision output; returned spec
  passes `validate_spec` and `/generate-ring` shape.

**CP2 — frontend (structured editor over the spec):**
- `static/photo.js` — consume `spec`: set the `archetype` `<select>`, fire its
  change handler (reuse `app.js` visibility), pre-fill shared + group fields
  from `spec`, flag low-confidence fields, keep "estimates only" label + detected
  line. Never touch `inner_diameter` estimate (fill from spec default only).
- `templates/index.html` + `static/*.css` — low-confidence marker styles + aria.
- Manual/browser QA (no-key 503 path, not-a-ring, a detected halo/trilogy).

> Seam rationale (CLAUDE.md "checkpoint at module seams"): CP1 is a self-contained
> backend contract change, green and trustworthy alone; CP2 is pure wire-up over
> it. A rate-limit interruption between them lands on a resumable commit.

## Success criteria

- [ ] Vision output maps to a **valid RingSpec** for every detected archetype;
      returned spec passes `validate_spec` and is a valid `/generate-ring` body.
- [ ] Detected-but-unsupported style falls back to a supported archetype with a
      clear note naming both the detected style and the built archetype.
- [ ] Per-element estimates clamped to RingSpec ranges (group bounds read from
      the model); counts snapped to int; `prong_count` snapped to {4,6}.
- [ ] Per-field confidence (shared 7) surfaced; low-confidence fields flagged in
      the UI; every pre-filled field stays editable.
- [ ] Frontend selects the detected archetype and pre-fills its group fields.
- [ ] RNG-6 discipline preserved: 503 no-key + manual-entry message, graceful
      not-a-ring, never-500, key stays server-side.
- [ ] `inner_diameter` never estimated.
- [ ] Full suite green.

## Checkpoints

- [x] **CP1 — backend:** `classify.py` emits a validated RingSpec (archetype
      detection, group clamp/snap, confidence, fallback note); `/classify-ring`
      returns the new contract. Tests green (3301 passed).
- [ ] **CP2 — frontend:** `photo.js` selects the archetype + pre-fills group
      fields from the spec; low-confidence flagging; RNG-6 fallbacks preserved.
      Suite green + browser QA.
