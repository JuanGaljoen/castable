"""Footprint — the shared currency for cross-feature castability (RNG-24 CP2).

Each feature answers ONE question: what annular sector (an angle range about
the ring axis, symmetric about the head at theta=0, plus a radial range) does
it occupy? One generic pairwise check (`clear`) then replaces a table of
per-pair special cases that would grow quadratically as features are added —
the same move ADR-0009 made for repair, applied here to composition.

**Spec-layer only, deliberately approximate.** `ringspec` cannot import
`geometry` (docs/adr/0002's boundary — a geometry-side copy of a spec-layer
fact is exactly the drift that ADR guards against), so a footprint cannot be
measured by building the real solid at validation time — castability runs
BEFORE geometry, and build123d generation costs seconds per ring, not
microseconds. Each formula below was instead measured ONCE, empirically,
against the real `compose()`d geometry during RNG-24 CP2's own development
(bounding-box corners converted to (r, theta) about the Z axis), then encoded
as a closed-form approximation in the SAME spec-layer style every other
`castability.py` check already uses (`_halo_overcrowding`'s `semi_minor`/
`semi_major` approximation of the true `StoneOutline`, `_trilogy_overcrowding`'s
`stone_r * length_ratio`). `SAFETY_MARGIN` widens each measured angular half-
width so the approximation is conservative — it may over-report a feature's
angular reach, never under-report it. Over-reporting costs a false rejection
(a future ticket's problem, if it ever bites); under-reporting would silently
ship colliding metal, which this checkpoint exists to prevent.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from ringcad.mesh_validator import MIN_WALL_MM

from .models import (
    HALO_PLATE_RIM, RingSpec, channel_groove_depth, effective_thickness_taper,
)
from .sections import head_r as _section_head_r
from .sections import section_for

# Measured against the real compose()d golden halo/trilogy (RNG-24 CP2): the
# naive head_r-based estimate under-reports a raised feature's true angular
# reach by up to ~25% (its nearest bounding-box corner sits closer to the axis
# than head_r, since gallery posts/plates are not flush with the head). This
# margin was sized so both measured cases clear with room, not tuned to either
# exactly.
SAFETY_MARGIN = 1.3


@dataclass(frozen=True)
class Footprint:
    """One feature's occupied annular sector. Angles in degrees, symmetric
    about the head (theta=0); radii in mm from the ring axis."""

    angle_start: float
    angle_end: float
    r_inner: float
    r_outer: float


def _head_r(spec: RingSpec) -> float:
    profile = section_for(spec.shank.outer_profile, spec.shank.inner_profile)
    return _section_head_r(
        spec.shank.inner_diameter / 2, spec.shank.band_thickness,
        effective_thickness_taper(spec), profile,
    )


def halo_footprint(spec: RingSpec) -> Footprint | None:
    """The halo plate's sector: symmetric about the head, standing off the
    band's surface up to roughly half the setting height (RNG-19 CP4's plate
    sits between the band and the centre stone's crown, never as tall as the
    full setting)."""
    if spec.halo is None:
        return None
    halo = spec.halo
    head_r = _head_r(spec)
    accent_r = halo.halo_stone_diameter / 2
    semi_major = (spec.stones.stone_diameter / 2) * getattr(
        spec.stones, "length_ratio", 1.0
    )
    # Matches _halo_overcrowding's own approximation of the plate's outer
    # radius: the stone's semi-major, expanded once by halo_gap + accent_r
    # (to the accent ring) and once more by accent_r + HALO_PLATE_RIM (to the
    # plate's outer rim) -- the tangential half-extent that projects onto the
    # ring's own angular coordinate (docs/geometry/outline.py's local-Y
    # convention: local Y is band-tangential).
    plate_y_half = semi_major + halo.halo_gap + 2 * accent_r + HALO_PLATE_RIM
    half_deg = math.degrees(plate_y_half / head_r) * SAFETY_MARGIN
    return Footprint(-half_deg, half_deg, head_r, head_r + spec.setting.setting_height / 2)


def trilogy_footprint(spec: RingSpec) -> Footprint | None:
    """The two side settings' sector: symmetric about the head, standing as
    tall as the centre setting (they ride the same gallery-post construction)."""
    if spec.trilogy is None:
        return None
    trilogy = spec.trilogy
    head_r = _head_r(spec)
    stone_r = (spec.stones.stone_diameter / 2) * getattr(
        spec.stones, "length_ratio", 1.0
    )
    side_r = trilogy.side_stone_diameter / 2
    phi = (stone_r + trilogy.side_stone_gap + side_r) / head_r
    half_deg = math.degrees(phi + side_r / head_r) * SAFETY_MARGIN
    return Footprint(-half_deg, half_deg, head_r, head_r + spec.setting.setting_height)


def side_stone_start_deg(spec: RingSpec, base_deg: float) -> float:
    """How far round the shank the channel row must start to clear whatever
    ELSE is sharing the head (RNG-24 CP2) -- `base_deg` is the row's own
    fixed clearance of the bare centre setting (castability.py's
    `_SIDE_STONE_A_START_DEG`), widened when a halo's plate reaches further
    round than the bare centre does. Trilogy occupies the same head region a
    side-stone row would also need to clear, but the two are not evidenced
    together (specs/RNG-24.md); widen for it too on the same principle rather
    than leave a silent gap the day someone combines them.
    """
    start = base_deg
    # A margin, not a bare touch: widening to exactly the other feature's own
    # angle_end would let the two footprints meet with zero clearance, which
    # `clear()` (correctly) still calls a collision. Convert MIN_WALL_MM to
    # degrees at head_r so the widened start clears by construction rather
    # than by chance.
    # 1.1x, not the bare MIN_WALL_MM conversion: landing exactly on the floor
    # is a coin flip against `clear()`'s own floating-point rounding, and this
    # widening is meant to guarantee clearance, not approach it.
    margin_deg = math.degrees(MIN_WALL_MM / _head_r(spec)) * 1.1
    for footprint in (halo_footprint(spec), trilogy_footprint(spec)):
        if footprint is not None:
            start = max(start, footprint.angle_end + margin_deg)
    return start


def side_stone_footprints(spec: RingSpec, base_start_deg: float) -> list[Footprint]:
    """The channel row's own sectors — ONE PER SHOULDER, never a single
    symmetric range spanning the gap between them.

    A row starts at `start_deg` on EACH side and never crosses the head, so
    the true occupied region is two disjoint arcs, not the single interval
    `[-end, +end]` — that single interval would wrongly swallow the head
    itself (and whatever else sits there, e.g. a halo) even though nothing is
    actually built in that middle gap. Found by measuring the golden
    halo + side_stone combination during CP2's own development: modelled as
    one interval, it reported a collision with EVERY halo regardless of
    size, since a halo centred on the head always falls inside
    `[-end, +end]`.
    """
    if spec.side_stone is None:
        return []
    ss = spec.side_stone
    head_r = _head_r(spec)
    start_deg = side_stone_start_deg(spec, base_start_deg)
    step = ss.accent_stone_diameter + ss.accent_gap
    dphi_deg = math.degrees(step / head_r)
    last_deg = start_deg + (ss.accent_count_per_side - 1) * dphi_deg
    pad_deg = math.degrees((ss.accent_stone_diameter / 2) / head_r)
    end_deg = last_deg + pad_deg
    depth = channel_groove_depth(ss.accent_stone_height)
    r_inner, r_outer = head_r - depth, head_r
    return [
        Footprint(start_deg, end_deg, r_inner, r_outer),
        Footprint(-end_deg, -start_deg, r_inner, r_outer),
    ]


def clear(a: Footprint, b: Footprint, min_wall_mm: float = MIN_WALL_MM) -> bool:
    """True iff two footprints are safely separated by at least `min_wall_mm`
    in EITHER dimension — collision needs overlap in both angle and radius,
    so clearance in either alone is enough.

    The angular gap converts to mm at the SMALLER of the two outer radii —
    the same radius gives a smaller arc for the same angle, so this is the
    conservative (safe) choice of denominator, not the exact one.
    """
    radial_gap = max(b.r_inner - a.r_outer, a.r_inner - b.r_outer)
    if radial_gap >= min_wall_mm:
        return True
    angular_gap_deg = max(b.angle_start - a.angle_end, a.angle_start - b.angle_end)
    if angular_gap_deg <= 0:
        return False
    r = min(a.r_outer, b.r_outer)
    return math.radians(angular_gap_deg) * r >= min_wall_mm
