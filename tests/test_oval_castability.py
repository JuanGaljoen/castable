"""Castability of an elongated centre stone (RNG-23 CP2).

Elongation is not free: an ellipse's tightest bend is `semi_minor^2/semi_major`,
so raising `length_ratio` (or shrinking the stone at a fixed ratio) sharpens the
apex. Below a point the seat collar cannot follow the girdle at all -- a tube of
section radius r swept along a curve whose radius of curvature is smaller than r
self-intersects, which is degenerate metal rather than merely thin metal.

That is a genuine geometric fact about the placement, in the spirit of
docs/adr/0002 and 0003: it is checked directly rather than through a
wall-thickness proxy.

The trilogy consequence is checked too. The side stones flank along the SAME
axis an N-S oval is longest on, so an oval centre reaches further toward them
than a round one of equal `stone_diameter`.
"""
from __future__ import annotations

import pytest

from ringcad.ringspec import validate_castability, validate_spec


def _spec(shape="round", length_ratio=1.0, stone_diameter=6.5, archetype=None):
    body = {
        "version": "1.0",
        "archetype": archetype or "solitaire",
        "shank": {
            "inner_diameter": 16.5, "band_width": 2.2, "band_thickness": 1.9,
        },
        "setting": {"prong_count": 6, "setting_height": 6.0},
        "stones": {
            "stone_diameter": stone_diameter, "stone_height": 4.0,
            "shape": shape, "length_ratio": length_ratio,
        },
    }
    if archetype == "trilogy":
        # Large side stones at the minimum legal gap: the configuration where the
        # centre stone's reach actually decides the outcome. With smaller side
        # stones the arc-vs-chord margin absorbs even a 2.5x oval, so the check
        # would pass for both and prove nothing.
        body["trilogy"] = {
            "side_stone_diameter": 6.0,
            "side_stone_height": 1.8,
            "side_stone_gap": 0.3,
        }
    return validate_spec(body)


def _codes(spec):
    return {v.code for v in validate_castability(spec)}


# --- round is unaffected ---------------------------------------------------

def test_round_stone_raises_no_shape_violation():
    assert "stone_curvature" not in _codes(_spec())


@pytest.mark.parametrize("diameter", [2.0, 6.5, 10.0])
def test_round_stays_castable_at_every_size(diameter):
    assert "stone_curvature" not in _codes(_spec(stone_diameter=diameter))


# --- the curvature floor ---------------------------------------------------

def test_generous_oval_is_castable():
    assert "stone_curvature" not in _codes(
        _spec(shape="oval", length_ratio=1.6, stone_diameter=8.0)
    )


def test_small_stone_at_high_elongation_is_rejected():
    """d=2.0 at ratio 2.5 gives a tip curvature radius of 0.4mm, below the
    0.45mm seat collar section -- the collar would self-intersect at the apex."""
    codes = _codes(_spec(shape="oval", length_ratio=2.5, stone_diameter=2.0))
    assert "stone_curvature" in codes


def test_the_violation_names_the_offending_field():
    violations = validate_castability(
        _spec(shape="oval", length_ratio=2.5, stone_diameter=2.0)
    )
    v = next(v for v in violations if v.code == "stone_curvature")
    assert v.field in ("stones.length_ratio", "stones.stone_diameter")
    assert v.actual_mm < v.limit_mm


def test_same_stone_becomes_castable_when_less_elongated():
    """The fix a user can act on: reduce the elongation, keep the stone."""
    assert "stone_curvature" in _codes(
        _spec(shape="oval", length_ratio=2.5, stone_diameter=2.0)
    )
    assert "stone_curvature" not in _codes(
        _spec(shape="oval", length_ratio=1.2, stone_diameter=2.0)
    )


# --- the bore is a width-consumer too --------------------------------------

def test_an_oval_longer_than_the_finger_bore_is_rejected():
    """`stone_exceeds_bore` compared the SHORT axis, so a 10mm stone at ratio 2.5
    -- 25mm long on a 16.5mm bore -- passed. A stone longer than the hole the
    finger goes through is not a ring."""
    assert "stone_exceeds_bore" in _codes(
        _spec(shape="oval", length_ratio=2.5, stone_diameter=10.0)
    )


def test_a_round_stone_inside_the_bore_still_passes():
    assert "stone_exceeds_bore" not in _codes(_spec(stone_diameter=10.0))


def test_a_modest_oval_inside_the_bore_still_passes():
    assert "stone_exceeds_bore" not in _codes(
        _spec(shape="oval", length_ratio=1.4, stone_diameter=8.0)
    )


# --- the trilogy consequence -----------------------------------------------

def test_oval_centre_consumes_more_trilogy_clearance_than_round():
    """An N-S oval reaches toward the side stones on its LONG axis, so a gap
    that is fine for a round centre can overcrowd once the stone is elongated."""
    round_codes = _codes(_spec(archetype="trilogy", stone_diameter=6.5))
    oval_codes = _codes(
        _spec(archetype="trilogy", shape="oval", length_ratio=2.5,
              stone_diameter=6.5)
    )
    assert "trilogy_overcrowding" not in round_codes
    assert "trilogy_overcrowding" in oval_codes
