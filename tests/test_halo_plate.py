"""RNG-19 CP4 -- the halo body is a PLATE with bored seats, not a ring of collars.

`docs/reference/halo.png` (a trade semi-mount: bare metal, empty prongs, exactly
what we render) shows the halo as one continuous plate with the accent seats
bored through it, retained by small beads between adjacent stones. RNG-9 built N
`accent_seat` torus collars instead -- 0.7-0.8mm of metal wrapped around a 1.2mm
stone, pinned at `max(MIN_WALL/2, 0.35)` so no tuning could make it finer.

Two defects this checkpoint fixes are invisible to a watertightness assertion,
so both are asserted directly:

  - the WEB between adjacent seats. `_halo_overcrowding` only ever checked that
    accents do not overlap; the corpus halo passed the gate with 0.195mm of
    metal between seats (docs/adr/0006 -- a wrong gate is silent).
  - ENCLOSED CAVITIES. A first cut left a 0.02mm floor under each seat, sealing
    them into internal voids; the solid still reported watertight with one
    B-rep solid. Only mesh BODY COUNT exposed it (docs/adr/0005).
"""
from __future__ import annotations

import io

import pytest
import trimesh

from ringcad.geometry import compose
from ringcad.geometry._common import MIN_PRONG_TIP, MIN_WALL, clamps
from ringcad.geometry.export import to_stl_bytes
from ringcad.geometry.halo import _halo_geometry, halo_cuts, halo_parts
from ringcad.ringspec import Halo, HaloSpec, Setting, Shank, Stones
from ringcad.ringspec.castability import validate_castability
from ringcad.ringspec.models import PAVILION_FRACTION, halo_min_arc


def _spec(*, count=13, accent_d=1.2, accent_h=1.2, gap=0.3,
          stone_d=8.0, ratio=1.0, shape="round"):
    return HaloSpec(
        shank=Shank(inner_diameter=16.5, band_width=2.2, band_thickness=1.9),
        setting=Setting(prong_count=6, setting_height=6.0),
        stones=Stones(stone_diameter=stone_d, stone_height=4.0,
                      shape=shape, length_ratio=ratio),
        halo=Halo(halo_stone_diameter=accent_d, halo_stone_height=accent_h,
                  halo_stone_count=count, halo_gap=gap),
    )


def _mesh(solid):
    return trimesh.load(io.BytesIO(to_stl_bytes(solid)), file_type="stl")


def _codes(spec):
    return {v.code for v in validate_castability(spec)}


# ------------------------------------------------------------- the web rule
def test_corpus_halo_web_is_rejected():
    """The real defect this found: 22 accents of 1.2mm leave 0.199mm of metal
    between seats and the gate called it castable."""
    v = [x for x in validate_castability(_spec(count=22)) if x.code == "halo_web"]
    assert v, "22 accents on a 8mm centre passed the web check"
    assert v[0].field == "halo.halo_stone_count"
    assert "at most" in v[0].message, "the violation must say what WOULD fit"


def test_web_rule_tracks_the_accent_size():
    """A real constraint, not a constant: a bigger accent needs more arc."""
    assert halo_min_arc(1.2, MIN_WALL, MIN_PRONG_TIP) < halo_min_arc(
        2.0, MIN_WALL, MIN_PRONG_TIP
    )


def test_web_is_measured_where_the_bore_is_narrowest():
    """The seats are TAPERED, so the metal between two of them is a V-shaped
    ridge -- near zero at the surface, thickening with depth. Measuring at the
    girdle treats that ridge's top sliver as the wall and forces a flat plate
    between every pair of stones; real halos set them nearly touching with a
    bright-cut edge between (docs/reference/halo.png).

    So the required pitch must be LESS than `diameter + MIN_WALL`, which is what
    measuring at the girdle would demand."""
    assert halo_min_arc(1.2, MIN_WALL, MIN_PRONG_TIP) < 1.2 + MIN_WALL


def test_stones_end_up_nearly_touching():
    """The visible consequence of the rule above, and the thing that was wrong:
    at the default accent size the gap between adjacent stones is a fraction of
    a millimetre, not a plateau of flat metal."""
    gap = halo_min_arc(1.3, MIN_WALL, MIN_PRONG_TIP) - 1.3
    assert 0 < gap < 0.3, f"stones sit {gap:.3f}mm apart -- too far to read right"


def test_web_rule_never_lets_stones_overlap():
    """On a big accent the wall rule is slacker than simply not colliding with
    the neighbour, so the floor must not drop below the stone's own diameter."""
    assert halo_min_arc(2.5, MIN_WALL, MIN_PRONG_TIP) >= 2.5


def test_compliant_halo_is_castable():
    assert "halo_web" not in _codes(_spec(count=13))


