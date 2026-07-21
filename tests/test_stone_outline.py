"""StoneOutline — the girdle abstraction that replaces the `stone_r` scalar
(RNG-23 CP1).

Tested through the public interface only: the two consumer kinds are
curve-walkers (seat / bezel / prong_setting / halo, which need the path, prong
angles and frames) and width-consumers (trilogy / overcrowding, which need only
a half-width). Round is the degenerate case INSIDE the abstraction, so the round
outline must reproduce today's even prong spacing exactly.
"""
from __future__ import annotations

import math

import pytest

from ringcad.geometry.outline import OvalOutline, RoundOutline

TWO_PI = 2 * math.pi


def _norm(a: float) -> float:
    """Normalise an angle into [0, 2pi)."""
    return a % TWO_PI


# --- width consumers -------------------------------------------------------

def test_round_half_width_is_the_radius_on_both_axes():
    o = RoundOutline(3.25)
    assert o.half_width("x") == pytest.approx(3.25)
    assert o.half_width("y") == pytest.approx(3.25)


def test_oval_half_width_is_per_axis():
    """Semi-major lies along local Y (the band-tangential / finger direction);
    semi-minor across the band on local X."""
    o = OvalOutline(semi_minor=2.5, semi_major=4.0)
    assert o.half_width("x") == pytest.approx(2.5)
    assert o.half_width("y") == pytest.approx(4.0)


def test_unknown_axis_is_rejected():
    with pytest.raises(ValueError):
        RoundOutline(3.0).half_width("z")


# --- prong placement -------------------------------------------------------

@pytest.mark.parametrize("n", [4, 6])
def test_round_prongs_keep_todays_even_spacing(n):
    """Round must be unchanged from the pre-RNG-23 geometry: k * 2pi/n."""
    angles = RoundOutline(3.0).prong_angles(n)
    assert angles == pytest.approx([k * TWO_PI / n for k in range(n)])


@pytest.mark.parametrize("n", [4, 6])
def test_oval_prongs_never_sit_on_a_tip(n):
    """The tips (ends of the major axis, at pi/2 and 3pi/2) are the highest-
    curvature points and the worst place for a claw. No prong may land there."""
    o = OvalOutline(semi_minor=2.5, semi_major=4.0)
    for theta in o.prong_angles(n):
        for tip in (math.pi / 2, 3 * math.pi / 2):
            gap = abs(_norm(theta) - tip)
            gap = min(gap, TWO_PI - gap)
            assert gap > 1e-6, f"prong at {math.degrees(theta):.1f} sits on a tip"


def test_oval_four_prongs_are_the_conventional_quarters():
    """The 10-2-4-8 oval layout: tips fall midway between adjacent claws."""
    angles = sorted(_norm(a) for a in OvalOutline(2.5, 4.0).prong_angles(4))
    assert angles == pytest.approx([math.radians(d) for d in (45, 135, 225, 315)])


def test_oval_six_prongs_clear_the_tips_by_thirty_degrees():
    angles = sorted(_norm(a) for a in OvalOutline(2.5, 4.0).prong_angles(6))
    assert angles == pytest.approx(
        [math.radians(d) for d in (0, 60, 120, 180, 240, 300)]
    )


def test_prong_count_is_respected():
    assert len(OvalOutline(2.5, 4.0).prong_angles(6)) == 6


# --- frames (a claw needs to know which way to lean) -----------------------

def test_round_frame_normal_is_radial():
    o = RoundOutline(3.0)
    point, normal = o.frame_at(0.0)
    assert (point.X, point.Y) == pytest.approx((3.0, 0.0))
    assert (normal.X, normal.Y) == pytest.approx((1.0, 0.0))


def test_oval_frame_normal_is_not_merely_radial():
    """On an ellipse the outward normal is NOT the radial direction except on
    the axes -- a claw that leaned radially would not sit square on the girdle."""
    o = OvalOutline(semi_minor=2.0, semi_major=4.0)
    theta = math.pi / 4
    point, normal = o.frame_at(theta)
    radial = point.normalized()
    assert normal.length == pytest.approx(1.0)
    assert abs(normal.X - radial.X) > 1e-3 or abs(normal.Y - radial.Y) > 1e-3


def test_oval_frame_on_the_axes_is_axis_aligned():
    o = OvalOutline(semi_minor=2.0, semi_major=4.0)
    point, normal = o.frame_at(0.0)
    assert (point.X, point.Y) == pytest.approx((2.0, 0.0))
    assert (normal.X, normal.Y) == pytest.approx((1.0, 0.0))
    point, normal = o.frame_at(math.pi / 2)
    assert (point.X, point.Y) == pytest.approx((0.0, 4.0))
    assert (normal.X, normal.Y) == pytest.approx((0.0, 1.0))


# --- castability input -----------------------------------------------------

def test_round_min_curvature_radius_is_the_radius():
    assert RoundOutline(3.0).min_curvature_radius() == pytest.approx(3.0)


def test_oval_tightest_curvature_is_at_the_tip():
    """For semi-axes p (minor) and q (major) the tightest bend is at the end of
    the major axis, radius p^2/q. This is the number the casting floors must be
    checked against, and it is what makes a too-elongated stone fail loudly."""
    o = OvalOutline(semi_minor=2.0, semi_major=4.0)
    assert o.min_curvature_radius() == pytest.approx(1.0)


def test_more_elongated_means_tighter_curvature():
    mild = OvalOutline(semi_minor=3.0, semi_major=3.6)
    sharp = OvalOutline(semi_minor=3.0, semi_major=6.0)
    assert sharp.min_curvature_radius() < mild.min_curvature_radius()


# --- the path the curve-walkers sweep along --------------------------------

def test_wire_is_a_closed_path_of_the_right_size():
    """The girdle path is what seat / bezel / halo sweep along.

    Tolerance note: the oval wire is a true GeomType.ELLIPSE, but OCCT's
    curve-length integration reports it ~0.13% high against the exact elliptic
    integral (19.4023 vs 19.3769 for semi-axes 2x4). That is kernel integration
    tolerance, not a modelling error, and 0.13% of a girdle is far below both the
    0.05mm fuse epsilon and any casting tolerance -- so it is accepted here
    rather than worked around. Relevant to CP3, which spaces halo accents by arc
    length along this wire.
    """
    from build123d import Wire

    for outline, expected in (
        (RoundOutline(3.0), TWO_PI * 3.0),
        (OvalOutline(2.0, 4.0), 19.3769),  # exact, via 4a*E(m)
    ):
        wire = outline.wire()
        assert isinstance(wire, Wire)
        assert wire.length == pytest.approx(expected, rel=2e-3)
