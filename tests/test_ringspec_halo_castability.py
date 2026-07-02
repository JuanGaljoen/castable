"""RNG-9 Checkpoint 1, CP1-4 — halo castability gate (DIRECTION-ONLY).

RED until HaloSpec + the three halo checks land in ringcad.ringspec.castability.
The import below fails at collection (HaloSpec missing) — the correct RED signal.

These tests assert DIRECTION (a violation is flagged vs not) and the named
field / single-sourced limit constant. They deliberately do NOT pin exact
numeric thresholds: the halo wall / accent-tip / overcrowding proxies are
fuzzy by design (plan Risk #4) and the implementer sets the formula. A tight
boundary assertion would pin the test to an unstable proxy.
"""
import json

import pytest

from ringcad.mesh_validator import MIN_PRONG_TIP_MM, MIN_WALL_MM
from ringcad.ringspec import HaloSpec, validate_castability

SHANK = {
    "inner_diameter": 16.5,
    "band_width": 2.2,
    "band_thickness": 1.9,
    "shank_taper": 1.7,
}
SETTING = {"prong_count": 6, "setting_height": 6.0}
STONES = {"stone_diameter": 6.5, "stone_height": 4.0}
HALO_GROUP = {
    "halo_stone_diameter": 1.3,
    "halo_stone_count": 14,
    "halo_gap": 0.5,
    "halo_stone_height": 1.2,
}


def _halo_spec(halo=None, stones=None):
    """Build a real, schema-valid HaloSpec from base fixtures + overrides."""
    from ringcad.ringspec import validate_spec

    spec = validate_spec(
        {
            "archetype": "halo",
            "shank": SHANK,
            "setting": SETTING,
            "stones": {**STONES, **(stones or {})},
            "halo": {**HALO_GROUP, **(halo or {})},
        }
    )
    assert isinstance(spec, HaloSpec)
    return spec


def _fields(spec):
    return [v.field for v in validate_castability(spec)]


# --- CP1-4: halo_gap wall proxy — tight gap on a large centre stone flags -----
def test_tight_halo_gap_flags_halo_gap_field():
    spec = _halo_spec(halo={"halo_gap": 0.3}, stones={"stone_diameter": 9.0})
    assert "halo.halo_gap" in _fields(spec)


def test_comfortable_halo_gap_does_not_flag_halo_gap():
    spec = _halo_spec(halo={"halo_gap": 1.0}, stones={"stone_diameter": 9.0})
    assert "halo.halo_gap" not in _fields(spec)


# --- CP1-4: overcrowding — too many big accents in the ring flags the count ---
def test_overcrowded_halo_flags_halo_stone_count_field():
    spec = _halo_spec(
        halo={"halo_stone_count": 24, "halo_stone_diameter": 2.5, "halo_gap": 0.3}
    )
    assert "halo.halo_stone_count" in _fields(spec)


def test_sparse_halo_does_not_flag_halo_stone_count():
    spec = _halo_spec(
        halo={"halo_stone_count": 8, "halo_stone_diameter": 0.9}
    )
    assert "halo.halo_stone_count" not in _fields(spec)


# --- CP1-4: accent-tip proxy — a thin accent flags, a generous one does not ---
def test_thin_accent_flags_halo_stone_diameter_field():
    spec = _halo_spec(
        halo={"halo_stone_diameter": 0.9, "halo_stone_height": 0.8}
    )
    assert "halo.halo_stone_diameter" in _fields(spec)


def test_generous_accent_does_not_flag_halo_stone_diameter():
    spec = _halo_spec(
        halo={"halo_stone_diameter": 2.5, "halo_stone_height": 3.0}
    )
    assert "halo.halo_stone_diameter" not in _fields(spec)


# --- CP1-4: halo violations are JSON-serializable ----------------------------
def test_halo_violations_are_json_serializable():
    spec = _halo_spec(
        halo={"halo_gap": 0.3, "halo_stone_diameter": 0.9, "halo_stone_height": 0.8},
        stones={"stone_diameter": 9.0},
    )
    violations = validate_castability(spec)
    assert violations, "expected at least one halo violation to serialize"
    json.dumps([v.model_dump() for v in violations])


# --- CP1-4: limits are single-sourced from mesh_validator, never literals -----
def test_halo_wall_limit_is_single_sourced_constant():
    spec = _halo_spec(halo={"halo_gap": 0.3}, stones={"stone_diameter": 9.0})
    wall = [v for v in validate_castability(spec) if v.field == "halo.halo_gap"]
    assert wall and wall[0].limit_mm == MIN_WALL_MM


def test_halo_accent_tip_limit_is_single_sourced_constant():
    spec = _halo_spec(
        halo={"halo_stone_diameter": 0.9, "halo_stone_height": 0.8}
    )
    tip = [
        v
        for v in validate_castability(spec)
        if v.field == "halo.halo_stone_diameter"
    ]
    assert tip and tip[0].limit_mm == MIN_PRONG_TIP_MM
