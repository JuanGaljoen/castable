"""The halo overcrowding gate must measure the ring it actually builds (RNG-23).

Found by running a real photo through the live path, not by a unit test: an
"oval halo with pave shoulders" classified correctly as an oval halo and was then
REJECTED by `halo_overcrowding`, because that check still computed the accent arc
from a circle of the SHORT axis while CP3 had made the halo ring an ellipse. The
elliptical ring is longer than that circle, so the gate was refusing a ring the
geometry could build.

This is the halo counterpart of the trilogy width-consumer fix in CP2 -- the same
omission, one archetype over.
"""
from __future__ import annotations

import math

import pytest

from ringcad.ringspec import validate_castability, validate_spec


def _spec(shape="round", length_ratio=1.0, stone_diameter=6.5, count=24,
          accent_d=1.2, gap=0.3):
    return validate_spec({
        "version": "1.0",
        "archetype": "halo",
        "shank": {
            "inner_diameter": 16.5, "band_width": 2.2, "band_thickness": 1.9,
        },
        "setting": {"prong_count": 4, "setting_height": 6.0},
        "stones": {
            "stone_diameter": stone_diameter, "stone_height": 4.0,
            "shape": shape, "length_ratio": length_ratio,
        },
        "halo": {
            "halo_stone_diameter": accent_d,
            "halo_stone_count": count,
            "halo_gap": gap,
            "halo_stone_height": 1.2,
        },
    })


def _codes(spec):
    return {v.code for v in validate_castability(spec)}


def test_round_halo_gate_is_unchanged():
    """A circle is the degenerate ellipse, so round results must not move."""
    assert "halo_overcrowding" in _codes(_spec(count=24, stone_diameter=6.5))
    assert "halo_overcrowding" not in _codes(_spec(count=24, stone_diameter=7.5))


def test_the_photo_that_exposed_this_is_castable_as_an_oval():
    """The real classification: 6.5mm centre, ratio 1.45, 24 accents of 1.2mm.

    On a circle of the short axis each accent gets 1.086mm and the gate fires.
    The ellipse the halo actually rides is ~30.8mm around, giving ~1.28mm each.
    """
    assert "halo_overcrowding" not in _codes(
        _spec(shape="oval", length_ratio=1.45, stone_diameter=6.5, count=24)
    )


def test_elongation_makes_more_room_not_less():
    """Monotonic: a longer ring fits at least as many accents as a round one."""
    round_codes = _codes(_spec(stone_diameter=6.5, count=24))
    oval_codes = _codes(
        _spec(shape="oval", length_ratio=1.6, stone_diameter=6.5, count=24)
    )
    assert "halo_overcrowding" in round_codes
    assert "halo_overcrowding" not in oval_codes


def test_an_oval_halo_can_still_be_overcrowded():
    """The gate must not simply switch off for ovals -- crowd it and it fires.

    `halo_stone_count` caps at 24, so the crowding comes from big accents on a
    small stone rather than from more of them.
    """
    assert "halo_overcrowding" in _codes(
        _spec(shape="oval", length_ratio=1.45, stone_diameter=2.0,
              count=24, accent_d=2.5)
    )


def test_reported_arc_matches_the_elliptical_ring():
    """The message a user reads should describe the ring being built."""
    violations = validate_castability(
        _spec(shape="oval", length_ratio=1.45, stone_diameter=2.0,
              count=24, accent_d=2.5)
    )
    v = next(v for v in violations if v.code == "halo_overcrowding")
    # Ramanujan perimeter of the accent ring: offset = gap + accent_r = 1.55.
    b, a = 1.0 + 1.55, 1.45 + 1.55
    perimeter = math.pi * (3 * (a + b) - math.sqrt((3 * a + b) * (a + 3 * b)))
    assert v.actual_mm == pytest.approx(perimeter / 24, rel=0.02)
