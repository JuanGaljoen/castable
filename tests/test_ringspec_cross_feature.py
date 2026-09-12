"""RNG-24 CP2 — cross-feature castability, through the public seams only.

The contract (RNG-24 CP1) already allows any subset of {halo, trilogy,
side_stone}; CP2 is what makes a genuine combination trustworthy rather than
merely expressible. Two golden combinations anchor this file, both found by
running the real numbers during CP2's own development (see footprint.py):

  * halo + side-stone shoulders (the evidenced AC — three separate corpus
    photos read this combination correctly and had the shoulders discarded
    by the old archetype union) CLEARS and generates as one raw watertight
    manifold, no repair.
  * halo + trilogy does NOT clear at the same defaults: both are fixed at
    the head and neither can move to make room for the other, so this is
    the genuine negative case (RNG-24 CP2's own design note).
"""
from __future__ import annotations

from ringcad.geometry.export import to_stl_bytes
from ringcad.geometry.module import compose
from ringcad.mesh_validator import validate_and_repair
from ringcad.ringspec import (
    Halo, RingSpec, Setting, Shank, SideStone, Stones, Trilogy,
    validate_castability,
)

SHANK = Shank(inner_diameter=16.5, band_width=3.2, band_thickness=1.9)
SETTING = Setting(prong_count=6, setting_height=6.0)
STONES = Stones(stone_diameter=6.5, stone_height=4.0)


def _spec(**features) -> RingSpec:
    return RingSpec(shank=SHANK, setting=SETTING, stones=STONES, **features)


def test_halo_and_side_stone_golden_defaults_clear():
    spec = _spec(halo=Halo(), side_stone=SideStone())
    assert validate_castability(spec) == []


def test_halo_and_side_stone_generates_one_raw_watertight_manifold():
    spec = _spec(halo=Halo(), side_stone=SideStone())
    solid = compose(spec)
    assert len(solid.solids()) == 1
    assert solid.volume > 0
    outcome = validate_and_repair(to_stl_bytes(solid))
    assert outcome.mesh_valid
    assert not outcome.mesh_repaired
    assert outcome.body_count == 1


def test_halo_and_trilogy_overcrowd_and_name_both_features():
    spec = _spec(halo=Halo(), trilogy=Trilogy())
    violations = validate_castability(spec)
    codes = [v.code for v in violations]
    assert "cross_feature_overcrowding" in codes
    overcrowded = next(v for v in violations if v.code == "cross_feature_overcrowding")
    assert "halo" in overcrowded.field
    assert "trilogy" in overcrowded.field


def test_side_stone_alone_is_unaffected_by_cross_feature_gate():
    """No OTHER feature present — the gate must not fire against itself
    (side_stone's own two shoulders are not a cross-feature pair)."""
    spec = _spec(side_stone=SideStone())
    codes = [v.code for v in validate_castability(spec)]
    assert "cross_feature_overcrowding" not in codes
