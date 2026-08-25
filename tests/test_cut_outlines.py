"""ProfileOutline — one kernel adapter over any CutProfile (RNG-33 CP2).

RNG-23's seam promised that "a new cut is a new outline class, not an edit to six
modules". CP1 went one better: because `CutProfile` owns every shape-specific
fact, the geometry layer needs ONE adapter, not four. A new cut is a profile;
the kernel side is already written.

Two things this file pins that nothing else can:

  * **Vertices survive into the kernel.** An emerald's corners and a marquise's
    points are the whole identity of those cuts. Sampling them into a spline
    would round them off and still produce a plausible-looking, closed, watertight
    wire -- so the edge COUNT is asserted, not just the silhouette.
  * **The bore actually opens.** docs/adr/0008's trap: a bore that fails to break
    through becomes a sealed void that still reports watertight, single-solid and
    all-floors-met. Body count and volume are asserted, never watertightness alone.
"""
from __future__ import annotations

import math

import pytest

from ringcad.geometry.outline import (
    OvalOutline, ProfileOutline, RoundOutline, StoneOutline, outline_for,
)
from ringcad.ringspec.cuts import ProngType, profile_for

NEW_CUTS = ("cushion", "emerald", "pear", "marquise")


def _outline(shape, half_short=3.25, ratio=None):
    p = profile_for(shape)
    return outline_for(shape, half_short, p.default_ratio if ratio is None
                       else ratio)


# --- dispatch: round and oval must NOT be rerouted through the adapter ------

def test_round_and_oval_still_use_their_original_classes():
    """Their geometry is pinned bit-identical by the parity and golden suites,
    so they keep their literal `Torus` and swept-ellipse construction."""
    assert isinstance(outline_for("round", 3.25, 1.0), RoundOutline)
    assert isinstance(outline_for("oval", 3.25, 1.5), OvalOutline)


@pytest.mark.parametrize("shape", NEW_CUTS)
def test_every_new_cut_resolves_to_the_shared_adapter(shape):
    assert isinstance(_outline(shape), ProfileOutline)


@pytest.mark.parametrize("shape", NEW_CUTS)
def test_the_adapter_satisfies_the_stone_outline_protocol(shape):
    assert isinstance(_outline(shape), StoneOutline)


def test_a_ratio_of_one_still_collapses_to_round():
    """RNG-23's contract, unchanged: `length_ratio == 1.0` IS a circle."""
    assert isinstance(outline_for("oval", 3.25, 1.0), RoundOutline)


# --- the wire ---------------------------------------------------------------

@pytest.mark.parametrize("shape", NEW_CUTS)
def test_the_girdle_wire_is_closed(shape):
    assert _outline(shape).wire().is_closed


@pytest.mark.parametrize("shape", NEW_CUTS)
def test_the_wire_matches_the_profiles_own_extents(shape):
    p = profile_for(shape)
    r = p.default_ratio
    bb = _outline(shape).wire().bounding_box()
    assert bb.max.X == pytest.approx(3.25, abs=0.02)
    assert bb.max.Y == pytest.approx(3.25 * r, abs=0.02)


@pytest.mark.parametrize("shape,edges", [
    ("emerald", 8),      # a true octagon: four long sides, four cut corners
    ("marquise", 2),     # two circular arcs meeting at two points
    ("pear", 3),         # one head arc, two straight tangent wings
])
def test_cornered_and_pointed_cuts_keep_exact_edges_not_a_sampled_spline(
        shape, edges):
    """The vertices ARE the cut. A spline through sampled points would round
    them off and still close, still be watertight, and still look roughly
    right -- so the edge count is the assertion that actually bites."""
    assert len(_outline(shape).wire().edges()) == edges


def test_cushion_is_a_single_smooth_closed_curve():
    """A superellipse has no vertices, so it needs no exact primitive."""
    assert len(_outline("cushion").wire().edges()) >= 1


# --- expanded() -------------------------------------------------------------

