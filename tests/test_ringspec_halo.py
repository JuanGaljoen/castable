"""RNG-9/RNG-24 — RingSpec's Halo feature-group contract slice.

RNG-24 retired the archetype union: RingSpec is one model with an optional
`halo` group, and a legacy `archetype: "halo"` tag is translated at the
`validate_spec` edge rather than routing to a distinct type. Covers CP1-1
(legacy-tag translation), CP1-1a (loc paths, no tag prefix to strip), CP1-1b
(archetype-vs-body error disambiguation), CP1-2 (7-param back-compat), and
CP1-3 (Halo field ranges/defaults + committed example + schema drift).
Castability (CP1-4) lives in tests/test_ringspec_halo_castability.py.
"""
import json
import os

import pytest
from pydantic import TypeAdapter, ValidationError

from ringcad.ringspec import (
    Halo,
    RingSpec,
    from_params,
    spec_errors,
    to_params,
    validate_spec,
)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HALO_EXAMPLE_PATH = os.path.join(
    REPO_ROOT, "docs", "ringspec", "examples", "halo.json"
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
HALO_GROUP = {
    "halo_stone_diameter": 1.3,
    "halo_stone_count": 14,
    "halo_gap": 0.5,
    "halo_stone_height": 1.2,
}

SOLITAIRE_SPEC = {
    "archetype": "solitaire",
    "shank": SHANK,
    "setting": SETTING,
    "stones": STONES,
}
HALO_SPEC = {
    "archetype": "halo",
    "shank": SHANK,
    "setting": SETTING,
    "stones": STONES,
    "halo": HALO_GROUP,
}

# The canonical flat-7 params (matches the RNG-14 round-trip fixture).
GOOD_PARAMS = {
    "inner_diameter": 16.5,
    "band_width": 2.2,
    "band_thickness": 1.9,
    "stone_diameter": 6.5,
    "stone_height": 4.0,
    "prong_count": 6,
    "setting_height": 6.0,
}


def _fields(exc):
    return [e["field"] for e in spec_errors(exc.value)]


# --- CP1-1: a legacy archetype tag translates to the matching feature group --
def test_halo_spec_validates_to_halospec():
    spec = validate_spec(HALO_SPEC)
    assert spec.halo is not None
    assert spec.halo.halo_gap == 0.5


def test_solitaire_spec_validates_to_solitairespec():
    spec = validate_spec(SOLITAIRE_SPEC)
    assert spec.halo is None and spec.trilogy is None and spec.side_stone is None


def test_solitaire_carrying_halo_group_is_rejected():
    bad = {**SOLITAIRE_SPEC, "halo": HALO_GROUP}
    with pytest.raises(ValidationError) as exc:
        validate_spec(bad)
    assert "halo" in _fields(exc)


def test_halo_missing_its_group_is_rejected_as_missing():
    bad = {k: v for k, v in HALO_SPEC.items() if k != "halo"}
    with pytest.raises(ValidationError) as exc:
        validate_spec(bad)
    halo_err = [e for e in spec_errors(exc.value) if e["field"] == "halo"]
    assert halo_err and halo_err[0]["type"] == "missing"


# --- CP1-1a: spec_errors strips the archetype discriminator from field paths --
def test_solitaire_bad_field_strips_archetype_tag():
    bad = {**SOLITAIRE_SPEC, "shank": {**SHANK, "band_width": "wide"}}
    with pytest.raises(ValidationError) as exc:
        validate_spec(bad)
    fields = _fields(exc)
    assert "shank.band_width" in fields
    assert "solitaire.shank.band_width" not in fields


def test_halo_bad_field_strips_archetype_tag():
    bad = {**HALO_SPEC, "halo": {**HALO_GROUP, "halo_gap": "wide"}}
    with pytest.raises(ValidationError) as exc:
        validate_spec(bad)
    fields = _fields(exc)
    assert "halo.halo_gap" in fields
    assert "halo.halo.halo_gap" not in fields


# --- CP1-1b: disambiguate archetype-tag vs body error on TYPE, not loc --------
def test_unknown_archetype_names_archetype_field_via_union_tag():
    bad = {**SOLITAIRE_SPEC, "archetype": "cluster"}
    with pytest.raises(ValidationError) as exc:
        validate_spec(bad)
    errs = spec_errors(exc.value)
    archetype_err = [e for e in errs if e["field"] == "archetype"]
    assert archetype_err, errs
    assert archetype_err[0]["type"] == "union_tag_invalid"


def test_none_body_names_empty_field():
    with pytest.raises(ValidationError) as exc:
        validate_spec(None)
    errs = spec_errors(exc.value)
    body_err = [e for e in errs if e["field"] == ""]
    assert body_err, errs


# --- CP1-2: 7-param back-compat is preserved -------------------------------
def test_from_params_returns_a_featureless_spec():
    spec = from_params(GOOD_PARAMS)
    assert spec.halo is None and spec.trilogy is None and spec.side_stone is None


def test_archetypeless_dict_defaults_to_solitaire():
    body = {"shank": SHANK, "setting": SETTING, "stones": STONES}
    spec = validate_spec(body)
    assert spec.halo is None and spec.trilogy is None and spec.side_stone is None


def test_flat7_roundtrip_unaffected_by_union():
    assert to_params(from_params(GOOD_PARAMS)) == GOOD_PARAMS


# --- CP1-3: Halo group field ranges are enforced with named fields -----------
HALO_RANGE_CASES = [
    ("count_too_high", {"halo_stone_count": 25}, "halo.halo_stone_count"),
    ("count_too_low", {"halo_stone_count": 7}, "halo.halo_stone_count"),
    ("diameter_too_low", {"halo_stone_diameter": 0.5}, "halo.halo_stone_diameter"),
    ("diameter_too_high", {"halo_stone_diameter": 3.0}, "halo.halo_stone_diameter"),
    ("gap_too_low", {"halo_gap": 0.1}, "halo.halo_gap"),
    ("gap_too_high", {"halo_gap": 2.0}, "halo.halo_gap"),
    ("height_too_low", {"halo_stone_height": 0.5}, "halo.halo_stone_height"),
]


@pytest.mark.parametrize(
    "override,field",
    [(c[1], c[2]) for c in HALO_RANGE_CASES],
    ids=[c[0] for c in HALO_RANGE_CASES],
)
def test_halo_out_of_range_field_is_named(override, field):
    bad = {**HALO_SPEC, "halo": {**HALO_GROUP, **override}}
    with pytest.raises(ValidationError) as exc:
        validate_spec(bad)
    assert field in _fields(exc), f"expected '{field}' among {_fields(exc)}"


def test_halo_group_defaults_are_applied():
    spec = validate_spec({**HALO_SPEC, "halo": {}})
    assert spec.halo.halo_stone_diameter == 1.3
    assert spec.halo.halo_stone_count == 14
    assert spec.halo.halo_gap == 0.5
    assert spec.halo.halo_stone_height == 1.2


def test_halo_model_constructs_at_defaults():
    halo = Halo()
    assert (
        halo.halo_stone_diameter,
        halo.halo_stone_count,
        halo.halo_gap,
        halo.halo_stone_height,
    ) == (1.3, 14, 0.5, 1.2)


# --- CP1-3: committed example + schema-drift guard ---------------------------
def test_committed_halo_example_exists_and_validates():
    assert os.path.isfile(HALO_EXAMPLE_PATH), f"missing: {HALO_EXAMPLE_PATH}"
    with open(HALO_EXAMPLE_PATH) as fh:
        data = json.load(fh)
    assert validate_spec(data).halo is not None


def test_committed_schema_matches_generated_schema():
    expected = TypeAdapter(RingSpec).json_schema()
    with open(SCHEMA_PATH) as fh:
        committed = json.load(fh)
    assert committed == expected
