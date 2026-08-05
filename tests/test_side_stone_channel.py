"""RNG-19 CP3 -- channel setting built as a SUBTRACTIVE module.

`docs/jewelry-design-principles.md` #Channel: channel setting holds stones in a
groove cut into the band between two walls, with seats cut into the walls' inner
faces -- NO prongs and NO per-stone collar, by definition. RNG-11 shipped raised
`Torus` beads (halo geometry where its premise does not hold) because a real
channel needs `accent_d + 2*MIN_WALL` = 3.1mm of band and the corpus spec
supplies 2.0mm.

We render metal only, so a channel row IS the negative of its stones: the band is
cut, not decorated. The wall bearings fall out of the subtraction at the
research's 0.2mm girdle penetration rather than being modelled as features.
"""
from __future__ import annotations

import pytest

from ringcad.geometry import compose
from ringcad.geometry._common import MIN_WALL, clamps
from ringcad.ringspec import (
    Setting, Shank, SideStone, SideStoneSpec, Stones, validate_spec,
)
from ringcad.ringspec.castability import validate_castability as check_spec


def _spec(*, a_dia=1.5, a_height=1.2, a_count=3, a_gap=0.3,
          band_width=None, band_thickness=1.9):
    """A side-stone spec whose band FITS its channel by default: the width rule
    is `a_dia + 2*MIN_WALL`, so the golden 1.5mm accent needs 3.1mm."""
    if band_width is None:
        band_width = a_dia + 2 * MIN_WALL + 0.1
    return SideStoneSpec(
        shank=Shank(inner_diameter=16.5, band_width=band_width,
                    band_thickness=band_thickness),
        setting=Setting(prong_count=6, setting_height=6.0),
        stones=Stones(stone_diameter=6.5, stone_height=4.0),
        side_stone=SideStone(
            accent_stone_diameter=a_dia, accent_stone_height=a_height,
            accent_count_per_side=a_count, accent_gap=a_gap,
        ),
    )


def _codes(spec):
    return {v.code for v in check_spec(spec)}


# ------------------------------------------------------- the fit constraint
def test_band_too_narrow_for_a_channel_is_rejected():
    """A channel groove runs across the band's WIDTH, so the band must carry
    the stone plus a MIN_WALL wall each side. RNG-11's corpus band (2.0mm)
    cannot physically hold a 1.5mm channel -- that is why it shipped beads."""
    spec = _spec(a_dia=1.5, band_width=2.0)
    violations = [v for v in check_spec(spec)
                  if v.code == "side_stone_channel_fit"]
    assert violations, "a 2.0mm band accepted a 1.5mm channel"
    assert violations[0].field == "shank.band_width"
    assert violations[0].limit_mm == pytest.approx(1.5 + 2 * MIN_WALL)


def test_band_exactly_wide_enough_is_accepted():
    """The rule is an inclusive floor, not a strict inequality."""
    assert "side_stone_channel_fit" not in _codes(
        _spec(a_dia=1.5, band_width=1.5 + 2 * MIN_WALL)
    )


def test_wider_accents_demand_a_wider_band():
    """The floor tracks the accent, so it is a real constraint rather than a
    constant: a 2.5mm accent needs 4.1mm of band."""
    assert "side_stone_channel_fit" in _codes(_spec(a_dia=2.5, band_width=3.5))
    assert "side_stone_channel_fit" not in _codes(_spec(a_dia=2.5, band_width=4.2))


# ----------------------------------------------------- the floor constraint
def test_groove_cannot_cut_through_the_band_floor():
    """The groove is cut inward from the outer surface, so the metal left
    under it must still clear MIN_WALL -- otherwise the cut severs the band
    and the ring is no longer a solid."""
    violations = [v for v in check_spec(_spec(a_height=3.0, band_thickness=1.6))
                  if v.code == "side_stone_channel_floor"]
    assert violations, "a 3.0mm-deep channel was allowed in a 1.6mm band"
    assert violations[0].field == "shank.band_thickness"


def test_shallow_accents_clear_the_floor():
    assert "side_stone_channel_floor" not in _codes(
        _spec(a_height=1.2, band_thickness=1.9)
    )


# --------------------------------------------------------- the geometry
def test_channel_removes_metal_rather_than_adding_it():
    """The inversion of RNG-11's `accents_are_proud_not_buried`. That test
    guarded a bug where the beads were buried and added nothing; a real channel
    is a groove, so it must REMOVE a meaningful amount of metal. Both failure
    modes -- no cut at all, and a decorative bead -- fail this."""
    spec = _spec()
    band = compose(spec)
    bare = compose(spec, archetype="solitaire")
    removed = bare.volume - band.volume
    assert removed > 2.0, (
        f"the channel removes only {removed:.2f}mm^3 -- it is not a groove"
    )


def test_channel_band_is_a_single_watertight_solid(raw_validate):
    """The RNG-17 bar on raw geometry, plus the ADR-0005 volume assertion: a
    cut that severed the band would still report watertight."""
    s = compose(_spec())
    assert len(s.solids()) == 1, "the channel cut split the band into pieces"
    assert s.volume > 0
    result = raw_validate(s)
    assert result.body_count == 1
    assert result.non_manifold_edges == 0
    assert result.is_watertight


def test_no_raised_collar_remains():
    """Channel setting has no per-stone collar by definition. The composed band
    must not stand proud of the shank's own outer surface -- a `Torus` bead
    would push the bounding box out past it."""
    spec = _spec()
    band = compose(spec).bounding_box()
    bare = compose(spec, archetype="solitaire").bounding_box()
    # Compared against the bare solitaire, not an absolute radius: the centre
    # head legitimately reaches far past the band on both.
    assert band.size.X <= bare.size.X + 1e-6, (
        f"the channel band reaches {band.size.X - bare.size.X:.3f}mm further "
        "than the same ring without it -- a collar or rail survived CP3"
    )
    assert band.size.Z <= bare.size.Z + 1e-6, (
        "the channel band is wider across the finger than the bare shank"
    )


@pytest.mark.parametrize("a_dia,a_height,a_count,a_gap,bt", [
    (0.9, 0.8, 1, 0.2, 1.6),
    (1.5, 1.2, 3, 0.3, 1.9),
    (2.5, 1.5, 2, 1.0, 2.4),
    (0.9, 1.4, 4, 1.0, 2.0),
    (1.5, 1.0, 5, 0.5, 1.8),
])
def test_channel_band_raw_watertight_across_the_range(
    raw_validate, a_dia, a_height, a_count, a_gap, bt
):
    """Every in-range, fit-satisfying channel band is castable on RAW geometry."""
    spec = _spec(a_dia=a_dia, a_height=a_height, a_count=a_count,
                 a_gap=a_gap, band_thickness=bt)
    assert not [v for v in check_spec(spec)
                if v.code.startswith("side_stone_channel")], "spec is not in range"
    s = compose(spec)
    assert len(s.solids()) == 1
    assert s.volume > 0
    result = raw_validate(s)
    assert result.non_manifold_edges == 0
    assert result.is_watertight


def test_roundtrip_still_validates():
    """No schema change: a CP3 channel spec still round-trips through the
    public validator."""
    spec = _spec()
    assert validate_spec(spec.model_dump()).archetype == "side_stone"
