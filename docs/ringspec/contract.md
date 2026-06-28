# RingSpec v1 — Contract (RNG-14)

The versioned, typed contract between the **vision/understanding** layer and the
**procedural geometry** layer. The vision layer (or a user) produces a
`RingSpec`; both sides evolve against it independently; castability is validated
on the spec *before* any geometry runs.

- **Package:** `ringcad/ringspec/`
- **Kernel:** Pydantic v2 models (matches `ringcad/classify.py`)
- **Generated schema:** [`ringspec.schema.json`](./ringspec.schema.json)
- **Worked example:** [`examples/solitaire.json`](./examples/solitaire.json)

## Envelope

`RingSpec` is a versioned envelope over four element groups. Unknown/extra
fields are rejected everywhere (`extra="forbid"`).

| Field        | Type                       | Default        | Notes |
|--------------|----------------------------|----------------|-------|
| `version`    | `Literal["1.0"]`           | `"1.0"`        | Schema version. |
| `archetype`  | `Literal["solitaire"]`     | `"solitaire"`  | **Discriminator** (see below). |
| `shank`      | `Shank`                    | required       | Band geometry. |
| `setting`    | `Setting`                  | required       | Prong / gallery. |
| `stones`     | `Stones`                   | required       | Centre-stone sizing. |
| `motifs`     | `list[Motif]`              | `[]`           | Empty is valid for a solitaire. |
| `confidence` | `FieldConfidence \| null`  | `null`         | Per-field vision confidence; populated by RNG-12. |

### Archetype discriminator

v1 **defines and validates the `solitaire` archetype only**. `archetype` is a
`Literal["solitaire"]`, so any other value (e.g. `"halo"`) is rejected at schema
validation with a literal error. Future archetypes (halo/trilogy, RNG-16) are
added as new discriminator values — additive, no breaking v2. v1 uses a single
model + Literal discriminator; the true discriminated union (JSON Schema
`oneOf`) is deferred to RNG-16.

The element groups map deliberately onto the build123d modules proven in the
RNG-13 spike: `shank → shank()`, `setting → prong_setting()`,
`stones → seat()` — so RNG-15 consumes RingSpec cleanly.

## Element groups

All bounds below are **structural sanity caps** (generous physical limits), not
casting floors. Casting floors are enforced separately in castability validation
(see below). All dimensions are millimetres, floats.

### `Shank`

| Field            | Type    | Default | Bound        |
|------------------|---------|---------|--------------|
| `inner_diameter` | `float` | required| `> 0`, `<= 40` |
| `band_width`     | `float` | required| `> 0`, `<= 12` |
| `band_thickness` | `float` | required| `> 0`, `<= 8`  |
| `shank_taper`    | `float` | `1.7`   | `>= 1.0`, `<= 3.0` |

`shank_taper` is the SCAD 8th shaping parameter — see round-trip rule below.

### `Setting`

| Field            | Type            | Default | Bound        |
|------------------|-----------------|---------|--------------|
| `prong_count`    | `Literal[4, 6]` | required| exactly 4 or 6 |
| `setting_height` | `float`         | required| `> 0`, `<= 20` |

`prong_count ∉ {4, 6}` (including `5` and `True`) is a schema rejection. SCAD's
snap-to-nearest is a vision-layer concern, not the contract's.

### `Stones`

| Field            | Type    | Default | Bound        |
|------------------|---------|---------|--------------|
| `stone_diameter` | `float` | required| `> 0`, `<= 24` |
| `stone_height`   | `float` | required| `> 0`, `<= 12` |

### `Motif`

| Field      | Type            | Default | Notes |
|------------|-----------------|---------|-------|
| `kind`     | `str`           | required| |
| `position` | `float \| null` | `null`  | |

### `FieldConfidence`

Optional per-field vision confidence in `[0, 1]`, one nullable float per 7-param
field (`inner_diameter`, `band_width`, `band_thickness`, `stone_diameter`,
`stone_height`, `prong_count`, `setting_height`). All default `null`; RNG-12
populates them.

