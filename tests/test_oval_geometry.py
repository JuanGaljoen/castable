"""An oval centre stone produces real oval geometry (RNG-23 CP2).

The bar is RNG-17's: the RAW geometry (no `validate_and_repair`) must be a single
watertight manifold with zero non-manifold edges. `raw_validate` (conftest)
measures the unrepaired mesh, so a fuse that slivers is caught rather than welded
away -- the failure mode that bit RNG-9 CP3, and the top risk on this ticket
since a swept elliptical seat presents a different surface to the claws than a
torus does.

Round geometry must be untouched: `RoundOutline` keeps the original `Torus` call
and even prong spacing, so the existing parity and golden suites stay valid.
"""
from __future__ import annotations

import math

import pytest

from ringcad.geometry import build_solitaire, seat
from ringcad.geometry._common import clamps
from ringcad.geometry.outline import OvalOutline, RoundOutline
from ringcad.ringspec import validate_spec

BASE = {
    "version": "1.0",
    "archetype": "solitaire",
    "shank": {"inner_diameter": 16.5, "band_width": 2.2, "band_thickness": 1.9},
    "setting": {"prong_count": 6, "setting_height": 6.0},
}


def _spec(shape="round", length_ratio=1.0, prong_count=6, stone_diameter=6.5):
    body = {
        **BASE,
        "setting": {"prong_count": prong_count, "setting_height": 6.0},
        "stones": {
            "stone_diameter": stone_diameter,
            "stone_height": 4.0,
            "shape": shape,
            "length_ratio": length_ratio,
        },
    }
    return validate_spec(body)


# --- the outline reaches the geometry layer --------------------------------

def test_clamps_exposes_a_round_outline_by_default():
    assert isinstance(clamps(_spec())["outline"], RoundOutline)


def test_clamps_exposes_an_oval_outline_when_asked():
    c = clamps(_spec(shape="oval", length_ratio=1.6, stone_diameter=6.0))
    outline = c["outline"]
    assert isinstance(outline, OvalOutline)
    # stone_diameter is the SHORT axis, so semi_minor is half of it.
    assert outline.half_width("x") == pytest.approx(3.0)
    assert outline.half_width("y") == pytest.approx(4.8)


def test_ratio_one_stays_round_even_when_shape_says_oval():
    """length_ratio 1.0 is a circle; taking the round path keeps geometry
    bit-identical rather than sweeping a degenerate ellipse."""
    c = clamps(_spec(shape="oval", length_ratio=1.0))
    assert isinstance(c["outline"], RoundOutline)


# --- the seat actually becomes elliptical ----------------------------------

def test_oval_seat_is_longer_along_the_band_than_across_it():
    """Local Y is band-tangential, so an N-S oval is longest along global Y
    after `placement()` maps the local frame onto the +X head axis."""
    spec = _spec(shape="oval", length_ratio=1.8, stone_diameter=6.0)
    bbox = seat(spec).bounding_box()
    across = bbox.max.Z - bbox.min.Z   # local X -> global Z
    along = bbox.max.Y - bbox.min.Y    # local Y -> global Y
    assert along > across * 1.5


def test_round_seat_stays_symmetric():
    bbox = seat(_spec()).bounding_box()
    assert (bbox.max.Y - bbox.min.Y) == pytest.approx(
        bbox.max.Z - bbox.min.Z, rel=1e-6
    )


# --- the castability bar ---------------------------------------------------

@pytest.mark.parametrize("prong_count", [4, 6])
@pytest.mark.parametrize("length_ratio", [1.3, 1.8, 2.5])
def test_oval_solitaire_is_one_raw_watertight_manifold(
    raw_validate, prong_count, length_ratio
):
    spec = _spec(
        shape="oval", length_ratio=length_ratio, prong_count=prong_count,
        stone_diameter=6.0,
    )
    result = raw_validate(build_solitaire(spec))
    assert result.is_watertight, f"raw mesh not watertight (ratio {length_ratio})"
    assert result.non_manifold_edges == 0
    assert result.body_count == 1


@pytest.mark.parametrize("prong_count", [4, 6])
@pytest.mark.parametrize("length_ratio", [1.0, 1.3, 1.8, 2.5])
def test_the_claws_are_actually_there(prong_count, length_ratio):
    """Every claw contributes metal (docs/adr/0005).

    A fuse that silently drops bodies still reports watertight, zero
    non-manifold edges and one solid -- a 6-prong oval at ratio 1.3 once came
    back as the bare peg (5.65 against 39.02) and passed every other check. So
    pin something proportional to the metal that must exist: the peg alone is
    under 10mm3, and each claw adds several more.
    """
    from ringcad.geometry import prong_setting

    shape = "round" if length_ratio == 1.0 else "oval"
    volume = prong_setting(
        _spec(shape=shape, length_ratio=length_ratio,
              prong_count=prong_count, stone_diameter=6.0)
    ).volume
    floor = 10.0 + 3.0 * prong_count
    assert volume > floor, (
        f"{prong_count} claws at ratio {length_ratio} give only {volume:.2f}mm3 "
        f"(expected > {floor:.0f}) -- claws were probably dropped by the fuse"
    )


def test_oval_solitaire_holds_together_at_a_small_stone(raw_validate):
    """Small stone + high elongation is the tightest curvature we allow, and the
    hardest place to keep the seat wall and claw tips castable."""
    spec = _spec(shape="oval", length_ratio=2.5, stone_diameter=2.5)
    result = raw_validate(build_solitaire(spec))
    assert result.is_watertight
    assert result.body_count == 1


# --- prongs sit where the outline says -------------------------------------

def test_oval_prongs_avoid_the_tips_in_the_built_geometry():
    """Guards the whole chain, not just the outline maths: if prong_setting
    stopped consulting the outline, claws would drift back onto the apex."""
    from ringcad.geometry.outline import OvalOutline as _O

    angles = _O(3.0, 5.4).prong_angles(4)
    for theta in angles:
        for tip in (math.pi / 2, 3 * math.pi / 2):
            gap = abs((theta % (2 * math.pi)) - tip)
            assert min(gap, 2 * math.pi - gap) > math.radians(20)
