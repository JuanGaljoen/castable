"""The castability gate: can this well-formed spec actually be cast?

Runs before any geometry and returns `Violation`s, each naming its field. An
empty list means castable. Limits come from `ringcad.mesh_validator`.
"""
from __future__ import annotations

import math

from pydantic import BaseModel

from ringcad.mesh_validator import MIN_PRONG_TIP_MM, MIN_WALL_MM

from .cuts import ProngType, profile_for
from .footprint import clear as _footprints_clear
from .footprint import halo_footprint, side_stone_footprints, trilogy_footprint
from .footprint import side_stone_start_deg
from .models import (
    SHANK_THICKNESS_TAPER, RingSpec,
    HALO_WELL_BACK_RATIO, channel_band_width, channel_groove_depth,
    effective_thickness_taper, halo_min_arc,
)
from .sections import head_r as _section_head_r
from .sections import section_for

# Side-stone row runs from just off the head (A_START) to A_MAX, leaving the
# base of the ring clear so it can still be resized.
_SIDE_STONE_A_START_DEG = 10.0
_SIDE_STONE_A_MAX_DEG = 110.0

# Share of the girdle arc each prong gets. A coarse estimate; the in-kernel
# `check_prong_setting` measures the real tip.
_PRONG_WIRE_FRACTION = 0.25

# Mirrors geometry/seat.py; restated so this layer doesn't import the kernel.
_SEAT_COLLAR_R = max(MIN_WALL_MM / 2, 0.45)


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
    """Estimated prong-tip diameter below MIN_PRONG_TIP_MM.

    Uses the stone's real girdle length (not a circle of its short axis), and
    divides by TIPS, not prongs: a V-prong forks into two arms (docs/adr/0006).
    """
    stones = spec.stones
    profile = profile_for(getattr(stones, "shape", "round"))
    layout = profile.prong_layout(spec.setting.prong_count)
    tips = len(layout) + sum(1 for _, kind in layout if kind is ProngType.V)
    arc = profile.perimeter(
        stones.stone_diameter / 2, getattr(stones, "length_ratio", 1.0)
    ) / tips
    tip = arc * _PRONG_WIRE_FRACTION
    if tip < MIN_PRONG_TIP_MM:
        return [
            Violation(
                code="min_prong_tip",
                field="setting.prong_count",
                message=f"Derived prong-tip diameter {tip:.3f}mm is below the "
                f"{MIN_PRONG_TIP_MM}mm minimum for {spec.setting.prong_count} "
                f"prongs ({tips} tips) at this stone size.",
                limit_mm=MIN_PRONG_TIP_MM,
                actual_mm=tip,
            )
        ]
    return []