## Schema validation (AC2)

- `validate_spec(data) -> RingSpec` wraps `RingSpec.model_validate`.
- `spec_errors(exc) -> list[dict]` flattens a `ValidationError` into
  JSON-serializable `{"field", "reason", "type"}` entries. `field` is the dotted
  loc path (`"shank.band_width"`); a top-level/body error (e.g. a `null` body)
  has `field == ""`.

Rejected cases: wrong type, out-of-range, `prong_count` not in `{4, 6}`,
unsupported `archetype`, extra/unknown field, missing required group/field, and
a `null`/non-object body.

## Castability validation (AC3)

Distinct from schema validation: a schema-valid spec can still be physically
uncastable. `validate_castability(spec) -> list[Violation]` runs the lost-wax
gate; `[]` means castable. `is_castable(spec) -> bool` is the boolean form.
Each `Violation` is `{code, field, message, limit_mm, actual_mm, severity}` and
is JSON-serializable via `model_dump()`.

Casting constants are **single-sourced** from
[`ringcad/mesh_validator.py:20-21`](../../ringcad/mesh_validator.py) —
`MIN_WALL_MM = 0.8`, `MIN_PRONG_TIP_MM = 0.7` — never duplicated.

| Code                 | Rule |
|----------------------|------|
| `min_wall`           | `band_thickness`, `band_width`, or `setting_height` `< MIN_WALL_MM`. `0.8mm` exactly is **inclusive** (passes). `limit_mm == MIN_WALL_MM`. |
| `min_prong_tip`      | Derived prong-tip diameter `< MIN_PRONG_TIP_MM`. The tip diameter is a **coarse proxy** (`π · stone_diameter / prong_count · wire_fraction`) — plan Risk #2, "fuzzy"; pin against the SCAD/build123d geometry in RNG-15. |
| `stone_exceeds_bore` | `stone_diameter >= inner_diameter` (stone wider than the finger bore). |
| `stone_exceeds_head` | `stone_height >= setting_height` (stone taller than the head). |

## Round-trip with the legacy 7-param dict (AC1)

`from_params` / `to_params` (`ringcad/ringspec/adapters.py`) bridge the legacy
flat 7-key dict (`ringcad/params.py`) additively — `/generate-ring` keeps using
params until the RNG-15 cutover.

- `from_params(p) -> RingSpec`: maps the 7 keys into groups; `shank_taper` is
  restored to its default (`DEFAULT_SHANK_TAPER = 1.7`).
- `to_params(spec) -> dict`: flattens back to the canonical `PARAM_KEYS` order,
  **dropping** `shank_taper`; `prong_count` is returned as an `int`.

**Lossless guarantee:** `to_params(from_params(p)) == p` exactly for every
schema-valid 7-param input — floats unchanged, `prong_count` stays an `int`.
The `shank_taper` drop/restore is what keeps the 7-key dict clean while the spec
carries the 8th shaping parameter.

Canonical key order (`PARAM_KEYS`): `inner_diameter`, `band_width`,
`band_thickness`, `stone_diameter`, `stone_height`, `prong_count`,
`setting_height`.

## Versioning policy

- `version` and `archetype` are `Literal`s, so every spec is self-describing.
- **RNG-16 archetypes are additive:** new archetype values + new optional
  groups; existing solitaire specs stay valid. The JSON Schema shifts from a
  single model to a `oneOf` over archetype variants at that point — a non-
  breaking widening for solitaire consumers.
- A breaking change bumps `version` to a new `Literal`.

## Regenerating the schema

The committed `ringspec.schema.json` is generated from the model. Regenerate
after any model change:

```bash
python -c "import json,ringcad.ringspec as r;print(json.dumps(r.RingSpec.model_json_schema(),indent=2))" > docs/ringspec/ringspec.schema.json
```