@pytest.mark.parametrize("shape", NEW_CUTS)
@pytest.mark.parametrize("d", [0.5, -0.4])
def test_expanding_moves_both_extents_by_the_distance(shape, d):
    """Grows both semi-axes rather than computing a true parallel curve --
    the same approximation `OvalOutline.expanded` already makes, and for the
    same reason: the result stays a shape the kernel can sweep and face, and a
    jeweller lays a halo out the same way."""
    p = profile_for(shape)
    r = p.default_ratio
    bb = _outline(shape).expanded(d).wire().bounding_box()
    assert bb.max.X == pytest.approx(3.25 + d, abs=0.02)
    assert bb.max.Y == pytest.approx(3.25 * r + d, abs=0.02)


@pytest.mark.parametrize("shape", NEW_CUTS)
def test_an_expanded_outline_is_still_the_same_kind_of_shape(shape):
    """The halo plate faces `expanded()` at two different distances and needs
    both to be the same construction, or the plate and its bore disagree."""
    grown = _outline(shape).expanded(0.6)
    assert isinstance(grown, ProfileOutline)
    assert grown.profile.name == shape


# --- frames -----------------------------------------------------------------

@pytest.mark.parametrize("shape", NEW_CUTS)
def test_the_normal_points_outward_everywhere(shape):
    o = _outline(shape)
    for deg in range(0, 360, 11):
        point, normal = o.frame_at(math.radians(deg))
        assert normal.length == pytest.approx(1.0, abs=1e-6)
        # Outward: stepping along the normal must increase the distance from
        # the centre for any star-shaped girdle.
        here = math.hypot(point.X, point.Y)
        out = math.hypot(point.X + normal.X * 1e-3, point.Y + normal.Y * 1e-3)
        assert out > here


@pytest.mark.parametrize("shape", NEW_CUTS)
def test_frame_at_lands_on_the_requested_polar_angle(shape):
    o = _outline(shape)
    for deg in (7, 61, 143, 209, 300):
        point, _ = o.frame_at(math.radians(deg))
        assert math.degrees(math.atan2(point.Y, point.X)) % 360 == \
            pytest.approx(deg, abs=1.0)


# --- placements (the interface prong_setting will consume in CP3) ----------

@pytest.mark.parametrize("shape", NEW_CUTS)
@pytest.mark.parametrize("n", [4, 6])
def test_placements_carry_a_prong_type_alongside_the_angle(shape, n):
    for theta, kind in _outline(shape).placements(n):
        assert isinstance(theta, float)
        assert isinstance(kind, ProngType)


@pytest.mark.parametrize("shape,expected_v", [
    ("cushion", 0), ("emerald", 0), ("pear", 1), ("marquise", 2)])
def test_v_prongs_land_only_where_there_is_a_vertex_to_wrap(shape, expected_v):
    """V is the prong that wraps a POINT -- somewhere a claw has no width to
    sit on.

    Emerald expected 4 here until 2026-08-25, on CP1's reasoning that a cut
    corner is a vertex and V wraps vertices. A vertex is necessary but not
    sufficient: an emerald's corner is a short FLAT facet, wide enough for one
    claw, and `docs/reference/emerald.png` draws exactly that -- "4 PRONG
    SOLITAIRE SETTING", one rounded claw per corner. A pear's point has no
    width to sit on, which is why it needs metal from both sides. The research
    note is explicit that no source ever named emerald corners; the V there was
    an inference.

    Note `has_vertices` is UNCHANGED for emerald -- its corners really are
    vertices, which is why its seat is bored rather than swept and why
    `_stone_curvature` declines to judge it. Only the prong type moved.
    """
    got = [t for _, t in _outline(shape).placements(4) if t is ProngType.V]
    assert len(got) == expected_v


def test_round_and_oval_placements_are_the_pre_rng33_angles():
    """`placements` replaces `prong_angles` for every outline, so the old
    shapes must come through it unchanged."""
    assert [t for t, _ in RoundOutline(3.25).placements(4)] == pytest.approx(
        [k * math.pi / 2 for k in range(4)])
    tip = math.pi / 2
    assert [t for t, _ in OvalOutline(2.0, 3.0).placements(4)] == \
        pytest.approx([tip + (k + 0.5) * math.pi / 2 for k in range(4)])


