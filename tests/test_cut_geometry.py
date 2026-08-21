"""Each new cut composes into castable metal (RNG-33 CP2).

The RNG-17 bar, applied to cushion, emerald, pear and marquise: the RAW solid --
before `validate_and_repair` ever runs -- must be a single watertight manifold
with zero non-manifold edges.

**Watertightness alone is not the assertion, and never should be here.** Three
separate ADRs exist because a wrong solid reports watertight:

  * docs/adr/0005 -- a fuse that silently DROPS a body still reports watertight,
    zero non-manifold edges, and passes every casting floor, because the
    offending metal is gone. Assert VOLUME.
  * docs/adr/0008 -- a bore that fails to OPEN becomes a sealed void that still
    reports watertight and single-solid. Assert BODY COUNT.
  * docs/adr/0007 -- a perfectly valid B-rep can still tessellate into a cracked
    mesh, which is why this runs on exported STL rather than on the B-rep.

These are slow (B-rep + tessellation per case), so the parameter sweep is
deliberately coarse: the corners of the space, not a grid.
"""
from __future__ import annotations

import pytest

from ringcad.geometry.module import compose
from ringcad.ringspec import validate_spec
from ringcad.ringspec.castability import validate_castability
from ringcad.ringspec.cuts import profile_for

NEW_CUTS = ("cushion", "emerald", "pear", "marquise")


def _spec(shape, ratio=None, stone=6.5, prongs=4, archetype="solitaire",
          **groups):
    p = profile_for(shape)
    body = {
        "archetype": archetype,
        "shank": {"inner_diameter": 17.0, "band_width": 2.5,
                  "band_thickness": 1.8},
        "setting": {"prong_count": prongs, "setting_height": 5.0},
        "stones": {"stone_diameter": stone, "stone_height": 4.0,
                   "shape": shape,
                   "length_ratio": p.default_ratio if ratio is None else ratio},
        "motifs": [],
    }
    body.update(groups)
    return validate_spec(body)


# --- the RNG-17 bar, per cut ------------------------------------------------

@pytest.mark.parametrize("shape", NEW_CUTS)
def test_each_cut_is_a_single_raw_watertight_manifold(shape, raw_validate):
    result = raw_validate(compose(_spec(shape)))
    assert result.is_watertight
    assert result.non_manifold_edges == 0
    assert result.body_count == 1


@pytest.mark.parametrize("shape", NEW_CUTS)
def test_each_cut_has_real_volume(shape):
    """docs/adr/0005: the seat could be dropped entirely by a silent boolean
    failure and everything above would still pass. Compare against the shank
    alone, which is what a ring with no setting left on it would weigh."""
    from ringcad.geometry.shank import shank
    spec = _spec(shape)
    assert compose(spec).volume > shank(spec).volume


@pytest.mark.parametrize("shape", NEW_CUTS)
@pytest.mark.parametrize("prongs", [4, 6])
def test_each_cut_builds_at_both_prong_counts(shape, prongs, raw_validate):
    result = raw_validate(compose(_spec(shape, prongs=prongs)))
    assert result.is_watertight
    assert result.body_count == 1


@pytest.mark.parametrize("shape", NEW_CUTS)
def test_each_cut_builds_at_both_ends_of_its_own_ratio_band(
        shape, raw_validate):
    """A cut's band is its own, not a shared 1.0-2.5: marquise never goes below
    1.5 and cushion never above 1.30, so sweeping a shared range would test
    stones that cut does not have."""
    p = profile_for(shape)
    for ratio in (p.min_ratio, p.max_ratio):
        result = raw_validate(compose(_spec(shape, ratio=ratio)))
        assert result.is_watertight, f"{shape} at ratio {ratio}"
        assert result.body_count == 1, f"{shape} at ratio {ratio}"


@pytest.mark.parametrize("shape", NEW_CUTS)
def test_each_cut_builds_at_the_small_end_of_the_stone_range(
        shape, raw_validate):
    """Small stones are where the seat bore comes closest to inverting, so this
    is the end of the range worth sweeping."""
    spec = _spec(shape, stone=2.5)
    assert not [v for v in validate_castability(spec)
                if v.code == "stone_curvature"]
    result = raw_validate(compose(spec))
    assert result.is_watertight
    assert result.body_count == 1


# --- the seat is genuinely open, not a filled slab -------------------------

@pytest.mark.parametrize("shape", NEW_CUTS)
def test_the_bore_removes_metal_rather_than_leaving_a_lid(shape):
    """A seat whose bore failed to break through is a sealed cavity: single
    solid, watertight, all floors met, and heavier than it should be. Compare
    the seat against the un-bored plate it was cut from."""
    from build123d import Face, extrude

    from ringcad.geometry._common import clamps
    o = clamps(_spec(shape))["outline"]
    r = 0.45
    seat = o.seat_solid(r)
    plate = extrude(Face(o.expanded(r).wire()), amount=2 * r)
    assert seat.volume < plate.volume * 0.75, (
        f"{shape} seat is barely lighter than the solid plate -- the bore "
        "may not have opened")


# --- round and oval are untouched ------------------------------------------

@pytest.mark.parametrize("shape,ratio", [("round", 1.0), ("oval", 1.5)])
def test_the_existing_shapes_still_compose(shape, ratio, raw_validate):
    """`seat()` now asks the outline for a finished solid instead of a tube.
    For round and oval that returns the same `Torus` and swept ellipse as
    before, so nothing about them may move."""
    result = raw_validate(compose(_spec(shape, ratio=ratio)))
    assert result.is_watertight
    assert result.non_manifold_edges == 0
    assert result.body_count == 1


# --- compose's subtraction must be checked, not trusted ---------------------

def test_a_long_centre_stone_on_a_side_stone_band_survives_the_channel_cut():
    """The n-ary `cut(*tools)` fails silently on this combination.

    Measured before the fix: a marquise centre went from a 376.95mm3 single
    solid to 9.25mm3 in 8 pieces -- the tools removed 98% of the ring -- and the
    casting gate called the spec castable throughout. Cutting iteratively
    returned a correct single solid, so `compose` now checks the result and
    falls back rather than trusting the boolean (docs/adr/0005).

    NOT a defect of the new cuts: `oval` at length_ratio 2.5 fails the same way
    on the pre-RNG-33 tree. The new cuts only made it reachable at a default.
    """
    spec = _spec("marquise", archetype="side_stone",
                 shank={"inner_diameter": 17.0, "band_width": 4.0,
                        "band_thickness": 1.8},
                 side_stone={"accent_count_per_side": 5,
                             "accent_stone_diameter": 1.4,
                             "accent_stone_height": 1.2,
                             "accent_gap": 0.3, "retention": "channel"})
    solid = compose(spec)
    assert len(solid.solids()) == 1
    # The channel groove removes a little metal; it must not remove the ring.
    assert solid.volume > 300, "the channel cut ate the ring"


def test_the_halo_case_that_forced_the_n_ary_cut_still_works():
    """RNG-19 moved to a single n-ary cut because iterating raised
    `Null TopoDS_Shape` on a 13-accent halo. The fallback must not regress it:
    n-ary stays the primary path and is kept whenever it yields one solid."""
    for count in (13, 22):
        spec = _spec("round", ratio=1.0, archetype="halo",
                     halo={"halo_stone_count": count,
                           "halo_stone_diameter": 1.3,
                           "halo_stone_height": 1.2, "halo_gap": 0.5})
        assert len(compose(spec).solids()) == 1, f"{count} accents"
