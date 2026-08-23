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

  * a V is strictly MORE metal than the claw it replaces (measured against the
    same ring built with the fork suppressed -- no threshold pulled from the
    output);
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
from build123d import Box, Plane, Pos

from ringcad.geometry import prong_setting
from ringcad.geometry._common import HEAD_INSET, clamps
from ringcad.geometry.prong_setting import TIP_LEAN, _along_girdle
from ringcad.mesh_validator import MIN_PRONG_TIP_MM
from ringcad.ringspec import validate_spec
from ringcad.ringspec.cuts import ProngType, profile_for

NEW_CUTS = ("cushion", "emerald", "pear", "marquise")
VERTEX_CUTS = ("emerald", "pear", "marquise")   # the cuts that get any V at all

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
def test_a_v_prong_is_more_metal_than_the_claw_it_replaces(shape, prongs):
    """Built against the same ring with the fork suppressed, so the bar is
    'strictly more', not a number read off the output."""
    spec = _spec(shape, prongs=prongs)
    c = clamps(spec)
    forked = prong_setting(spec, c)
    plain = prong_setting(spec, dict(c, outline=_ForcedClaws(c["outline"])))
    assert len(forked.solids()) == 1 and len(plain.solids()) == 1
    assert forked.volume > plain.volume


@pytest.mark.parametrize("shape", ["cushion", "round", "oval"])
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
def test_the_arms_are_laid_along_the_girdle_not_across_the_bisector(shape):
    """The arm ends must sit ON the stone's own outline.

    A V built by rotating the vertex normal through a wrap angle is right on an
    emerald, whose runs are straight, and wrong on a pear or a marquise, whose
    runs are ARCS -- the arms would lift away from the girdle the further out
    they reached. Walking the outline is what makes the wrap angle a
    consequence of the cut rather than a guess (specs/RNG-33.md).
    """
    c = clamps(_spec(shape))
    outline = c["outline"]
    for theta, kind in outline.placements(int(c["prong_n"])):
        if kind is not ProngType.V:
            continue
        vertex, _ = outline.frame_at(theta)
        for sign in (1, -1):
            end, _ = outline.frame_at(_along_girdle(outline, theta, 1.2, sign))
            assert math.dist((end.X, end.Y), (vertex.X, vertex.Y)) == \
                pytest.approx(1.2, abs=0.05)


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
