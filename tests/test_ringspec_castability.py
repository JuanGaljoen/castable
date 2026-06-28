"""RNG-14 AC3 — castability validation, distinct from schema validation.

RED until `ringcad.ringspec` exists. `validate_castability(spec)` runs on a
schema-valid spec and returns structured `Violation`s for manufacturing
problems (thin walls, geometric impossibilities) *before* geometry generation.
A castable spec returns []. Casting floors are single-sourced from
ringcad.mesh_validator (MIN_WALL_MM / MIN_PRONG_TIP_MM) — never duplicated.
"""
import json

import pytest

from ringcad.mesh_validator import MIN_WALL_MM
from ringcad.ringspec import (
    from_params,
    is_castable,
    validate_castability,
)

# Known-good, castable solitaire (matches the contract's worked example).
GOOD_PARAMS = {
    "inner_diameter": 16.5,
    "band_width": 2.2,
    "band_thickness": 1.9,
    "stone_diameter": 6.5,
    "stone_height": 4.0,
    "prong_count": 6,
    "setting_height": 6.0,
}


def _params(**changes):
    p = dict(GOOD_PARAMS)
    p.update(changes)
    return p


# --- AC3: a castable spec yields no violations -------------------------------
def test_good_spec_is_castable():
    spec = from_params(GOOD_PARAMS)
    assert validate_castability(spec) == []
    assert is_castable(spec) is True


# --- AC3: min-wall floor (band_thickness < 0.8mm) ----------------------------
def test_thin_band_thickness_flags_exactly_one_min_wall():
    spec = from_params(_params(band_thickness=0.79))
    violations = validate_castability(spec)
    min_wall = [v for v in violations if v.code == "min_wall"]
    assert len(min_wall) == 1
    assert min_wall[0].field == "shank.band_thickness"


def test_band_thickness_boundary_080_is_inclusive():
    spec = from_params(_params(band_thickness=0.8))
    violations = validate_castability(spec)
    assert not any(
        v.code == "min_wall" and v.field == "shank.band_thickness"
        for v in violations
    )


def test_min_wall_limit_is_single_sourced_constant():
    spec = from_params(_params(band_thickness=0.79))
    min_wall = [v for v in validate_castability(spec) if v.code == "min_wall"][0]
    # The validator must reference the canonical constant, not a literal 0.8.
    assert min_wall.limit_mm == MIN_WALL_MM


# --- AC3: geometric impossibility (stone wider than the finger bore) ---------
def test_stone_exceeds_bore_is_flagged():
    spec = from_params(_params(stone_diameter=18.0, inner_diameter=16.5))
    violations = validate_castability(spec)
    assert any(v.code == "stone_exceeds_bore" for v in violations)


# --- AC3: violations are JSON-serializable (for API surfacing in RNG-15) -----
def test_violations_are_json_serializable():
    spec = from_params(_params(band_thickness=0.79, stone_diameter=18.0))
    violations = validate_castability(spec)
    json.dumps([v.model_dump() for v in violations])  # raises if non-JSON


# NOTE: the min_prong_tip proxy (derived tip diameter from prong_count + seat
# circumference) is an explicit approximation per the plan (Risk #2, "fuzzy").
# Asserting an exact trigger would pin the test to an unstable formula, so it is
# deliberately under-specified here — the min_wall and geometric rules give
# robust AC3 coverage. Tighten this once RNG-15 pins the proxy against SCAD.
