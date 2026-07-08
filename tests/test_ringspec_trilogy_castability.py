"""RNG-10 — trilogy castability gate: `_trilogy_overcrowding` only.

Unlike halo's CP1 (which shipped, then had to retire, wall/tip proxies keyed
on spec fields — see docs/adr/0002), this check is NOT a wall-thickness proxy:
the side-setting post's wall will be sized from a fixed construction margin
independent of `side_stone_gap` (mirroring the gallery hub), so a
`side_stone_gap >= MIN_WALL_MM` check would repeat that exact anti-pattern.

Instead, `_trilogy_overcrowding` checks a genuine geometric impossibility: the
side stone is placed at an angular offset derived from an ARC-LENGTH
approximation (`stone_r + side_stone_gap + side_r`), but the two stones'
actual separation is the CHORD (straight-line) distance, which is always
<= the arc length. At larger offsets the two diverge enough that the stones'
girdles can overlap even though `side_stone_gap` is comfortably positive.
This is the same shape as `_halo_overcrowding` (a real placement-math
constraint construction doesn't independently guard against), not a rehash
of the retired wall proxy.
"""
import json
import math

import pytest

from ringcad.ringspec import TrilogySpec, validate_castability, validate_spec

SETTING = {"prong_count": 6, "setting_height": 6.0}


def _trilogy_spec(shank=None, stones=None, trilogy=None):
    """Build a real, schema-valid TrilogySpec from base fixtures + overrides."""
    spec = validate_spec(
        {
            "archetype": "trilogy",
            "shank": {
                "inner_diameter": 16.5,
                "band_width": 2.2,
                "band_thickness": 1.9,
                "shank_taper": 1.7,
                **(shank or {}),
            },
            "setting": SETTING,
            "stones": {"stone_diameter": 6.5, "stone_height": 4.0, **(stones or {})},
            "trilogy": {
                "side_stone_diameter": 2.5,
                "side_stone_height": 1.8,
                "side_stone_gap": 0.6,
                **(trilogy or {}),
            },
        }
    )
    assert isinstance(spec, TrilogySpec)
    return spec


def _fields(spec):
    return [v.field for v in validate_castability(spec)]


# --- golden trilogy defaults must be castable ---------------------------------
def test_golden_trilogy_defaults_are_castable():
    spec = _trilogy_spec()
    assert validate_castability(spec) == []


# --- overcrowding: an oversized side stone on a small shoulder collides -------
def test_oversized_side_stone_on_small_ring_flags_gap_field():
    spec = _trilogy_spec(
        shank={"inner_diameter": 3.5, "band_thickness": 0.8, "shank_taper": 1.0},
        stones={"stone_diameter": 3.0, "stone_height": 2.0},
        trilogy={"side_stone_diameter": 6.0, "side_stone_gap": 0.3},
    )
    assert "trilogy.side_stone_gap" in _fields(spec)


def test_generously_spaced_trilogy_does_not_flag_overcrowding():
    spec = _trilogy_spec(trilogy={"side_stone_diameter": 1.0, "side_stone_gap": 2.0})
    assert "trilogy.side_stone_gap" not in _fields(spec)


# --- trilogy violations are JSON-serializable ---------------------------------
def test_trilogy_violations_are_json_serializable():
    spec = _trilogy_spec(
        shank={"inner_diameter": 3.5, "band_thickness": 0.8, "shank_taper": 1.0},
        stones={"stone_diameter": 3.0, "stone_height": 2.0},
        trilogy={"side_stone_diameter": 6.0, "side_stone_gap": 0.3},
    )
    violations = validate_castability(spec)
    assert violations, "expected at least one trilogy violation to serialize"
    json.dumps([v.model_dump() for v in violations])