# --- the seat: built by the outline, bored not swept ------------------------

@pytest.mark.parametrize("shape", NEW_CUTS)
def test_the_seat_is_one_solid_with_real_volume(shape):
    """docs/adr/0005 + 0008: a dropped body and a sealed void BOTH report
    watertight. Volume and body count are what actually distinguish them."""
    solid = _outline(shape).seat_solid(0.45)
    assert len(solid.solids()) == 1
    assert solid.volume > 0


@pytest.mark.parametrize("shape", NEW_CUTS)
def test_the_seat_is_open_through_the_middle(shape):
    """The bore must BREAK THROUGH, not leave a lid. A sealed seat has the
    volume of the whole plate; an open one is a rim of known thickness."""
    p = profile_for(shape)
    o = _outline(shape)
    solid = o.seat_solid(0.45)
    plate = o.expanded(0.45).wire()
    bb = plate.bounding_box()
    # A solid slab of the same footprint would be far heavier than the rim.
    slab = bb.size.X * bb.size.Y * 0.9
    assert solid.volume < slab, f"{p.name} seat reads as a sealed slab"


def test_round_and_oval_seats_still_come_from_the_swept_collar():
    """Unchanged construction for the shapes the parity suite pins."""
    for o in (RoundOutline(3.25), OvalOutline(2.0, 3.0)):
        solid = o.seat_solid(0.45)
        assert len(solid.solids()) == 1
        assert solid.volume > 0


@pytest.mark.parametrize("shape", NEW_CUTS)
def test_a_stone_narrower_than_its_collar_is_refused_not_built(shape):
    """Below `half_short <= minor_r` the inner bore INVERTS.

    Pear and marquise raise out of OCCT, but cushion and emerald quietly
    returned a plausible single solid of positive volume with no opening --
    wrong metal, no error, every structural assertion still green. Found by
    sweeping the small end of the parameter space by hand, not by any test.
    """
    o = outline_for(shape, 0.45, profile_for(shape).default_ratio)
    with pytest.raises(ValueError, match="seat collar"):
        o.seat_solid(0.45)


@pytest.mark.parametrize("shape", NEW_CUTS)
def test_the_smallest_buildable_seat_still_opens(shape):
    """Just above the guard the seat must be a real rim, not a slab.

    The size is DERIVED from the guard rather than written out, because the
    guard sits at `minor_r + GIRDLE_EMBED` and that constant moves: RNG-33 CP3
    raised it from 0.06 to 0.15 to keep a marquise's tip out of the grazing
    band, which silently invalidated a hardcoded 0.55 that had been "just
    above" a 0.51 guard.
    """
    from ringcad.geometry.outline import GIRDLE_EMBED

    o = outline_for(shape, 0.45 + GIRDLE_EMBED + 0.04,
                    profile_for(shape).default_ratio)
    solid = o.seat_solid(0.45)
    assert len(solid.solids()) == 1
    assert solid.volume > 0


def test_the_seat_wall_clears_anything_sitting_on_the_girdle():
    """The bored seat's outer wall must fully contain the claw node that sits
    ON the girdle, not graze it.

    Pinning the CAUSE rather than the symptom. `prong_setting` builds each
    claw's girdle node as a sphere centred exactly on the girdle; if that
    sphere reaches past the seat's flat extruded outer wall, OCCT resolves the
    graze as a zero-volume lamina -- measured at 323 faces and 183 non-manifold
    edges, reported as a second mesh body, off a B-rep that was a single valid
    solid (docs/adr/0007). A swept torus never showed it, so this only became
    reachable when the seat started being bored.

    If either radius is ever retuned, this fails before the geometry does.
    """
    from ringcad.geometry._common import MIN_WALL
    from ringcad.geometry.outline import GIRDLE_EMBED

    collar = max(MIN_WALL / 2, 0.45)
    claw_girdle_sphere = max(MIN_WALL / 2 + 0.1, 0.5) * 0.92
    assert collar + GIRDLE_EMBED > claw_girdle_sphere, (
        "the seat's outer wall no longer contains the claw's girdle node"
    )
