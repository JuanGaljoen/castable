"""RNG-33 CP3 — the outline chooses the prong, and a vertex gets a V.

CP1 gave every cut a `prong_layout`, CP2 exposed it as `placements()`, and
`prong_setting` still ignored both: it read the angle-only view and built the
round-stone claw at every position. A pear's point and an emerald's cut corners
were therefore held by a single claw sitting ON the vertex -- the arrangement
Stuller names as the failure mode outright ("cushions with rounded corners can
easily rotate and fall out of a prong setting").

**What a V is, and what it is not.** A V-prong lays one arm back along each of
the two girdle runs that meet at the vertex. On an obtuse corner (emerald) the
two arms stay separate all the way to their tips; on a sharp point (pear,
marquise) they converge and merge into one piece of metal -- which is what a
V-prong at a point physically IS. So counting tips is NOT the invariant, and a
first draft of this file that counted them was measuring the wedge angle rather
than the fork. The invariants that hold for both are:

  * a V builds something other than the claw it replaces (measured against the
    same ring with the fork suppressed);
  * the cup FOLLOWS THE GIRDLE either side of the point and leaves the stone's
    own space empty -- a solid lump over the point would pass every other test
    here and leave nowhere for the stone to sit;
  * the metal a fork ADDS lands on both sides of the vertex bisector, in equal
    amounts -- weighed by boolean against the same ring built with the fork
    suppressed;
  * mirror-image placements produce mirror-image metal.

That last one is not decoration. The first working fork was built as a fan of
cones off one node, and OCCT's n-ary fuse silently DROPPED a whole arm from ONE
of a marquise's two V-prongs -- 4.866mm3 against its twin's 6.524, single-solid,
watertight, no warning (docs/adr/0005, third sighting). Asymmetric metal on a
symmetric stone was the only signal, and nothing else in the suite looks for it.

Sectioning follows `tests/test_prong_finishing.py`: `placement()` lays the local
+Z setting frame onto the global +X head axis, so local height `z` is the plane
`x = head_r - HEAD_INSET + z`, and local (x, y) reads off the section as
(-global Z, global Y).
"""
from __future__ import annotations

import math

import pytest
from build123d import Box, Plane, Pos, Sphere

from ringcad.geometry import prong_setting
from ringcad.geometry._common import HEAD_INSET, clamps
from ringcad.geometry.prong_setting import TIP_LEAN
from ringcad.mesh_validator import MIN_PRONG_TIP_MM
from ringcad.geometry.module import compose
from ringcad.ringspec import validate_spec
from ringcad.ringspec.cuts import ProngType, profile_for

NEW_CUTS = ("cushion", "emerald", "pear", "marquise")
VERTEX_CUTS = ("pear", "marquise")   # the cuts that get any V at all
# Emerald left this list on 2026-08-25: a cut corner is a flat wide enough for
# one claw, and docs/reference/emerald.png draws four single claws.

def _spec(shape, prongs=4, stone=6.5, ratio=None):
    p = profile_for(shape)
    return validate_spec({
        "archetype": "solitaire",
        "shank": {"inner_diameter": 17.0, "band_width": 2.5,
                  "band_thickness": 1.8},
        "setting": {"prong_count": prongs, "setting_height": 5.0},
        "stones": {"stone_diameter": stone, "stone_height": 4.0,
                   "shape": shape,
                   "length_ratio": p.default_ratio if ratio is None else ratio},
        "motifs": [],
    })


def _tips(solid, c, fraction=0.92):
    """The separate metal regions at claw-tip height -- above the girdle the
    only material is prong, so one face is one piece of prong."""
    z = c["ring_z"] + fraction * c["claw_rise"]
    section = solid & Plane(origin=(c["head_r"] - HEAD_INSET + z, 0, 0),
                            z_dir=(1, 0, 0))
    return section.faces()


def _has_metal(solid, c, local_xy, z) -> bool:
    """Is there metal at local (x, y, z)? Local +z is global +X."""
    probe = Pos(c["head_r"] - HEAD_INSET + z, local_xy[1], -local_xy[0]) \
        * Sphere(0.02)
    hit = solid & probe
    # An empty boolean comes back as None, not a zero-volume shape.
    return hit is not None and hit.volume > 0


class _ForcedClaws:
    """The same outline with every V demoted to a claw -- the counterfactual."""

    def __init__(self, inner):
        self._inner = inner

    def __getattr__(self, name):
        return getattr(self._inner, name)

    def placements(self, n):
        return [(t, ProngType.CLAW) for t, _ in self._inner.placements(n)]


