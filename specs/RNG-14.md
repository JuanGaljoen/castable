# RingSpec v1: structured ring IR / schema (RNG-14)

> The versioned, typed contract between the vision layer and the geometry
> layer. v1 fully expresses the solitaire; future archetypes extend it
> additively. Type: feature. Depends on RNG-13 (build123d GO — done).

## Problem

Today the only "contract" between the vision layer and the geometry layer is a
flat 7-key dict, validated ad hoc in `ringcad/params.py`, with castability baked
into the SCAD as scattered `max()` clamps. There is no structured, versioned,
archetype-aware representation of a ring. Without a shared spec, every new
archetype becomes a hand-written template.

When this is done, the vision layer (or a user) produces a typed, versioned
**RingSpec**; vision and geometry evolve against it independently; and
castability is validated on the spec *before* any geometry runs. Before this,
the only representation was an unstructured 7-param dict with no archetype model
and no pre-geometry castability gate.

## Acceptance Criteria

1. **Lossless round-trip.** `from_params(p)` → `RingSpec` → `to_params()`
   returns the identical 7 values for every valid 7-param input (exact
   equality; ints stay ints). Verified by a property test over the valid input
   space.
2. **Versioned + validated.** Every RingSpec carries `version` and an
   `archetype` discriminator. Schema validation rejects malformed specs (wrong
   type, out-of-range, unknown archetype, missing or unknown field) with a
   field-level error naming the offending field and reason. Unknown/extra
   fields are forbidden.
3. **Castability validation.** A `validate_castability(spec)` pass — distinct
   from schema/type validation — flags manufacturing violations (band thickness
   < 0.8mm, prong tip < 0.7mm, geometric impossibilities) and returns
   structured violations *before* geometry generation. Constants single-sourced
   from the existing `MIN_WALL` / `MIN_PRONG_TIP`.
4. **Documented schema committed.** JSON Schema generated from the model
   (`model_json_schema()`) plus a markdown contract doc, committed under
   `docs/ringspec/`.

## Approach

Pydantic v2 models in a new `ringcad/ringspec/` package (already a dependency;
matches `classify.py`). A versioned envelope with an `archetype` discriminator
over nested element groups: **`shank`**, **`setting`**, **`stones`**,
**`motifs`**. v1 *defines and validates the `solitaire` archetype only*; future
archetypes (halo/trilogy, RNG-16) are added as new discriminator values —
additive, no breaking v2. Field-local castability (min wall, min tip) as
Pydantic validators; cross-field geometric rules in a separate
`validate_castability`. `from_params` / `to_params` adapters bridge the existing
7-param dict.

The element groups map deliberately onto the build123d modules proven in the
RNG-13 spike: `shank → shank()`, `setting → prong_setting()`,
`stones/seat → seat()` — so RNG-15 consumes RingSpec cleanly.

## Edge Cases

| Case | Expected behavior |
|------|-------------------|
| `prong_count` ∉ {4, 6} | Schema rejection with clear error (SCAD's snap-to-4 is a vision-layer concern, not the contract's) |
| `band_thickness` exactly 0.8mm | Valid (boundary inclusive) |
| Unknown archetype (e.g. `"halo"` pre-RNG-16) | Rejected: "archetype not supported in v1" |
| Extra/unknown field | Rejected (`extra="forbid"`) |
| `shank_taper` (SCAD's 8th shaping param) | Lives in `shank` group, default `1.7`; `to_params` drops it, `from_params` restores default → 7-param round-trip stays lossless |
| Empty/null body | Clear top-level error |
| `motifs` empty for solitaire | Valid |
| Optional per-field confidence absent | Fine (defaults `None`; populated by RNG-12, only defined here) |

## Constraints

- No new top-level dependencies (Pydantic already present).
- ≤300 LOC per file (split the package if needed).
- Does NOT modify `/generate-ring` or `params.py` — round-trip is purely
  additive (endpoint cutover is RNG-15).
- Validation errors must be JSON-serializable (for API surfacing in RNG-15).
- mm units, floats, throughout. Casting constants referenced, never duplicated.

## Scope Boundaries

**In scope:** the `ringspec` package, the solitaire archetype, schema +
castability validation, round-trip adapters, JSON Schema + markdown doc, tests.

**Out of scope (with reason):**
- Wiring RingSpec into `/generate-ring` and retiring `params.py` → RNG-15.
- Other archetypes (halo/trilogy) → RNG-16.
- Vision *populating* RingSpec and consuming confidence → RNG-12.
- Generating geometry from RingSpec → RNG-15.

## Success Metrics

- Round-trip identity holds for 100% of valid 7-param combinations (property test).
- 100% of malformed specs rejected with a named offending field.
- Generated JSON Schema validates the committed example specs.
- Contract doc committed and linked from the ticket.

## Dependencies

- RNG-13 (build123d GO) — done. Element groups align with the spike's
  `shank` / `prong_setting` / `seat` modules so RNG-15 can consume RingSpec
  directly.

## Build sizing

1–3 ACs, ~3–4 files (new `ringspec/` package + tests + doc), 1 codebase area →
**direct mode**, not worker mode.
