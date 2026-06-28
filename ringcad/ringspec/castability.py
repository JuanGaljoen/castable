"""Castability validation — distinct from schema validation (RNG-14, AC3).

Schema validation (models.py) only checks structural validity; a well-formed
spec can still be physically uncastable. `validate_castability` runs the
lost-wax manufacturing gate on a schema-valid spec and returns structured
`Violation`s *before* any geometry runs. An empty list means castable.

Casting constants are single-sourced from ringcad.mesh_validator (the same
limits the post-generation mesh check uses) — never duplicated here.
"""
from __future__ import annotations

import math

from pydantic import BaseModel

from ringcad.mesh_validator import MIN_PRONG_TIP_MM, MIN_WALL_MM

from .models import RingSpec

# Fraction of the inter-prong seat arc that becomes prong wire. The prong-tip
# diameter is a coarse proxy (plan Risk #2, "fuzzy") pending an RNG-15 pin
# against the SCAD/build123d geometry; do not treat it as exact.
_PRONG_WIRE_FRACTION = 0.25


class Violation(BaseModel):
    """A single structured castability failure (JSON-serializable)."""

    code: str
    field: str | None
    message: str
    limit_mm: float | None
    actual_mm: float | None
    severity: str = "error"


def _min_wall(spec: RingSpec) -> list[Violation]:
    """Walls below MIN_WALL_MM (0.8 inclusive passes)."""
    checks = (
        ("shank.band_thickness", spec.shank.band_thickness),
        ("shank.band_width", spec.shank.band_width),
        ("setting.setting_height", spec.setting.setting_height),
    )
    out: list[Violation] = []
    for field, value in checks:
        if value < MIN_WALL_MM:
            out.append(
                Violation(
                    code="min_wall",
                    field=field,
                    message=f"{field} {value}mm is below the {MIN_WALL_MM}mm "
                    "minimum wall thickness for lost-wax casting.",
                    limit_mm=MIN_WALL_MM,
                    actual_mm=value,
                )
            )
    return out


def _min_prong_tip(spec: RingSpec) -> list[Violation]:
    """Derived prong-tip diameter below MIN_PRONG_TIP_MM (coarse proxy)."""
    arc = math.pi * spec.stones.stone_diameter / spec.setting.prong_count
    tip = arc * _PRONG_WIRE_FRACTION
    if tip < MIN_PRONG_TIP_MM:
        return [
            Violation(
                code="min_prong_tip",
                field="setting.prong_count",
                message=f"Derived prong-tip diameter {tip:.3f}mm is below the "
                f"{MIN_PRONG_TIP_MM}mm minimum for {spec.setting.prong_count} "
                "prongs at this stone size.",
                limit_mm=MIN_PRONG_TIP_MM,
                actual_mm=tip,
            )
        ]
    return []


def _geometric(spec: RingSpec) -> list[Violation]:
    """Cross-field geometric impossibilities."""
    out: list[Violation] = []
    if spec.stones.stone_diameter >= spec.shank.inner_diameter:
        out.append(
            Violation(
                code="stone_exceeds_bore",
                field="stones.stone_diameter",
                message="Stone diameter must be smaller than the finger bore "
                "(inner_diameter).",
                limit_mm=spec.shank.inner_diameter,
                actual_mm=spec.stones.stone_diameter,
            )
        )
    if spec.stones.stone_height >= spec.setting.setting_height:
        out.append(
            Violation(
                code="stone_exceeds_head",
                field="stones.stone_height",
                message="Stone height must be smaller than the setting height.",
                limit_mm=spec.setting.setting_height,
                actual_mm=spec.stones.stone_height,
            )
        )
    return out


def validate_castability(spec: RingSpec) -> list[Violation]:
    """Run the full lost-wax gate; [] means the spec is castable."""
    return _min_wall(spec) + _min_prong_tip(spec) + _geometric(spec)


def is_castable(spec: RingSpec) -> bool:
    """True iff the spec produces no castability violations."""
    return not validate_castability(spec)
