"""CutProfile — the cut's own facts, kernel-free (RNG-33 CP1).

`ringcad/ringspec/cuts.py` is where a cut's proportions, outline math and prong
layout live. It imports no `build123d`, so BOTH the castability gate and the
geometry outline can read the same numbers instead of each deriving its own --
which is exactly the drift ADR-0002 warns about and which RNG-23 left in place
(`castability._stone_curvature` re-derives `semi_minor / ratio` while
`outline.min_curvature_radius()` has no production caller at all).

Round and oval must come out of this layer with their pre-RNG-33 values EXACTLY,
or the parity and golden suites move for shapes this ticket never touched.
"""
from __future__ import annotations

import math

import pytest

from ringcad.ringspec.cuts import (
    CUT_NAMES, ProngType, profile_for,
)


# --- the registry -----------------------------------------------------------

def test_every_supported_cut_has_a_profile():
    assert set(CUT_NAMES) == {
        "round", "oval", "cushion", "emerald", "pear", "marquise",
    }
    for name in CUT_NAMES:
        assert profile_for(name).name == name


def test_unknown_cut_is_rejected_by_name():
    with pytest.raises(ValueError, match="princess"):
        profile_for("princess")


# --- per-cut proportions ----------------------------------------------------

@pytest.mark.parametrize("name,expected", [
    ("round", 1.0),
    ("oval", 1.4),
    ("cushion", 1.02),
    ("emerald", 1.40),
    ("pear", 1.60),
    ("marquise", 1.95),
])
def test_each_cut_declares_its_conventional_default_ratio(name, expected):
    """A single shared default makes three of four new cuts wrong on sight."""
    assert profile_for(name).default_ratio == pytest.approx(expected)


def test_round_is_the_only_cut_that_cannot_elongate():
    assert profile_for("round").max_ratio == 1.0
    for name in ("oval", "cushion", "emerald", "pear", "marquise"):
        assert profile_for(name).max_ratio > 1.0


def test_each_cuts_default_ratio_lies_inside_its_own_band():
    for name in CUT_NAMES:
        p = profile_for(name)
        assert p.min_ratio <= p.default_ratio <= p.max_ratio


# --- round and oval must not move -------------------------------------------

def test_round_half_width_is_the_radius_on_both_axes():
    p = profile_for("round")
    assert p.half_width(3.25, 1.0, "x") == pytest.approx(3.25)
    assert p.half_width(3.25, 1.0, "y") == pytest.approx(3.25)


def test_oval_half_width_is_semi_minor_across_and_semi_major_along():
    p = profile_for("oval")
    assert p.half_width(2.0, 1.5, "x") == pytest.approx(2.0)
    assert p.half_width(2.0, 1.5, "y") == pytest.approx(3.0)


def test_round_perimeter_is_exactly_the_circle():
    p = profile_for("round")
    assert p.perimeter(3.25, 1.0) == pytest.approx(2 * math.pi * 3.25)


def test_oval_min_curvature_radius_is_the_rng23_formula():
    """`semi_minor^2 / semi_major`, the value castability.py re-derives today."""
    p = profile_for("oval")
    assert p.min_curvature_radius(2.0, 1.5) == pytest.approx(2.0 ** 2 / 3.0)


def test_round_prong_layout_is_the_pre_rng33_even_spacing():
    p = profile_for("round")
    for n in (4, 6):
        angles = [theta for theta, _ in p.prong_layout(n)]
        assert angles == pytest.approx([k * 2 * math.pi / n for k in range(n)])


def test_round_and_oval_prongs_are_never_v_prongs():
    """A V-prong is for a point or a corner; a smooth girdle has neither."""
    for name in ("round", "oval"):
        for n in (4, 6):
            types = {t for _, t in profile_for(name).prong_layout(n)}
            assert ProngType.V not in types


# --- marquise: the two-arc construction -------------------------------------

def test_marquise_arc_radius_follows_the_two_arc_construction():
    """R = (a^2 + b^2) / (2b) for half-length a, half-width b."""
    p = profile_for("marquise")
    b, ratio = 2.0, 2.0
    a = b * ratio
    assert p.arc_radius(b, ratio) == pytest.approx((a * a + b * b) / (2 * b))


def test_marquise_tip_is_a_finite_wedge_not_a_spike():
    p = profile_for("marquise")
    assert p.tip_wedge_angle(2.0) == pytest.approx(math.radians(106), abs=0.02)


def test_marquise_tip_wedge_is_exactly_120_degrees_at_the_vesica_ratio():
    """The vesica piscis is L:W = sqrt(3); its lens tip is exactly 120 degrees.

    A pure math fact, and the one independent check on the whole construction.
    """
    p = profile_for("marquise")
    assert p.tip_wedge_angle(math.sqrt(3)) == pytest.approx(
        math.radians(120), abs=1e-9)


# --- which cuts have vertices ----------------------------------------------

