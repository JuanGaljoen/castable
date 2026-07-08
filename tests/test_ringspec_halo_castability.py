"""RNG-9 — halo castability gate: model-level `_halo_overcrowding` only.

CP1 originally shipped three halo proxies (`_halo_wall`, `_halo_accent_tip`,
`_halo_overcrowding`) explicitly flagged "fuzzy... pending a pin against real
geometry." CP2/CP3 built that real geometry (gallery + accent seat/prong,
castable BY CONSTRUCTION across the documented field range, per
tests/test_halo_watertight.py's BAND). RNG-9 CP4 (endpoint wire-up) found the
wall/accent-tip proxies rejected the RNG-9 golden-halo DEFAULTS that CP3 itself
proved clean, so they were retired — see the note in
ringcad/ringspec/castability.py. `_halo_overcrowding` stays: it catches a
genuine cross-field geometric impossibility (arc spacing between accents) that
construction does not guard against.
"""
import json

import pytest

from ringcad.ringspec import HaloSpec, validate_castability, validate_spec

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


# --- The golden-halo defaults must be castable (regression for the CP4 bug) --
def test_golden_halo_defaults_are_castable():
    spec = _halo_spec()
    assert validate_castability(spec) == []


# --- overcrowding — too many big accents in the ring flags the count ---------
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


# --- halo violations are JSON-serializable ------------------------------------
def test_halo_violations_are_json_serializable():
    spec = _halo_spec(
        halo={"halo_stone_count": 24, "halo_stone_diameter": 2.5, "halo_gap": 0.3}
    )
    violations = validate_castability(spec)
    assert violations, "expected at least one halo violation to serialize"
    json.dumps([v.model_dump() for v in violations])