# --- the fork exists and is metal ------------------------------------------

@pytest.mark.parametrize("shape", VERTEX_CUTS)
@pytest.mark.parametrize("prongs", [4, 6])
def test_a_v_placement_builds_something_other_than_a_claw(shape, prongs):
    """The V code path actually runs, measured against the same ring with the
    fork suppressed.

    Asserted 'strictly MORE metal' until the V became a cup. That was true of
    the two-armed fork and is not true of a cup: measured, a marquise's cup is
    +6% but a pear's is -0.5%, because a pear's point is sharp enough that the
    wall wrapping it encloses less metal than the claw tip it replaces. A V-tip
    on a sharp point genuinely IS a small piece of metal, so the old assertion
    was a property of one construction rather than of a V-prong.

    What survives is the weaker, true claim: the geometry differs. The SHAPE of
    that difference is pinned by the two tests below -- the cup follows the
    girdle without plugging the point, and the metal it adds lands on both sides
    of the bisector.
    """
    spec = _spec(shape, prongs=prongs)
    c = clamps(spec)
    forked = prong_setting(spec, c)
    plain = prong_setting(spec, dict(c, outline=_ForcedClaws(c["outline"])))
    # Not `len(solids()) == 1` for the forked build: a cup is joined to the rest
    # by the SEAT, so `prong_setting` alone legitimately comes back in pieces.
    # The test below pins that, and the composed ring is what has to be one body.
    assert len(plain.solids()) == 1
    assert forked.volume != pytest.approx(plain.volume, abs=0.01)


@pytest.mark.parametrize("shape", VERTEX_CUTS)
@pytest.mark.parametrize("prongs", [4, 6])
def test_a_v_prong_is_carried_by_the_seat_not_by_its_own_shaft(
        shape, prongs, raw_validate):
    """The cup has no shaft to the peg, and does not need one.

    It welds into the seat plate, and the plate is already carried to the peg by
    the CLAWS at the other placements -- every cut in the catalogue has at least
    one. So `prong_setting` on its own comes back in PIECES for a V cut, and the
    composed ring is nonetheless a single watertight body.

    Both halves are asserted because the second depends on the first being
    deliberate. A future all-V cut would have no claw to carry the seat and
    would ship in pieces; this is what makes that fail loudly here rather than
    quietly downstream.
    """
    spec = _spec(shape, prongs=prongs)
    c = clamps(spec)
    assert len(prong_setting(spec, c).solids()) > 1, (
        "the cup is expected to be a separate solid until the seat joins it"
    )
    assert any(k is ProngType.CLAW
               for _, k in c["outline"].placements(prongs)), (
        f"{shape} at {prongs} prongs has no claw to carry the seat"
    )
    mesh = raw_validate(compose(spec))
    assert mesh.body_count == 1 and mesh.is_watertight


@pytest.mark.parametrize("shape", ["cushion", "emerald", "round", "oval"])
def test_a_cut_with_no_vertex_to_wrap_gets_no_fork(shape):
    """The control. A cushion's corners are ROUNDED, so it takes claws -- the
    distinction is geometric, not stylistic, which is what makes `ProngType`
    reusable for princess and trillion later."""
    spec = _spec(shape, ratio=1.5 if shape == "oval" else None)
    c = clamps(spec)
    assert all(k is not ProngType.V
               for _, k in c["outline"].placements(int(c["prong_n"])))
    assert len(_tips(prong_setting(spec, c), c)) == int(c["prong_n"])


# --- the fork straddles the vertex -----------------------------------------

@pytest.mark.parametrize("shape", ["pear", "marquise"])
@pytest.mark.parametrize("prongs", [4, 6])
def test_the_metal_a_fork_adds_lands_on_both_sides_of_the_point(shape, prongs):
    """Cut the forked setting against the claws-only one and weigh what is
    left, either side of the long axis.

    Measured on the B-rep by boolean, not by counting faces in a section: on a
    sharp point the two arms MERGE into one piece of metal (which is what a
    V-prong at a point is), so face topology cannot tell a fork from a fat
    claw. Volume either side of the bisector can, and it is exact.

    Pear and marquise put every V on the long axis, so one plane -- local
    x = 0 -- is the bisector for all of them at once. Emerald's four corners
    have four different bisectors; its fork is covered by the mirror-symmetry
    and follows-the-girdle tests below.
    """
    spec = _spec(shape, prongs=prongs)
    c = clamps(spec)
    added = prong_setting(spec, c).cut(
        prong_setting(spec, dict(c, outline=_ForcedClaws(c["outline"]))))
    assert added is not None and added.volume > 0, "the fork added no metal"
    # Local +x is global -Z, so a half-space in local x is one in global Z.
    reach = 4 * c["stone_r"]
    halves = []
    for sign in (1, -1):
        box = Pos(c["head_r"] - HEAD_INSET, 0, -sign * reach) * Box(
            4 * reach, 4 * reach, 2 * reach)
        piece = added & box
        halves.append(0.0 if piece is None else piece.volume)
    assert min(halves) > 0, f"{shape}: the fork is one-sided {halves}"
    assert halves[0] == pytest.approx(halves[1], rel=1e-3), \
        f"{shape}: the fork is lopsided {halves}"