@pytest.mark.parametrize("name,expected", [
    ("round", False),
    ("oval", False),
    ("cushion", False),
    ("emerald", True),
    ("pear", True),
    ("marquise", True),
])
def test_cuts_declare_whether_their_girdle_has_vertices(name, expected):
    """A vertex cannot be swept along by a collar tube at ANY radius, which is
    why CP2 bores those seats instead. The gate must ask, not guess."""
    assert profile_for(name).has_vertices is expected


def test_a_visible_tip_radius_is_never_modelled_on_a_pointed_cut():
    """GIA grades a rounded point ("undefined points") as a DEFECT -- real
    stones protect the point with a thicker girdle, not by blunting it."""
    for name in ("pear", "marquise"):
        assert profile_for(name).tip_radius == 0.0


# --- prong layout per cut ---------------------------------------------------

def test_emerald_prongs_grip_the_corners_not_the_flat_sides():
    """Compass placement leaves the cut corners -- the likeliest impact site --
    unprotected, and a prong on a flat side has nothing to hook."""
    p = profile_for("emerald")
    angles = sorted(theta % (2 * math.pi) for theta, _ in p.prong_layout(4))
    corners = sorted(c % (2 * math.pi) for c in p.corner_angles(1.40))
    assert angles == pytest.approx(corners)


def test_cushion_prongs_also_grip_the_corners():
    p = profile_for("cushion")
    angles = sorted(theta % (2 * math.pi) for theta, _ in p.prong_layout(4))
    corners = sorted(c % (2 * math.pi) for c in p.corner_angles(1.02))
    assert angles == pytest.approx(corners)


@pytest.mark.parametrize("n", [4, 6])
def test_pear_has_exactly_one_v_prong_and_it_sits_on_the_point(n):
    p = profile_for("pear")
    layout = p.prong_layout(n)
    vs = [theta for theta, t in layout if t is ProngType.V]
    assert len(vs) == 1
    assert vs[0] == pytest.approx(p.point_angle)


@pytest.mark.parametrize("n", [4, 6])
def test_marquise_has_a_v_prong_on_each_of_its_two_points(n):
    p = profile_for("marquise")
    vs = [theta for theta, t in p.prong_layout(n) if t is ProngType.V]
    assert len(vs) == 2
    assert sorted(v % (2 * math.pi) for v in vs) == pytest.approx(
        sorted(a % (2 * math.pi) for a in p.point_angles))


@pytest.mark.parametrize("name", CUT_NAMES)
@pytest.mark.parametrize("n", [4, 6])
def test_every_prong_layout_is_distinct_and_in_range(name, n):
    layout = profile_for(name).prong_layout(n)
    angles = [theta % (2 * math.pi) for theta, _ in layout]
    assert len(angles) == len(layout)
    assert len({round(a, 9) for a in angles}) == len(angles)


# --- the gate's question ----------------------------------------------------

def test_an_elongated_cut_has_more_girdle_than_the_circle_of_its_short_axis():
    """`castability._min_prong_tip` divides a CIRCLE's perimeter by the prong
    count, so on an elongated cut it under-reports the arc each prong gets and
    rejects specs the geometry can build -- the `_halo_overcrowding` bug of
    ADR-0006, in a second gate."""
    circle = 2 * math.pi * 2.0
    for name in ("oval", "emerald", "pear", "marquise"):
        p = profile_for(name)
        assert p.perimeter(2.0, p.default_ratio) > circle


# --- symmetry: the invariant that catches a scrambled parametrisation --------

@pytest.mark.parametrize("name", CUT_NAMES)
def test_every_girdle_is_symmetric_about_the_long_axis(name):
    """Every supported cut is mirror-symmetric across local X.

    Cheap to assert and it pins something structural: `point_at`,
    `angles_by_arc` and `_place_between` all assume the polyline runs
    monotonically CCW in POLAR angle, and nothing else notices when it does
    not. A pear built traversing its head arc the wrong way round still had
    the right silhouette, the right extents and the right perimeter -- and
    scrambled every arc-length lookup taken from it.
    """
    p = profile_for(name)
    r = p.default_ratio
    for deg in range(5, 180, 5):
        t = math.radians(deg)
        x1, y1 = p.point_at(t, 2.0, r)
        x2, y2 = p.point_at(math.pi - t, 2.0, r)
        assert x1 == pytest.approx(-x2, abs=2e-2)
        assert y1 == pytest.approx(y2, abs=2e-2)


@pytest.mark.parametrize("name", CUT_NAMES)
@pytest.mark.parametrize("n", [4, 6])
def test_prong_layouts_are_symmetric_about_the_long_axis(name, n):
    """A prong on one flank must have a mirror on the other, or the stone is
    gripped unevenly. This is what caught the pear traversal bug: the layout
    put a claw 12 degrees from the V-prong and left the far flank bare."""
    layout = profile_for(name).prong_layout(n)
    angles = sorted(t % (2 * math.pi) for t, _ in layout)
    mirrored = sorted((math.pi - t) % (2 * math.pi) for t in angles)
    assert angles == pytest.approx(mirrored, abs=2e-2)
