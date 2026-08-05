"""side_stone() -- the channel-set accent row, built by SUBTRACTION (RNG-19 CP3).

Channel setting holds stones in a groove cut into the band between two walls,
with bearings cut into the walls' inner faces. There are NO prongs and NO
per-stone collar -- that is the definition of channel
(docs/jewelry-design-principles.md #Channel).

RNG-11 CP2 built the opposite: an `accent_seat` (a `Torus` collar deliberately
left proud of the band) at each stone, retained by two `Torus` rails sitting ON
the surface. That is correct halo geometry reused where its premise does not
hold, and it shipped because a real channel needs `accent_d + 2*MIN_WALL` =
3.1mm of band while real specs supply 2.0mm. `_side_stone_channel` now rejects
those bands rather than silently building the wrong setting on them.

**We render metal only, so the row IS the negative of its stones.** Rather than
model a setting, cut the band:

  1. the TRENCH -- a rectangular section revolved along the accent arc at the
     CLEAR span (`accent_d - 2*GIRDLE_PENETRATION`), so the walls left standing
     are the band's own metal;
  2. each STONE -- pavilion cone + crown cylinder at its girdle plane, at the
     stone's FULL radius. Being wider than the clear span, it bites
     GIRDLE_PENETRATION into either wall: **the bearings fall out of the
     subtraction, at the research's stated depth, for free.**

This is why CP3 is castable where an additive channel was not. ADR-0007's
tessellation cracking came from fusing near-tangent bodies; a cut has no
tangency to crack along (the stone tool overlaps the trench by 0.4mm, nowhere
near a sliver). Watertightness holds by construction: a cut cannot open a solid
unless it severs it, and `_side_stone_channel`'s floor rule forbids that.
"""
from __future__ import annotations

import math

from build123d import Axis, Cone, Cylinder, Align, Plane, Pos, Rectangle, Rot, revolve

from ringcad.ringspec.castability import _SIDE_STONE_A_START_DEG as A_START_DEG
from ringcad.ringspec.models import (
    GIRDLE_PENETRATION, GIRDLE_RECESS, PAVILION_FRACTION, channel_groove_depth,
)

from ._common import clamps

# How far every cutting tool is extended PAST the band's outer surface. The cut
# must break the surface cleanly rather than land tangent to it -- the inverse
# of ADR-0001's prefer-overlap rule, applied to subtraction.
CUT_OVERSHOOT = 0.5


def _band_outer_r(c: dict) -> float:
    return c["inner_r"] + c["bt"]


def _dphi_deg(spec, c: dict) -> float:
    """Angular pitch between adjacent accents (specs/RNG-11.md Decision 6)."""
    ss = spec.side_stone
    step = ss.accent_stone_diameter + ss.accent_gap
    return math.degrees(step / _band_outer_r(c))


def _accent_angles(spec, c: dict, sign: float) -> list[float]:
    """Ring-angles (deg) for one shoulder's accent row (Decision 6)."""
    count = spec.side_stone.accent_count_per_side
    dphi = _dphi_deg(spec, c)
    return [sign * (A_START_DEG + k * dphi) for k in range(count)]


def _trench_span(spec, c: dict, sign: float) -> tuple[float, float]:
    """One shoulder's trench arc (deg), padded past the first/last accent by
    the accent radius so the groove fully contains the end stones."""
    angles = _accent_angles(spec, c, sign)
    accent_r = spec.side_stone.accent_stone_diameter / 2
    pad = math.degrees(accent_r / _band_outer_r(c))
    lo, hi = min(angles) - pad, max(angles) + pad
    return lo, hi


def _trench(spec, c: dict, lo_deg: float, hi_deg: float):
    """The channel groove: a rectangular section revolved about the ring axis
    over `[lo_deg, hi_deg]`.

    Revolve (not `Torus`) because the trench's width and depth are independent
    -- width is the stones' clear span, depth is their pavilion -- whereas a
    torus couples both to one minor radius. `revolve` sweeps counter-clockwise
    from global +X, the same convention `Rot(0, 0, angle)` uses for placement.
    """
    ss = spec.side_stone
    clear_w = ss.accent_stone_diameter - 2 * GIRDLE_PENETRATION
    depth = channel_groove_depth(ss.accent_stone_height)
    r_out = _band_outer_r(c)
    x0, x1 = r_out - depth, r_out + CUT_OVERSHOOT
    section = Plane.XZ * Pos((x0 + x1) / 2, 0) * Rectangle(x1 - x0, clear_w)
    return Rot(0, 0, lo_deg) * revolve(
        section, Axis.Z, revolution_arc=hi_deg - lo_deg
    )


def _stone_cut(spec, c: dict, angle_deg: float):
    """One stone's own volume, removed from the band.

    Authored in a local +Z-radially-outward frame (the shared `Rot(0, 90, 0)`
    convention) with the girdle at z=0: a pavilion cone below, and a crown
    cylinder above that breaks out through the band's surface. At the stone's
    FULL radius against the trench's clear span, this is what cuts the bearing
    into each wall's inner face.
    """
    ss = spec.side_stone
    accent_r = ss.accent_stone_diameter / 2
    pavilion = PAVILION_FRACTION * ss.accent_stone_height
    rise = GIRDLE_RECESS + CUT_OVERSHOOT

    crown = Cylinder(accent_r, rise, align=(Align.CENTER, Align.CENTER, Align.MIN))
    pav = Cone(
        accent_r, 0.0, pavilion,
        align=(Align.CENTER, Align.CENTER, Align.MAX),
    )
    local = crown.fuse(pav)
    r = _band_outer_r(c) - GIRDLE_RECESS
    return Rot(0, 0, angle_deg) * Pos(r, 0, 0) * Rot(0, 90, 0) * local


def side_stone_cuts(spec, c: dict | None = None) -> list:
    """Every solid the channel removes from the band, both shoulders:
    `[trench_l, *stones_l, trench_r, *stones_r]`.

    `compose` subtracts these AFTER its single general fuse, so the trench is
    cut from the finished band rather than from a loose shank leaf.
    """
    c = c if c is not None else clamps(spec)
    out = []
    for sign in (-1.0, 1.0):
        lo, hi = _trench_span(spec, c, sign)
        out.append(_trench(spec, c, lo, hi))
        out += [_stone_cut(spec, c, a) for a in _accent_angles(spec, c, sign)]
    return out


def side_stone(spec, c: dict | None = None):
    """The channel's NEGATIVE volume as one fused solid.

    Deliberately not "the side-stone band": this module contributes no metal.
    It exists so the module interface still has a solid to hand `check_side_stone`
    and to volume-check for degeneracy.
    """
    cuts = side_stone_cuts(spec, c)
    return cuts[0].fuse(*cuts[1:])