def _geometric(spec: RingSpec) -> list[Violation]:
    """Cross-field geometric impossibilities."""
    out: list[Violation] = []
    # Compare the LONG axis: stone_diameter is the short one.
    stone_length = spec.stones.stone_diameter * getattr(
        spec.stones, "length_ratio", 1.0
    )
    if stone_length >= spec.shank.inner_diameter:
        out.append(
            Violation(
                code="stone_exceeds_bore",
                field="stones.stone_diameter",
                message="Stone must be smaller than the finger bore "
                "(inner_diameter) along its longest axis.",
                limit_mm=spec.shank.inner_diameter,
                actual_mm=stone_length,
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


# No `halo_gap >= MIN_WALL` rule: halo_gap is spacing, not a wall
# (docs/adr/0003). `_halo_web` checks the metal between seats instead.


def _ring_perimeter(semi_minor: float, semi_major: float) -> float:
    """Perimeter of a circle or ellipse (Ramanujan's approximation)."""
    if semi_minor == semi_major:
        return 2 * math.pi * semi_minor
    a, b = semi_major, semi_minor
    return math.pi * (
        3 * (a + b) - math.sqrt((3 * a + b) * (a + 3 * b))
    )


def _halo_overcrowding(spec: RingSpec) -> list[Violation]:
    """Accents packed tighter than their own diameter. Measured around the
    ring the halo actually follows, which is an ellipse for an oval stone."""
    if spec.halo is None:
        return []
    halo = spec.halo
    offset = halo.halo_gap + halo.halo_stone_diameter / 2
    semi_minor = spec.stones.stone_diameter / 2
    semi_major = semi_minor * getattr(spec.stones, "length_ratio", 1.0)
    perimeter = _ring_perimeter(semi_minor + offset, semi_major + offset)
    arc = perimeter / halo.halo_stone_count
    if arc < halo.halo_stone_diameter:
        return [
            Violation(
                code="halo_overcrowding",
                field="halo.halo_stone_count",
                message=f"{halo.halo_stone_count} accents leave {arc:.3f}mm of arc "
                f"each, below the {halo.halo_stone_diameter}mm accent diameter.",
                limit_mm=halo.halo_stone_diameter,
                actual_mm=arc,
            )
        ]
    return []


def _halo_web(spec: RingSpec) -> list[Violation]:
    """Too little metal BETWEEN adjacent halo seats. Accents that don't
    overlap can still leave a web far below the casting floor."""
    if spec.halo is None:
        return []
    halo = spec.halo
    offset = halo.halo_gap + halo.halo_stone_diameter / 2
    semi_minor = spec.stones.stone_diameter / 2
    semi_major = semi_minor * getattr(spec.stones, "length_ratio", 1.0)
    perimeter = _ring_perimeter(semi_minor + offset, semi_major + offset)
    arc = perimeter / halo.halo_stone_count
    needed = halo_min_arc(
        halo.halo_stone_diameter, MIN_WALL_MM, MIN_PRONG_TIP_MM
    )
    if arc < needed:
        web = arc - halo.halo_stone_diameter * HALO_WELL_BACK_RATIO
        return [
            Violation(
                code="halo_web",
                field="halo.halo_stone_count",
                message=f"{halo.halo_stone_count} accents leave {web:.3f}mm of "
                f"metal between adjacent seats, below the {MIN_WALL_MM}mm "
                f"minimum wall; at most {int(perimeter // needed)} accents fit.",
                limit_mm=needed,
                actual_mm=arc,
            )
        ]
    return []


def _trilogy_overcrowding(spec: RingSpec) -> list[Violation]:
    """Side stone close enough to collide with the centre stone.

    Placement uses the gap as an arc, but the stones are separated by the
    straight-line chord, which is shorter, so a positive gap can still overlap.
    """
    if spec.trilogy is None:
        return []
    trilogy = spec.trilogy
    shank = spec.shank
    # Side stones sit along the stone's long axis, so use the long half-width.
    stone_r = (spec.stones.stone_diameter / 2) * getattr(
        spec.stones, "length_ratio", 1.0
    )
    side_r = trilogy.side_stone_diameter / 2
    # Same head-radius formula as the builder (docs/adr/0002).
    profile = section_for(shank.outer_profile, shank.inner_profile)
    head_r = _section_head_r(
        shank.inner_diameter / 2, shank.band_thickness,
        effective_thickness_taper(spec), profile,
    )
    arc = stone_r + trilogy.side_stone_gap + side_r
    phi = arc / head_r
    chord = 2 * head_r * math.sin(phi / 2)
    min_clearance = stone_r + side_r
    if chord < min_clearance:
        return [
            Violation(
                code="trilogy_overcrowding",
                field="trilogy.side_stone_gap",
                message=f"Side stone placement leaves {chord:.3f}mm of clearance "
                f"to the centre stone, below the {min_clearance:.3f}mm needed "
                "for the two stones' girdles not to overlap.",
                limit_mm=min_clearance,
                actual_mm=chord,
            )
        ]
    return []


def _side_stone_overcrowding(spec: RingSpec) -> list[Violation]:
    """The accent row doesn't fit the shoulder, or adjacent accents collide.

    Checks (a) the row fits between its start angle and A_MAX, then (b) the
    straight-line gap between neighbours. Returns the first failure.
    """
    if spec.side_stone is None:
        return []
    ss = spec.side_stone
    shank = spec.shank
    # A side-stone band is flat; same head-radius formula as the builder.
    profile = section_for(shank.outer_profile, shank.inner_profile)
    band_outer_r = _section_head_r(
        shank.inner_diameter / 2, shank.band_thickness,
        effective_thickness_taper(spec), profile,
    )
    step = ss.accent_stone_diameter + ss.accent_gap
    dphi = math.degrees(step / band_outer_r)

    start_deg = side_stone_start_deg(spec, _SIDE_STONE_A_START_DEG)
    budget_deg = _SIDE_STONE_A_MAX_DEG - start_deg
    budget_arc = band_outer_r * math.radians(budget_deg)
    required_arc = (ss.accent_count_per_side - 1) * step
    if required_arc > budget_arc:
        return [
            Violation(
                code="side_stone_overcrowding",
                field="side_stone.accent_count_per_side",
                message=f"{ss.accent_count_per_side} accents per side need "
                f"{required_arc:.3f}mm of shoulder arc, above the "
                f"{budget_arc:.3f}mm available before the ring base.",
                limit_mm=budget_arc,
                actual_mm=required_arc,
            )
        ]

    chord = 2 * band_outer_r * math.sin(math.radians(dphi) / 2)
    min_clearance = ss.accent_stone_diameter
    if chord < min_clearance:
        return [
            Violation(
                code="side_stone_overcrowding",
                field="side_stone.accent_gap",
                message=f"Adjacent accents leave {chord:.3f}mm of clearance, "
                f"below the {min_clearance:.3f}mm needed for their girdles "
                "not to overlap.",
                limit_mm=min_clearance,
                actual_mm=chord,
            )
        ]
    return []


def _stone_curvature(spec: RingSpec) -> list[Violation]:
    """The girdle bends too sharply for the seat collar to follow it.

    A tube swept along a curve tighter than its own radius passes through
    itself. For an ellipse the tightest bend is at the tip: (short/2) / ratio.
    """
    stones = getattr(spec, "stones", None)
    if stones is None or getattr(stones, "shape", "round") == "round":
        return []
    ratio = getattr(stones, "length_ratio", 1.0)
    if ratio <= 1.0:
        return []
    profile = profile_for(stones.shape)
    # Cuts with corners get a bored seat, not a swept collar (docs/adr/0008).
    if profile.has_vertices:
        return []
    semi_minor = stones.stone_diameter / 2
    min_curvature = profile.min_curvature_radius(semi_minor, ratio)
    if min_curvature >= _SEAT_COLLAR_R:
        return []
    return [
        Violation(
            code="stone_curvature",
            field="stones.length_ratio",
            message=(
                f"The stone's tip curves with a {min_curvature:.3f}mm radius, "
                f"tighter than the {_SEAT_COLLAR_R:.2f}mm seat collar can "
                "follow without passing through itself. Reduce length_ratio or "
                "increase stone_diameter."
            ),
            limit_mm=_SEAT_COLLAR_R,
            actual_mm=min_curvature,
        )
    ]


def _side_stone_channel(spec: RingSpec) -> list[Violation]:
    """The band must be big enough to cut a channel into.

    (a) Width: the stone plus a wall each side. (b) Thickness: the groove must
    leave a floor, or it severs the band. Returns the first failure.
    """
    if spec.side_stone is None:
        return []
    ss = spec.side_stone
    shank = spec.shank

    needed_w = channel_band_width(ss.accent_stone_diameter, MIN_WALL_MM)
    if shank.band_width < needed_w:
        return [
            Violation(
                code="side_stone_channel_fit",
                field="shank.band_width",
                message=f"a {ss.accent_stone_diameter:.2f}mm channel accent "
                f"needs a {needed_w:.3f}mm band (stone + {MIN_WALL_MM}mm wall "
                f"each side); this band is {shank.band_width:.3f}mm.",
                limit_mm=needed_w,
                actual_mm=shank.band_width,
            )
        ]

    depth = channel_groove_depth(ss.accent_stone_height)
    needed_t = depth + MIN_WALL_MM
    if shank.band_thickness < needed_t:
        return [
            Violation(
                code="side_stone_channel_floor",
                field="shank.band_thickness",
                message=f"a {ss.accent_stone_height:.2f}mm accent cuts a "
                f"{depth:.3f}mm groove, needing a {needed_t:.3f}mm band to "
                f"leave {MIN_WALL_MM}mm of floor; this band is "
                f"{shank.band_thickness:.3f}mm.",
                limit_mm=needed_t,
                actual_mm=shank.band_thickness,
            )
        ]
    return []


def _cross_feature_overcrowding(spec: RingSpec) -> list[Violation]:
    """Two features must not occupy the same metal.

    Each feature reports the region it occupies (footprint.py), and one
    pairwise check covers any combination.
    """
    footprints = [
        (name, fp) for name, fp in (
            ("halo", halo_footprint(spec)),
            ("trilogy", trilogy_footprint(spec)),
        )
        if fp is not None
    ] + [
        ("side_stone", fp)
        for fp in side_stone_footprints(spec, _SIDE_STONE_A_START_DEG)
    ]
    violations = []
    for i, (name_a, fp_a) in enumerate(footprints):
        for name_b, fp_b in footprints[i + 1:]:
            # side_stone has one entry per shoulder; don't compare them.
            if name_a == name_b:
                continue
            if not _footprints_clear(fp_a, fp_b):
                violations.append(
                    Violation(
                        code="cross_feature_overcrowding",
                        field=f"{name_a}+{name_b}",
                        message=f"{name_a} and {name_b} do not clear each "
                        f"other by {MIN_WALL_MM}mm on this ring — they occupy "
                        "the same metal.",
                        limit_mm=MIN_WALL_MM,
                        actual_mm=None,
                    )
                )
    return violations


def validate_castability(spec: RingSpec) -> list[Violation]:
    """Run the full lost-wax gate; [] means the spec is castable."""
    return (
        _min_wall(spec)
        + _min_prong_tip(spec)
        + _geometric(spec)
        + _stone_curvature(spec)
        + _cross_feature_overcrowding(spec)
        + _halo_overcrowding(spec)
        + _halo_web(spec)
        + _trilogy_overcrowding(spec)
        + _side_stone_overcrowding(spec)
        + _side_stone_channel(spec)
    )


def is_castable(spec: RingSpec) -> bool:
    """True iff the spec produces no castability violations."""
    return not validate_castability(spec)
