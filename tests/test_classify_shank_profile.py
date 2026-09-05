"""Vision reports the shank cross-section profile (RNG-25 CP3).

Closes the loop the whole ticket exists for: until the classifier can say
"knife edge", a knife-edge photo still produces a court model no matter how
good the geometry is.

Schema discipline from docs/adr/0004 applies to the two new fields, mirroring
`stone_shape`/`stone_length_ratio` (RNG-23 CP4): REQUIRED with no defaults,
plain `str` not `Literal`/union, degrading unknown values in code rather than
failing the whole classification.
"""
from __future__ import annotations

import pytest

from ringcad.classify import ClassifyResult, RingClassification


def _result(outer="domed", inner="domed", archetype="solitaire", **kw):
    return ClassifyResult(
        ok=True,
        ring_detected=True,
        style="knife edge solitaire",
        shank_taper="straight",
        note="",
        prong_count=6,
        features=[],
        estimates={"band_width": 2.2, "band_thickness": 1.9},
        archetype=archetype,
        outer_profile=outer,
        inner_profile=inner,
        **kw,
    )


# --- the schema stays API-safe (docs/adr/0004) -----------------------------

def test_new_profile_fields_are_required_not_optional():
    schema = RingClassification.model_json_schema()
    required = set(schema["required"])
    assert "outer_profile" in required
    assert "inner_profile" in required


def test_profile_fields_are_plain_strings_not_unions():
    """A Literal or an optional would add a union param; ADR-0004 keeps the
    schema flat and validates the value in code instead."""
    props = RingClassification.model_json_schema()["properties"]
    for name in ("outer_profile", "inner_profile"):
        assert props[name].get("type") == "string"
        assert "anyOf" not in props[name]


# --- the assembled spec carries the profile --------------------------------

def test_knife_edge_reaches_the_spec():
    spec = _result(outer="knife_edge", inner="flat").to_spec()
    assert spec["shank"]["outer_profile"] == "knife_edge"
    assert spec["shank"]["inner_profile"] == "flat"


def test_court_is_the_default():
    spec = _result(outer="domed", inner="domed").to_spec()
    assert spec["shank"]["outer_profile"] == "domed"
    assert spec["shank"]["inner_profile"] == "domed"


@pytest.mark.parametrize("outer", ["bulging", "", "KNIFE!", "round"])
def test_unsupported_outer_profile_falls_back_to_domed(outer):
    spec = _result(outer=outer, inner="flat").to_spec()
    assert spec["shank"]["outer_profile"] == "domed"


@pytest.mark.parametrize("inner", ["bulging", "", "DOMED!", "knife_edge"])
def test_unsupported_inner_profile_falls_back_to_domed(inner):
    spec = _result(outer="flat", inner=inner).to_spec()
    assert spec["shank"]["inner_profile"] == "domed"


def test_case_and_whitespace_are_tolerated():
    spec = _result(outer=" Knife_Edge ", inner=" Flat ").to_spec()
    assert spec["shank"]["outer_profile"] == "knife_edge"
    assert spec["shank"]["inner_profile"] == "flat"


def test_unsupported_pairing_falls_back_independently():
    """Each axis degrades on its own -- an unrecognised outer must not drag
    a perfectly valid inner down with it, and vice versa."""
    spec = _result(outer="bulging", inner="flat").to_spec()
    assert spec["shank"]["outer_profile"] == "domed"
    assert spec["shank"]["inner_profile"] == "flat"