@pytest.mark.parametrize("shape", VERTEX_CUTS)
def test_the_cup_follows_the_girdle_rather_than_plugging_across_the_point(shape):
    """The cup's inner face IS the stone's outline, so the point beds into it.

    This is what separates a cup from a blob: metal must sit ON the girdle
    either side of the vertex, and must NOT fill the space the stone occupies.
    A solid lump over the point would satisfy every other test in this file --
    more metal than a claw, symmetric, both sides of the bisector -- and would
    leave nowhere for the stone to go.

    Replaced a test that asserted `_along_girdle` returned a point 1.2mm from
    the vertex. That exercised a helper rather than the geometry, and the helper
    went with the fork construction it was written for.
    """
    spec = _spec(shape, prongs=6)
    c = clamps(spec)
    outline = c["outline"]
    solid = prong_setting(spec, c)
    z = c["ring_z"] + 0.3 * c["claw_rise"]      # inside the cup's own height

    for theta, kind in outline.placements(int(c["prong_n"])):
        if kind is not ProngType.V:
            continue
        for delta in (0.0, 0.08, -0.08):
            point, _ = outline.frame_at(theta + delta)
            assert _has_metal(solid, c, (point.X, point.Y), z), (
                f"{shape}: no metal on the girdle {delta:+.2f}rad from the "
                "point -- the cup does not follow the outline there"
            )
        # Well inside the stone: the cup must leave that space empty.
        inside, _ = outline.frame_at(theta)
        assert not _has_metal(solid, c, (inside.X * 0.55, inside.Y * 0.55), z), (
            f"{shape}: metal where the stone sits -- that is a plug, not a cup"
        )


# --- symmetry: the assertion that caught the silent body drop --------------

@pytest.mark.parametrize("shape", NEW_CUTS)
@pytest.mark.parametrize("prongs", [4, 6])
def test_mirror_image_placements_produce_mirror_image_metal(shape, prongs):
    """Every cut here is symmetric about its long axis, so the metal must be
    too. A fan-of-cones fork passed everything else in this file while quietly
    losing one arm of one V-prong; this is what saw it."""
    spec = _spec(shape, prongs=prongs)
    c = clamps(spec)
    faces = _tips(prong_setting(spec, c), c)
    # Local x is across the long axis: pair each face with its mirror.
    seen = sorted((round(-f.center().Z, 3), round(f.center().Y, 3),
                   round(float(f.area), 3)) for f in faces)
    mirrored = sorted((-x, y, a) for x, y, a in seen)
    assert seen == pytest.approx(mirrored, abs=1e-3)


# --- the casting floor still holds, per TIP not per prong ------------------

@pytest.mark.parametrize("shape", NEW_CUTS)
def test_every_tip_including_the_v_arms_clears_the_prong_floor(shape):
    """A fork adds tips; each one is still a prong tip and each one still has
    to be castable."""
    spec = _spec(shape)
    c = clamps(spec)
    floor = math.pi * (MIN_PRONG_TIP_MM / 2) ** 2
    areas = [float(f.area) for f in _tips(prong_setting(spec, c), c, 0.5)]
    assert min(areas) >= floor, f"{shape}: thinnest tip {min(areas):.4f}mm2"


# --- the interface actually replaced the old one ---------------------------

@pytest.mark.parametrize("shape", ["round", "oval", "marquise"])
def test_prong_angles_is_gone_from_the_outline_interface(shape):
    """`placements` REPLACES `prong_angles`. Leaving the angle-only view behind
    would leave a method with no production caller -- precisely how
    `min_curvature_radius` drifted out of step with the gate that re-derived it
    by hand (docs/adr/0002)."""
    assert not hasattr(clamps(_spec(shape))["outline"], "prong_angles")
