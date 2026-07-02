"""RNG-14 AC2 + AC4 — schema validation and committed documented schema.

RED until `ringcad.ringspec` exists (and, for AC4, until the implementer
commits docs/ringspec/examples/solitaire.json). Both failures are legitimate
RED: the feature/artifact is MISSING.

AC2: malformed specs are rejected with a field-level error naming the offending
field and reason; unknown/extra fields are forbidden; errors are JSON
serializable. AC4: a JSON Schema is generated from the model and a valid example
spec is committed.
"""
import json
import os

import pytest
from pydantic import TypeAdapter, ValidationError

from ringcad.ringspec import (
    HaloSpec,
    RingSpec,
    SolitaireSpec,
    spec_errors,
    validate_spec,
)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXAMPLE_PATH = os.path.join(
    REPO_ROOT, "docs", "ringspec", "examples", "solitaire.json"
)

# A known-good nested spec the malformed cases mutate one field at a time.
GOOD_SPEC = {
    "shank": {
        "inner_diameter": 16.5,
        "band_width": 2.2,
        "band_thickness": 1.9,
        "shank_taper": 1.7,
    },
    "setting": {"prong_count": 6, "setting_height": 6.0},
    "stones": {"stone_diameter": 6.5, "stone_height": 4.0},
}


def _mutate(**changes):
    """Deep-ish copy of GOOD_SPEC with top-level or nested-group overrides."""
    spec = {k: dict(v) if isinstance(v, dict) else v for k, v in GOOD_SPEC.items()}
    for key, val in changes.items():
        spec[key] = val
    return spec


# Each case: (label, malformed spec, expected offending "field" path).
MALFORMED_CASES = [
    (
        "wrong_type_band_width",
        _mutate(shank={**GOOD_SPEC["shank"], "band_width": "wide"}),
        "shank.band_width",
    ),
    (
        "out_of_range_band_thickness",
        _mutate(shank={**GOOD_SPEC["shank"], "band_thickness": -1}),
        "shank.band_thickness",
    ),
    (
        "prong_count_5",
        _mutate(setting={**GOOD_SPEC["setting"], "prong_count": 5}),
        "setting.prong_count",
    ),
    (
        "prong_count_bool",
        _mutate(setting={**GOOD_SPEC["setting"], "prong_count": True}),
        "setting.prong_count",
    ),
    ("unsupported_archetype", _mutate(archetype="cluster"), "archetype"),
    ("extra_top_level_field", _mutate(foo=1), "foo"),
    ("missing_required_group", {k: v for k, v in GOOD_SPEC.items() if k != "stones"}, "stones"),
]


# --- AC2: malformed specs rejected with a named offending field --------------
@pytest.mark.parametrize(
    "spec,field",
    [(c[1], c[2]) for c in MALFORMED_CASES],
    ids=[c[0] for c in MALFORMED_CASES],
)
def test_malformed_spec_raises_and_names_field(spec, field):
    with pytest.raises(ValidationError) as exc_info:
        validate_spec(spec)
    errors = spec_errors(exc_info.value)
    fields = [e["field"] for e in errors]
    assert field in fields, f"expected '{field}' among {fields}"


def test_missing_required_field_is_missing_type():
    spec = {k: v for k, v in GOOD_SPEC.items() if k != "stones"}
    with pytest.raises(ValidationError) as exc_info:
        validate_spec(spec)
    errors = spec_errors(exc_info.value)
    stones_err = [e for e in errors if e["field"] == "stones"]
    assert stones_err and stones_err[0]["type"] == "missing"


def test_none_body_raises_top_level_error():
    with pytest.raises(ValidationError) as exc_info:
        validate_spec(None)
    errors = spec_errors(exc_info.value)
    # Top-level (not field-scoped) error — empty dotted path.
    assert any(e["field"] == "" for e in errors), errors


# --- AC2: errors are JSON-serializable (for API surfacing in RNG-15) ---------
@pytest.mark.parametrize(
    "spec", [c[1] for c in MALFORMED_CASES], ids=[c[0] for c in MALFORMED_CASES]
)
def test_spec_errors_are_json_serializable(spec):
    with pytest.raises(ValidationError) as exc_info:
        validate_spec(spec)
    json.dumps(spec_errors(exc_info.value))  # raises if any value is non-JSON


def test_valid_spec_passes_validate_spec():
    spec = validate_spec(GOOD_SPEC)
    assert isinstance(spec, SolitaireSpec)


# --- AC4: generated JSON Schema + committed example --------------------------
def test_model_json_schema_exposes_top_level_groups():
    schema = TypeAdapter(RingSpec).json_schema()
    assert isinstance(schema, dict)
    assert "oneOf" in schema
    assert "discriminator" in schema
    defs = schema.get("$defs", {})
    assert "SolitaireSpec" in defs
    assert "HaloSpec" in defs


def test_committed_example_exists_and_validates():
    assert os.path.isfile(EXAMPLE_PATH), f"missing committed example: {EXAMPLE_PATH}"
    with open(EXAMPLE_PATH) as fh:
        data = json.load(fh)
    spec = validate_spec(data)
    assert isinstance(spec, SolitaireSpec)
