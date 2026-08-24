"""Vision can name all six cuts (RNG-33 CP4).

RNG-22's first live corpus run is the reason this ticket exists: the classifier
looked at a cushion, wrote the words "cushion cut" into its own free-text note,
and was then forced by the prompt to set `stone_shape` to "round", because round
and oval were the only shapes that could be built. The geometry caught up in CP1
to CP3; this is the half that lets the vision layer say so.

Two rules govern the ratio, and they are different questions:

  * **"I could not estimate it"** -- the 0 sentinel (docs/adr/0004: every schema
    field is required, so 0 rather than null means absent). That gets the cut's
    CONVENTIONAL default, because a marquise nobody measured is still a marquise
    and 1.0 would render it as a circle.
  * **"I estimated it, and it is outside what this cut can be"** -- that gets
    the nearest value the cut can be, which respects the reading rather than
    discarding it for a textbook number.

Degrading is still the rule for anything we genuinely cannot build: a princess
or a trillion becomes round rather than failing the whole classification, which
is what keeps the never-500 promise.
"""
from __future__ import annotations

import pytest

from ringcad.classify import _SYSTEM, ClassifyResult
from ringcad.ringspec.cuts import profile_for

NEW_CUTS = ("cushion", "emerald", "pear", "marquise")


def _result(shape="round", ratio=1.0, archetype="solitaire"):
    return ClassifyResult(
        ok=True, ring_detected=True, style=f"{shape} solitaire",
        shank_taper="straight", note="", prong_count=6, features=[],
        estimates={"stone_diameter": 6.5, "stone_height": 4.0},
        archetype=archetype, stone_shape=shape, stone_length_ratio=ratio,
    )


def _stones(shape, ratio):
    return _result(shape=shape, ratio=ratio).to_spec()["stones"]


# --- the four new cuts reach the spec --------------------------------------

@pytest.mark.parametrize("shape", NEW_CUTS)
def test_each_new_cut_survives_into_the_spec(shape):
    p = profile_for(shape)
    assert _stones(shape, p.default_ratio)["shape"] == shape


@pytest.mark.parametrize("shape", NEW_CUTS)
def test_an_unestimated_ratio_becomes_the_cuts_conventional_default(shape):
    """0 is the schema's 'not estimated' sentinel. A marquise nobody measured
    is still a marquise -- 1.0 would hand back a circle wearing the name."""
    p = profile_for(shape)
    assert _stones(shape, 0.0)["length_ratio"] == pytest.approx(p.default_ratio)


@pytest.mark.parametrize("shape", NEW_CUTS)
def test_an_estimated_ratio_outside_the_band_lands_on_the_nearest_edge(shape):
    """Not the default: vision looked and said 'very elongated'. Snapping to
    the textbook number would throw that reading away; the band edge keeps it."""
    p = profile_for(shape)
    assert _stones(shape, 4.0)["length_ratio"] == pytest.approx(p.max_ratio)
    if p.min_ratio > 1.0:
        assert _stones(shape, 1.01)["length_ratio"] == pytest.approx(p.min_ratio)


@pytest.mark.parametrize("shape", NEW_CUTS)
def test_a_named_cut_is_castable_and_schema_valid_end_to_end(shape):
    from ringcad.ringspec import validate_castability, validate_spec
    spec = validate_spec(_result(shape=shape,
                                 ratio=profile_for(shape).default_ratio).to_spec())
    assert spec.stones.shape == shape
    assert validate_castability(spec) == []


# --- what must NOT change --------------------------------------------------

@pytest.mark.parametrize("shape", ["princess", "trillion", "heart", "asscher",
                                   "", "CUSHION!!", "not a shape"])
def test_a_cut_we_cannot_build_still_degrades_to_round(shape):
    """The never-500 rule. Widening the vocabulary must not turn an unknown
    word into a validation failure."""
    assert _stones(shape, 1.5)["shape"] == "round"


def test_an_oval_at_ratio_one_is_still_recorded_as_round():
    """RNG-23's contract, untouched: a 1.0 oval IS a circle, and calling it
    oval would be a claim the geometry then has to special-case."""
    assert _stones("oval", 1.0)["shape"] == "round"


def test_a_cushion_at_ratio_one_is_a_cushion_not_a_circle():
    """The contrast that shows the rule above is about OVAL, not about 1.0. A
    square cushion is genuinely 1.00 and still has rounded corners and bowed
    sides -- it is not a circle and must not be flattened into one."""
    assert _stones("cushion", 1.0)["shape"] == "cushion"


def test_round_still_forces_ratio_one():
    """A round stone with a stray ratio must not produce an elongated model."""
    stones = _stones("round", 1.8)
    assert (stones["shape"], stones["length_ratio"]) == ("round", 1.0)


# --- the prompt has to agree with the code ---------------------------------

@pytest.mark.parametrize("shape", NEW_CUTS)
def test_the_prompt_names_every_cut_the_parser_accepts(shape):
    """The RNG-21 failure mode: every classify test stubs the client, so a
    prompt that still says these cuts cannot be built would never show up in
    a test -- only in a live call that quietly answers 'round'."""
    assert shape in _SYSTEM.lower()


def test_the_prompt_no_longer_claims_only_two_shapes_can_be_built():
    lowered = _SYSTEM.lower()
    assert "only two shapes" not in lowered
    assert "the only two shapes that can be built" not in lowered
