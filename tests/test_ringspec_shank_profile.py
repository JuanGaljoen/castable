"""Shank cross-section profile in RingSpec (RNG-25 CP1).

The contract half of the shank-profile work: `outer_profile` and
`inner_profile` join the shank group, both defaulted to `domed`/`domed`
("court" -- today's `Ellipse` section) so every spec written before RNG-25
stays valid and renders exactly as before.
"""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from ringcad.ringspec import (
    TrilogySpec, from_params, to_params, validate_castability, validate_spec,
)
from ringcad.ringspec.models import Shank


def _spec(**shank_overrides) -> dict:
    shank = {"inner_diameter": 16.5, "band_width": 2.2, "band_thickness": 1.9}
    shank.update(shank_overrides)
    return {
        "version": "1.0",
        "archetype": "solitaire",
        "shank": shank,
        "setting": {"prong_count": 6, "setting_height": 6.0},
        "stones": {"stone_diameter": 6.5, "stone_height": 4.0},
    }


# --- backward compatibility --------------------------------------------------

def test_spec_without_profile_fields_defaults_to_court():
    spec = validate_spec(_spec())
    assert spec.shank.outer_profile == "domed"
    assert spec.shank.inner_profile == "domed"


def test_shank_model_defaults_match_todays_geometry():
    shank = Shank(inner_diameter=16.5, band_width=2.2, band_thickness=1.9)
    assert shank.outer_profile == "domed"
    assert shank.inner_profile == "domed"


# --- the six profiles ---------------------------------------------------------

@pytest.mark.parametrize("outer", ["domed", "flat", "knife_edge"])
@pytest.mark.parametrize("inner", ["domed", "flat"])
def test_every_profile_combination_is_valid(outer, inner):
    spec = validate_spec(
        _spec(outer_profile=outer, inner_profile=inner)
    )
    assert spec.shank.outer_profile == outer
    assert spec.shank.inner_profile == inner


def test_unknown_outer_profile_rejected_with_field_name():
    with pytest.raises(ValidationError) as exc_info:
        validate_spec(_spec(outer_profile="bulging"))
    assert "outer_profile" in str(exc_info.value)


def test_unknown_inner_profile_rejected_with_field_name():
    with pytest.raises(ValidationError) as exc_info:
        validate_spec(_spec(inner_profile="bulging"))
    assert "inner_profile" in str(exc_info.value)


# --- 7-param round trip stays lossless (RNG-14 AC1) --------------------------

def test_round_trip_ignores_profile_fields_like_shank_taper():
    params = {
        "inner_diameter": 18.0,
        "band_width": 2.0,
        "band_thickness": 1.5,
        "stone_diameter": 6.0,
        "stone_height": 4.0,
        "prong_count": 4,
        "setting_height": 5.0,
    }
    spec = from_params(params)
    assert spec.shank.outer_profile == "domed"
    assert spec.shank.inner_profile == "domed"
    assert to_params(spec) == params


# --- head_r must not drift between the check and the builder (docs/adr/0002) -

def _trilogy_spec(outer_profile, inner_profile):
    spec = validate_spec(
        {
            "archetype": "trilogy",
            "shank": {
                "inner_diameter": 16.5,
                "band_width": 2.2,
                "band_thickness": 1.9,
                "shank_taper": 1.7,
                "outer_profile": outer_profile,
                "inner_profile": inner_profile,
            },
            "setting": {"prong_count": 6, "setting_height": 6.0},
            "stones": {"stone_diameter": 6.5, "stone_height": 4.0},
            "trilogy": {
                "side_stone_diameter": 2.5,
                "side_stone_height": 1.8,
                "side_stone_gap": 0.6,
            },
        }
    )
    assert isinstance(spec, TrilogySpec)
    return spec


@pytest.mark.parametrize("outer", ["domed", "flat", "knife_edge"])
@pytest.mark.parametrize("inner", ["domed", "flat"])
def test_trilogy_overcrowding_verdict_is_unchanged_by_profile(outer, inner):
    """`_trilogy_overcrowding` derives `head_r` from the shank's thickness
    taper, not its cross-section profile -- every profile reaches full
    thickness at the centreline, so the verdict for a fixed golden spec must
    be identical whichever profile is chosen."""
    baseline = [v.code for v in validate_castability(_trilogy_spec("domed", "domed"))]
    verdict = [v.code for v in validate_castability(_trilogy_spec(outer, inner))]
    assert verdict == baseline
