"""RNG-11 — side-stone castability gate: `_side_stone_overcrowding` only.

Not a wall-thickness proxy (docs/adr/0003): the channel-wall thickness (CP2)
is a fixed construction margin, independent of `accent_gap`, exactly like the
trilogy post / gallery rail are independent of their own gap fields. Instead
this checks two real placement facts the row-along-the-shoulder math (Decision
6 in specs/RNG-11.md) doesn't self-guard:

  (a) the row (accent_count_per_side spaced by accent_gap) must fit between
      A_START (clears the centre head) and A_MAX (stays off the ring base, so
      it stays resizable) -- else it flags accent_count_per_side;
  (b) adjacent accents' true CHORD (straight-line) distance at the band's
      outer radius must clear their combined diameter -- the same arc-vs-chord
      divergence `_trilogy_overcrowding` guards against -- else it flags
      accent_gap.

Checks return early on the first violation found (a) then (b), matching the
existing halo/trilogy overcrowding checks' shape.
"""
import json
import math

import pytest

from ringcad.ringspec import SideStoneSpec, validate_castability, validate_spec

SETTING = {"prong_count": 6, "setting_height": 6.0}


def _side_stone_spec(shank=None, stones=None, side_stone=None):
    """Build a real, schema-valid SideStoneSpec from base fixtures + overrides."""
    spec = validate_spec(
        {
            "archetype": "side_stone",
            "shank": {
                "inner_diameter": 16.5,
                "band_width": 2.2,
                "band_thickness": 1.9,
                "shank_taper": 1.7,
                **(shank or {}),
            },
            "setting": SETTING,
            "stones": {"stone_diameter": 6.5, "stone_height": 4.0, **(stones or {})},
            "side_stone": {
                "accent_stone_diameter": 1.5,
                "accent_stone_height": 1.2,
                "accent_count_per_side": 3,
                "accent_gap": 0.3,
                "retention": "channel",
                **(side_stone or {}),
            },
        }
    )
    assert isinstance(spec, SideStoneSpec)
    return spec


def _fields(spec):
    return [v.field for v in validate_castability(spec)]


# --- golden side-stone defaults must be castable -------------------------------
def test_golden_side_stone_defaults_are_castable():
    spec = _side_stone_spec()
    assert validate_castability(spec) == []


def test_generously_spaced_side_stone_does_not_flag_overcrowding():
    spec = _side_stone_spec(side_stone={"accent_count_per_side": 2, "accent_gap": 1.0})
    assert _fields(spec) == []


# --- (a) too many accents overrun the shoulder span before the ring base ------
def test_too_many_accents_flags_count_field():
    spec = _side_stone_spec(
        side_stone={
            "accent_stone_diameter": 2.5,
            "accent_gap": 1.0,
            "accent_count_per_side": 8,
        }
    )
    assert "side_stone.accent_count_per_side" in _fields(spec)


# --- (b) tightly packed accents on a small shoulder collide (chord < arc) -----
def test_tight_accents_on_small_ring_flags_gap_field():
    spec = _side_stone_spec(
        shank={"inner_diameter": 2.0, "band_thickness": 0.8, "shank_taper": 1.0},
        side_stone={
            "accent_stone_diameter": 2.5,
            "accent_gap": 0.2,
            "accent_count_per_side": 2,
        },
    )
    assert "side_stone.accent_gap" in _fields(spec)


# --- side_stone violations are JSON-serializable -------------------------------
def test_side_stone_violations_are_json_serializable():
    spec = _side_stone_spec(
        side_stone={
            "accent_stone_diameter": 2.5,
            "accent_gap": 1.0,
            "accent_count_per_side": 8,
        }
    )
    violations = validate_castability(spec)
    assert violations, "expected at least one side_stone violation to serialize"
    json.dumps([v.model_dump() for v in violations])
