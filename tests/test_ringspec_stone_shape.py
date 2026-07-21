"""Centre-stone shape in RingSpec (RNG-23 CP1).

The contract half of the stone-shape work: `shape` and `length_ratio` join the
stones group, both defaulted so that every spec written before RNG-23 stays
valid and still means a round stone. `stone_diameter` keeps its existing meaning
as the SHORT axis (the width); the long axis is `stone_diameter * length_ratio`.

A ratio rather than an explicit length because a ratio is what the vision layer
can actually see in a photo (it feeds RNG-26 directly), and because
`length_ratio == 1.0` makes round fall out of the same code path instead of
needing a branch.
"""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from ringcad.ringspec import validate_spec


def _spec(**stone_overrides) -> dict:
    stones = {"stone_diameter": 6.5, "stone_height": 4.0}
    stones.update(stone_overrides)
    return {
        "version": "1.0",
        "archetype": "solitaire",
        "shank": {
            "inner_diameter": 16.5,
            "band_width": 2.2,
            "band_thickness": 1.9,
        },
        "setting": {"prong_count": 6, "setting_height": 6.0},
        "stones": stones,
    }


# --- backward compatibility (the no-breaking-change criterion) --------------

def test_spec_without_shape_is_still_valid():
    spec = validate_spec(_spec())
    assert spec.stones.shape == "round"
    assert spec.stones.length_ratio == 1.0


def test_round_is_the_default_meaning_of_an_old_spec():
    """An old spec and an explicitly-round new spec must be indistinguishable."""
    old = validate_spec(_spec())
    new = validate_spec(_spec(shape="round", length_ratio=1.0))
    assert old.stones.model_dump() == new.stones.model_dump()


# --- the new fields --------------------------------------------------------

def test_oval_shape_round_trips():
    spec = validate_spec(_spec(shape="oval", length_ratio=1.6))
    assert spec.stones.shape == "oval"
    assert spec.stones.length_ratio == pytest.approx(1.6)


def test_unsupported_shape_is_rejected_naming_the_field():
    """Emerald / pear / marquise are deliberately out of scope for RNG-23: the
    cornered and pointed families need a different prong primitive. They must be
    rejected loudly, not silently treated as round."""
    with pytest.raises(ValidationError) as exc:
        validate_spec(_spec(shape="emerald"))
    assert "shape" in str(exc.value)


@pytest.mark.parametrize("ratio", [0.9, 0.0, -1.0])
def test_ratio_below_one_is_rejected(ratio):
    """length_ratio is long/short, so it cannot be less than 1: a stone wider
    than it is long is the same stone rotated, not a new shape."""
    with pytest.raises(ValidationError):
        validate_spec(_spec(shape="oval", length_ratio=ratio))


def test_absurd_elongation_is_rejected():
    with pytest.raises(ValidationError):
        validate_spec(_spec(shape="oval", length_ratio=9.0))


def test_boundary_ratios_are_accepted():
    assert validate_spec(_spec(length_ratio=1.0)).stones.length_ratio == 1.0
    assert validate_spec(
        _spec(shape="oval", length_ratio=2.5)
    ).stones.length_ratio == pytest.approx(2.5)
