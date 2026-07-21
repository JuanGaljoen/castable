"""Vision reports the centre stone's shape (RNG-23 CP4).

Closes the loop the whole ticket exists for: until the classifier can say "oval",
an oval photo still produces a round model no matter how good the geometry is.

Schema discipline from docs/adr/0004 applies to the two new fields: they are
REQUIRED with no defaults, because strict structured output treats a defaulted
field as optional and many optional fields make the real Messages API hang. The
model is told to answer "round" when unsure, which is the safe default anyway.
"""
from __future__ import annotations

import pytest

from ringcad.classify import ClassifyResult, RingClassification


def _result(shape="round", ratio=1.0, archetype="solitaire", **kw):
    return ClassifyResult(
        ok=True,
        ring_detected=True,
        style="round solitaire",
        shank_taper="straight",
        note="",
        prong_count=6,
        features=[],
        estimates={"stone_diameter": 6.5, "stone_height": 4.0},
        archetype=archetype,
        stone_shape=shape,
        stone_length_ratio=ratio,
        **kw,
    )


# --- the schema stays API-safe (docs/adr/0004) -----------------------------

def test_new_shape_fields_are_required_not_optional():
    schema = RingClassification.model_json_schema()
    required = set(schema["required"])
    assert "stone_shape" in required
    assert "stone_length_ratio" in required


def test_shape_field_is_a_plain_string_not_a_union():
    """A Literal or an optional would add a union param; ADR-0004 keeps the
    schema flat and validates the value in code instead."""
    prop = RingClassification.model_json_schema()["properties"]["stone_shape"]
    assert prop.get("type") == "string"
    assert "anyOf" not in prop


# --- the assembled spec carries the shape ----------------------------------

def test_oval_reaches_the_spec():
    spec = _result(shape="oval", ratio=1.6).to_spec()
    assert spec["stones"]["shape"] == "oval"
    assert spec["stones"]["length_ratio"] == pytest.approx(1.6)


def test_round_is_the_default_and_forces_ratio_one():
    """A round stone with a stray ratio must not produce an elongated model."""
    spec = _result(shape="round", ratio=1.8).to_spec()
    assert spec["stones"]["shape"] == "round"
    assert spec["stones"]["length_ratio"] == 1.0


@pytest.mark.parametrize("shape", ["emerald", "pear", "marquise", "", "OVAL!"])
def test_unsupported_shapes_fall_back_to_round(shape):
    """RNG-23 builds round and oval only. Anything else must degrade to a
    buildable spec rather than fail validation, preserving the never-500 rule."""
    spec = _result(shape=shape, ratio=1.5).to_spec()
    assert spec["stones"]["shape"] == "round"


def test_case_and_whitespace_are_tolerated():
    # Needs a real elongation: at ratio 1.0 the stone is a circle whatever the
    # model called it, which the test below pins separately.
    assert _result(shape=" Oval ", ratio=1.5).to_spec()["stones"]["shape"] == "oval"


# --- ratios are clamped to what is castable --------------------------------

@pytest.mark.parametrize("raw,expected", [
    (0.0, 1.0),    # "not estimated" sentinel
    (0.5, 1.0),    # below 1 is the same stone rotated
    (1.0, 1.0),
    (2.5, 2.5),
    (4.0, 2.5),    # beyond the schema cap
])
def test_ratio_is_clamped_into_the_schema_range(raw, expected):
    spec = _result(shape="oval", ratio=raw).to_spec()
    assert spec["stones"]["length_ratio"] == pytest.approx(expected)


def test_a_ratio_of_one_means_round_even_if_the_model_said_oval():
    """An 'oval' with ratio 1.0 is a circle; recording it as oval would be a
    lie the geometry then has to special-case."""
    spec = _result(shape="oval", ratio=1.0).to_spec()
    assert spec["stones"]["shape"] == "round"


# --- the spec still validates and stays castable ---------------------------

def test_assembled_oval_spec_is_schema_valid_and_castable():
    from ringcad.ringspec import validate_castability, validate_spec

    spec = _result(shape="oval", ratio=1.8).to_spec()
    validated = validate_spec(spec)
    assert validated.stones.shape == "oval"
    assert [v.code for v in validate_castability(validated)] == []


def test_shape_survives_on_a_non_solitaire_archetype():
    spec = _result(shape="oval", ratio=1.5, archetype="halo").to_spec()
    assert spec["archetype"] == "halo"
    assert spec["stones"]["shape"] == "oval"
