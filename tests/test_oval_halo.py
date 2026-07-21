"""A halo around an oval centre stone (RNG-23 CP3).

Two things must change together. The accent ring has to FOLLOW the girdle rather
than sit on a circle around it, and the accents have to be spaced by ARC LENGTH
rather than by equal angle: on an ellipse, equal angles crowd the accents toward
the tips, where the curve is travelling fastest per radian, so a ring that looks
even in polar coordinates is visibly bunched in metal.

Round must be untouched -- equal angle and equal arc length are the same thing on
a circle, so `RoundOutline` returns the analytic angles and the existing halo
geometry is unchanged.
"""
from __future__ import annotations

import math

import pytest

from ringcad.geometry import compose
from ringcad.geometry._common import clamps
from ringcad.geometry.outline import OvalOutline, RoundOutline
from ringcad.ringspec import validate_spec

BASE = {
    "version": "1.0",
    "archetype": "halo",
    "shank": {"inner_diameter": 16.5, "band_width": 2.2, "band_thickness": 1.9},
    "setting": {"prong_count": 6, "setting_height": 6.0},
    "halo": {
        "halo_stone_diameter": 1.3,
        "halo_stone_count": 12,
        "halo_gap": 0.4,
        "halo_stone_height": 1.2,
    },
}


def _spec(shape="round", length_ratio=1.0, stone_diameter=6.5, count=12):
    body = {
        **BASE,
        "halo": {**BASE["halo"], "halo_stone_count": count},
        "stones": {
            "stone_diameter": stone_diameter, "stone_height": 4.0,
            "shape": shape, "length_ratio": length_ratio,
        },
    }
    return validate_spec(body)


# --- the outline's arc-length machinery ------------------------------------

@pytest.mark.parametrize("n", [8, 12])
def test_round_arc_angles_are_the_analytic_even_angles(n):
    """Equal arc and equal angle coincide on a circle, so round must return the
    exact analytic values and leave existing halo geometry alone."""
    got = RoundOutline(3.25).angles_by_arc(n)
    assert got == pytest.approx([2 * math.pi * k / n for k in range(n)])


def test_round_arc_angles_respect_the_offset():
    got = RoundOutline(3.25).angles_by_arc(4, offset=0.5)
    assert got == pytest.approx([math.radians(d) for d in (45, 135, 225, 315)])


def test_oval_arc_spacing_is_not_equal_angle():
    """The whole point of CP3: on an ellipse these must differ."""
    o = OvalOutline(3.0, 5.4)
    arc = o.angles_by_arc(12)
    even = [2 * math.pi * k / 12 for k in range(12)]
    assert max(abs(a - b) for a, b in zip(arc, even)) > math.radians(2)


def test_oval_arc_spacing_gives_equal_chords():
    """Adjacent accents should be equidistant along the girdle. Chord length is
    the observable proxy, and on a smooth curve equal arcs give near-equal
    chords."""
    o = OvalOutline(3.0, 5.4)
    pts = [o.frame_at(t)[0] for t in o.angles_by_arc(16)]
    gaps = [
        (pts[(i + 1) % len(pts)] - pts[i]).length for i in range(len(pts))
    ]
    assert max(gaps) / min(gaps) < 1.06


def test_equal_angle_spacing_would_bunch_at_the_tips():
    """Pins the bug being avoided: with equal angles the chords are markedly
    uneven, so the test above is measuring something real."""
    o = OvalOutline(3.0, 5.4)
    pts = [o.frame_at(2 * math.pi * k / 16)[0] for k in range(16)]
    gaps = [
        (pts[(i + 1) % len(pts)] - pts[i]).length for i in range(len(pts))
    ]
    assert max(gaps) / min(gaps) > 1.4


def test_expanded_outline_grows_both_axes():
    o = OvalOutline(3.0, 5.4).expanded(0.7)
    assert o.half_width("x") == pytest.approx(3.7)
    assert o.half_width("y") == pytest.approx(6.1)


def test_expanded_round_stays_round():
    o = RoundOutline(3.0).expanded(0.7)
    assert isinstance(o, RoundOutline)
    assert o.half_width("x") == pytest.approx(3.7)


# --- the composed halo -----------------------------------------------------

def test_round_halo_ring_radius_is_unchanged():
    """The halo ring for a round stone must still sit at stone_r + gap + accent_r."""
    spec = _spec()
    c = clamps(spec)
    ring = c["outline"].expanded(0.4 + 1.3 / 2)
    assert ring.half_width("x") == pytest.approx(6.5 / 2 + 0.4 + 0.65)


@pytest.mark.parametrize("length_ratio", [1.3, 1.8])
def test_oval_halo_is_one_raw_watertight_manifold(raw_validate, length_ratio):
    spec = _spec(shape="oval", length_ratio=length_ratio, stone_diameter=6.0)
    result = raw_validate(compose(spec))
    assert result.is_watertight
    assert result.non_manifold_edges == 0
    assert result.body_count == 1


def test_oval_halo_has_all_its_accents(raw_validate):
    """Volume-bearing guard per docs/adr/0005: a dropped accent ring would still
    report watertight and single-body."""
    round_vol = compose(_spec(stone_diameter=6.0)).volume
    oval_vol = compose(
        _spec(shape="oval", length_ratio=1.6, stone_diameter=6.0)
    ).volume
    # An oval halo is a longer ring of the same accents on a larger gallery, so
    # it must carry MORE metal than the round one, not less.
    assert oval_vol > round_vol
