"""RNG-11 Checkpoint 1 — SideStone RingSpec discriminated-union contract slice.

RED until the union lands: SideStone / SideStoneSpec do not exist yet, so the
import below fails at collection (ImportError). That is the correct RED
signal — the feature (the new union member) is MISSING, not buggy.

Mirrors tests/test_ringspec_trilogy.py's CP1 pattern: union routing,
tag-stripped field paths, field ranges/defaults, committed example + schema
drift. Castability (row/base-clearance spacing) lives in
tests/test_ringspec_side_stone_castability.py.
"""
import json
import os

import pytest
from pydantic import TypeAdapter, ValidationError

from ringcad.ringspec import (
    RingSpec,
    SideStone,
    SideStoneSpec,
    SolitaireSpec,
    spec_errors,
    validate_spec,
)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SIDE_STONE_EXAMPLE_PATH = os.path.join(
    REPO_ROOT, "docs", "ringspec", "examples", "side_stone.json"
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
SIDE_STONE_GROUP = {
    "accent_stone_diameter": 1.5,
    "accent_stone_height": 1.2,
    "accent_count_per_side": 3,
    "accent_gap": 0.3,
    "retention": "channel",
}

SOLITAIRE_SPEC = {
    "archetype": "solitaire",
    "shank": SHANK,
    "setting": SETTING,
    "stones": STONES,
}
SIDE_STONE_SPEC = {
    "archetype": "side_stone",
    "shank": SHANK,
    "setting": SETTING,
    "stones": STONES,
    "side_stone": SIDE_STONE_GROUP,
}


def _fields(exc):
    return [e["field"] for e in spec_errors(exc.value)]


# --- CP1-1: the union routes side_stone to SideStoneSpec ----------------------
def test_side_stone_spec_validates_to_sidestonespec():
    spec = validate_spec(SIDE_STONE_SPEC)
    assert isinstance(spec, SideStoneSpec)
    assert spec.side_stone.accent_count_per_side == 3


def test_solitaire_carrying_side_stone_group_is_rejected():
    bad = {**SOLITAIRE_SPEC, "side_stone": SIDE_STONE_GROUP}
    with pytest.raises(ValidationError) as exc:
        validate_spec(bad)
    assert "side_stone" in _fields(exc)


def test_side_stone_missing_its_group_is_rejected_as_missing():
    bad = {k: v for k, v in SIDE_STONE_SPEC.items() if k != "side_stone"}
    with pytest.raises(ValidationError) as exc:
        validate_spec(bad)
    err = [e for e in spec_errors(exc.value) if e["field"] == "side_stone"]
    assert err and err[0]["type"] == "missing"


# --- CP1-1a: spec_errors strips the archetype discriminator from field paths --
def test_side_stone_bad_field_strips_archetype_tag():
    bad = {
        **SIDE_STONE_SPEC,
        "side_stone": {**SIDE_STONE_GROUP, "accent_gap": "wide"},
    }
    with pytest.raises(ValidationError) as exc:
        validate_spec(bad)
    fields = _fields(exc)
    assert "side_stone.accent_gap" in fields
    assert "side_stone.side_stone.accent_gap" not in fields


# --- back-compat: existing solitaire/union behaviour is unaffected -----------
def test_solitaire_spec_still_validates_to_solitairespec():
    spec = validate_spec(SOLITAIRE_SPEC)
    assert isinstance(spec, SolitaireSpec)


# --- CP1-3: SideStone group field ranges are enforced with named fields ------
SIDE_STONE_RANGE_CASES = [
    ("diameter_too_low", {"accent_stone_diameter": 0.5},
     "side_stone.accent_stone_diameter"),
    ("diameter_too_high", {"accent_stone_diameter": 3.0},
     "side_stone.accent_stone_diameter"),
    ("height_too_low", {"accent_stone_height": 0.5},
     "side_stone.accent_stone_height"),
    ("height_too_high", {"accent_stone_height": 4.0},
     "side_stone.accent_stone_height"),
    ("count_too_low", {"accent_count_per_side": 0},
     "side_stone.accent_count_per_side"),
    ("count_too_high", {"accent_count_per_side": 9},
     "side_stone.accent_count_per_side"),
    ("gap_too_low", {"accent_gap": 0.1}, "side_stone.accent_gap"),
    ("gap_too_high", {"accent_gap": 2.0}, "side_stone.accent_gap"),
]


@pytest.mark.parametrize(
    "override,field",
    [(c[1], c[2]) for c in SIDE_STONE_RANGE_CASES],
    ids=[c[0] for c in SIDE_STONE_RANGE_CASES],
)
def test_side_stone_out_of_range_field_is_named(override, field):
    bad = {**SIDE_STONE_SPEC, "side_stone": {**SIDE_STONE_GROUP, **override}}
    with pytest.raises(ValidationError) as exc:
        validate_spec(bad)
    assert field in _fields(exc), f"expected '{field}' among {_fields(exc)}"


# --- CP1: retention is a Literal["channel"] — a "pave" value 400s cleanly ----
def test_side_stone_retention_pave_is_rejected_naming_field():
    bad = {
        **SIDE_STONE_SPEC,
        "side_stone": {**SIDE_STONE_GROUP, "retention": "pave"},
    }
    with pytest.raises(ValidationError) as exc:
        validate_spec(bad)
    assert "side_stone.retention" in _fields(exc)


def test_side_stone_group_defaults_are_applied():
    spec = validate_spec({**SIDE_STONE_SPEC, "side_stone": {}})
    assert spec.side_stone.accent_stone_diameter == 1.5
    assert spec.side_stone.accent_stone_height == 1.2
    assert spec.side_stone.accent_count_per_side == 3
    assert spec.side_stone.accent_gap == 0.3
    assert spec.side_stone.retention == "channel"


def test_side_stone_model_constructs_at_defaults():
    side_stone = SideStone()
    assert (
        side_stone.accent_stone_diameter,
        side_stone.accent_stone_height,
        side_stone.accent_count_per_side,
        side_stone.accent_gap,
        side_stone.retention,
    ) == (1.5, 1.2, 3, 0.3, "channel")


# --- CP1-3: committed example + schema-drift guard ---------------------------
def test_committed_side_stone_example_exists_and_validates():
    assert os.path.isfile(SIDE_STONE_EXAMPLE_PATH), (
        f"missing: {SIDE_STONE_EXAMPLE_PATH}"
    )
    with open(SIDE_STONE_EXAMPLE_PATH) as fh:
        data = json.load(fh)
    assert isinstance(validate_spec(data), SideStoneSpec)


def test_committed_schema_matches_generated_union_schema():
    expected = TypeAdapter(RingSpec).json_schema()
    with open(SCHEMA_PATH) as fh:
        committed = json.load(fh)
    assert committed == expected
