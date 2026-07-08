"""RNG-10 Checkpoint 1 — Trilogy RingSpec discriminated-union contract slice.

RED until the union lands: Trilogy / TrilogySpec do not exist yet, so the
import below fails at collection (ImportError). That is the correct RED
signal — the feature (the new union member) is MISSING, not buggy.

Mirrors tests/test_ringspec_halo.py's CP1 pattern: union routing, tag-stripped
field paths, field ranges/defaults, committed example + schema drift.
Castability (side/center spacing) lives in
tests/test_ringspec_trilogy_castability.py.
"""
import json
import os

import pytest
from pydantic import TypeAdapter, ValidationError

from ringcad.ringspec import (
    RingSpec,
    SolitaireSpec,
    Trilogy,
    TrilogySpec,
    spec_errors,
    validate_spec,
)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TRILOGY_EXAMPLE_PATH = os.path.join(
    REPO_ROOT, "docs", "ringspec", "examples", "trilogy.json"
)
SCHEMA_PATH = os.path.join(REPO_ROOT, "docs", "ringspec", "ringspec.schema.json")

SHANK = {
    "inner_diameter": 16.5,
    "band_width": 2.2,
    "band_thickness": 1.9,
    "shank_taper": 1.7,
}
SETTING = {"prong_count": 6, "setting_height": 6.0}
STONES = {"stone_diameter": 6.5, "stone_height": 4.0}
TRILOGY_GROUP = {
    "side_stone_diameter": 2.5,
    "side_stone_height": 1.8,
    "side_stone_gap": 0.6,
}

SOLITAIRE_SPEC = {
    "archetype": "solitaire",
    "shank": SHANK,
    "setting": SETTING,
    "stones": STONES,
}
TRILOGY_SPEC = {
    "archetype": "trilogy",
    "shank": SHANK,
    "setting": SETTING,
    "stones": STONES,
    "trilogy": TRILOGY_GROUP,
}


def _fields(exc):
    return [e["field"] for e in spec_errors(exc.value)]


# --- CP1-1: the union routes trilogy to TrilogySpec --------------------------
def test_trilogy_spec_validates_to_trilogyspec():
    spec = validate_spec(TRILOGY_SPEC)
    assert isinstance(spec, TrilogySpec)
    assert spec.trilogy.side_stone_gap == 0.6


def test_solitaire_carrying_trilogy_group_is_rejected():
    bad = {**SOLITAIRE_SPEC, "trilogy": TRILOGY_GROUP}
    with pytest.raises(ValidationError) as exc:
        validate_spec(bad)
    assert "trilogy" in _fields(exc)


def test_trilogy_missing_its_group_is_rejected_as_missing():
    bad = {k: v for k, v in TRILOGY_SPEC.items() if k != "trilogy"}
    with pytest.raises(ValidationError) as exc:
        validate_spec(bad)
    trilogy_err = [e for e in spec_errors(exc.value) if e["field"] == "trilogy"]
    assert trilogy_err and trilogy_err[0]["type"] == "missing"


# --- CP1-1a: spec_errors strips the archetype discriminator from field paths --
def test_trilogy_bad_field_strips_archetype_tag():
    bad = {**TRILOGY_SPEC, "trilogy": {**TRILOGY_GROUP, "side_stone_gap": "wide"}}
    with pytest.raises(ValidationError) as exc:
        validate_spec(bad)
    fields = _fields(exc)
    assert "trilogy.side_stone_gap" in fields
    assert "trilogy.trilogy.side_stone_gap" not in fields


# --- back-compat: existing solitaire/union behaviour is unaffected -----------
def test_solitaire_spec_still_validates_to_solitairespec():
    spec = validate_spec(SOLITAIRE_SPEC)
    assert isinstance(spec, SolitaireSpec)


# --- CP1-3: Trilogy group field ranges are enforced with named fields --------
TRILOGY_RANGE_CASES = [
    ("diameter_too_low", {"side_stone_diameter": 0.5}, "trilogy.side_stone_diameter"),
    ("diameter_too_high", {"side_stone_diameter": 7.0}, "trilogy.side_stone_diameter"),
    ("height_too_low", {"side_stone_height": 0.5}, "trilogy.side_stone_height"),
    ("height_too_high", {"side_stone_height": 5.0}, "trilogy.side_stone_height"),
    ("gap_too_low", {"side_stone_gap": 0.1}, "trilogy.side_stone_gap"),
    ("gap_too_high", {"side_stone_gap": 3.0}, "trilogy.side_stone_gap"),
]


@pytest.mark.parametrize(
    "override,field",
    [(c[1], c[2]) for c in TRILOGY_RANGE_CASES],
    ids=[c[0] for c in TRILOGY_RANGE_CASES],
)
def test_trilogy_out_of_range_field_is_named(override, field):
    bad = {**TRILOGY_SPEC, "trilogy": {**TRILOGY_GROUP, **override}}
    with pytest.raises(ValidationError) as exc:
        validate_spec(bad)
    assert field in _fields(exc), f"expected '{field}' among {_fields(exc)}"


def test_trilogy_group_defaults_are_applied():
    spec = validate_spec({**TRILOGY_SPEC, "trilogy": {}})
    assert spec.trilogy.side_stone_diameter == 2.5
    assert spec.trilogy.side_stone_height == 1.8
    assert spec.trilogy.side_stone_gap == 0.6


def test_trilogy_model_constructs_at_defaults():
    trilogy = Trilogy()
    assert (
        trilogy.side_stone_diameter,
        trilogy.side_stone_height,
        trilogy.side_stone_gap,
    ) == (2.5, 1.8, 0.6)


# --- CP1-3: committed example + schema-drift guard ---------------------------
def test_committed_trilogy_example_exists_and_validates():
    assert os.path.isfile(TRILOGY_EXAMPLE_PATH), f"missing: {TRILOGY_EXAMPLE_PATH}"
    with open(TRILOGY_EXAMPLE_PATH) as fh:
        data = json.load(fh)
    assert isinstance(validate_spec(data), TrilogySpec)


def test_committed_schema_matches_generated_union_schema():
    expected = TypeAdapter(RingSpec).json_schema()
    with open(SCHEMA_PATH) as fh:
        committed = json.load(fh)
    assert committed == expected