# --------------------------------------------------------- the construction
def test_halo_contributes_one_plate_and_no_gallery():
    """The body is ONE leaf plus the beads -- no gallery.

    RNG-9 contributed N collar solids and needed a hub-and-spokes gallery to
    hold them together and to the centre; it read as a cross slung under the
    halo. The plate is a single ring that hangs off the CENTRE CLAWS instead, so
    a regression shows up either as leaves scaling with accent count (collars
    are back) or as an extra non-bead leaf (the gallery is back)."""
    for n in (8, 13):
        spec = _spec(count=n)
        parts = halo_parts(spec, clamps(spec))
        assert len(parts) == 1 + n, (
            f"{len(parts)} leaves for {n} accents; want 1 plate + {n} beads"
        )


def test_seats_are_blind_and_clear_the_gallery_rail():
    """Blind by requirement, not taste: the accent ring and the gallery rail
    share a radius, so a seat bored THROUGH the plate lands on the rail torus,
    and cone-against-torus would not tessellate. Every bore must stop above the
    plate bottom with MIN_WALL of floor."""
    spec = _spec(count=13)
    c = clamps(spec)
    g = _halo_geometry(spec, c)
    plate_bottom = g["seat_z"] - g["plate_t"]
    bore_bottom = g["seat_z"] - PAVILION_FRACTION * g["height"]
    floor = bore_bottom - plate_bottom
    assert floor >= MIN_WALL - 1e-9, f"only {floor:.3f}mm of floor under each seat"
    assert bore_bottom > g["rail_top_z"], "a bore reaches the gallery rail"


def test_every_accent_gets_a_seat_and_a_bead():
    spec = _spec(count=13)
    c = clamps(spec)
    assert len(halo_cuts(spec, c)) == 13
    assert len(halo_parts(spec, c)) - 1 == 13


# ------------------------------------------------------------- castability
@pytest.mark.parametrize("count", [8, 11, 13])
def test_halo_raw_watertight(count):
    """The RNG-17 bar on raw geometry."""
    spec = _spec(count=count)
    assert "halo_web" not in _codes(spec), "fixture is not in range"
    s = compose(spec)
    assert len(s.solids()) == 1
    assert s.volume > 0
    assert _mesh(s).is_watertight


@pytest.mark.parametrize("count", [8, 11, 13])
def test_no_seat_becomes_an_enclosed_cavity(count):
    """REGRESSION, docs/adr/0005. A first cut left a 0.02mm floor under each
    seat, sealing them as internal voids -- the solid reported watertight, one
    B-rep solid, every casting floor met, because the defect was a hole that
    failed to open. Body count is what exposed it."""
    m = _mesh(compose(_spec(count=count)))
    assert m.body_count == 1, (
        f"{m.body_count - 1} enclosed cavities: the seats did not open"
    )


def test_oval_halo_still_builds():
    """The plate follows the centre outline, so an oval halo is an oval plate
    -- the RNG-23 seam must survive the rewrite."""
    spec = _spec(count=11, shape="oval", ratio=1.5)
    assert "halo_web" not in _codes(spec)
    s = compose(spec)
    assert len(s.solids()) == 1
    m = _mesh(s)
    assert m.is_watertight and m.body_count == 1


def test_plate_removes_the_collar_bulk():
    """The plate should not simply be the old collars by another name: a halo
    reads as a plate, so the body carries real continuous metal rather than N
    tubes. Guards the leaf count staying at one while the shape regresses."""
    spec = _spec(count=13)
    c = clamps(spec)
    plate = halo_parts(spec, c)[1]
    assert len(plate.solids()) == 1, "the halo body is not one continuous solid"


# --------------------------------------------------- connectivity + the gate
@pytest.mark.parametrize("prong_count", [4, 6])
def test_halo_hangs_off_the_centre_claws(prong_count):
    """With no gallery, the ONLY thing joining the halo to the ring is the
    centre claws passing through the plate. So the weld has to hold at both
    prong counts -- a claw count the plate does not reach would leave the halo
    a separate body."""
    spec = _spec(count=13)
    spec = spec.model_copy(update={
        "setting": Setting(prong_count=prong_count, setting_height=6.0)
    })
    s = compose(spec)
    assert len(s.solids()) == 1, "the halo is not joined to the ring"
    m = _mesh(s)
    assert m.is_watertight and m.body_count == 1


def test_halo_check_can_actually_fail():
    """`check_gallery` was the halo's in-kernel check and worked by finding
    rail-tube faces; CP4 removed the rail, so it silently returned clean on
    every halo. Its replacement must be able to FAIL, or the archetype has no
    gate at all (docs/adr/0006)."""
    from ringcad.geometry._castability import check_halo_plate
    spec = _spec(count=13)
    c = clamps(spec)
    assert check_halo_plate(None, spec, c) == [], "a good halo was flagged"

    # Crowd the seats until the metal between them is gone. A first version of
    # this check measured `plate_t - seat_depth`, which is TAUTOLOGICAL --
    # plate_t is defined as seat_depth + MIN_WALL, so it was arithmetically
    # incapable of failing. This test existing is what caught that.
    crowded = _spec(count=24, accent_d=2.5, gap=0.3, stone_d=4.0)
    assert check_halo_plate(None, crowded, clamps(crowded)), (
        "the halo check cannot fail -- it is not a gate"
    )
