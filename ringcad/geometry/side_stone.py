"""side_stone() -- the side-stone (channel) composition module (RNG-11 CP2).

Places a symmetric row of `accent_seat` beads down each shoulder of the shank
(Decision 6 in specs/RNG-11.md), retained by two continuous channel-wall rails
per shoulder -- NO `accent_prong` (Decision 3: channel retention holds stones
with walls, not claws) and NO `gallery` (Decision 4: connectivity is a weld
THROUGH the shank, not an elevated post/rail).

Both the seats and the walls are placed using the shank's NOMINAL (untapered)
outer radius/width (`c["inner_r"] + c["bt"]`, `c["bw"]`) -- the same
approximation `_side_stone_overcrowding` uses (CP1). Because the shank tapers
WIDER approaching the head (`_common._head_t`), the nominal values are a
conservative lower bound everywhere the accent row actually sits (A_START..
A_MAX, both comfortably short of the head-opposite thinnest point) -- so a
placement embedded relative to the nominal surface is always embedded at least
that much into the TRUE (thicker) local band, never floating clear of it.

Each seat's bearing plunges radially inward from the nominal outer surface (a
deep volumetric overlap, not a tangent graze -- the recurring OCCT
non-manifold trap); each wall is a partial `Torus` arc (major_angle < 360)
spanning its shoulder's accent row, embedded into the band the same way.
"""
from __future__ import annotations

import math

from build123d import Location, Pos, Rot, Torus

from ringcad.ringspec.castability import _SIDE_STONE_A_START_DEG as A_START_DEG

from ._common import MIN_WALL, clamps
from .accent_seat import accent_seat

# Fixed construction margin embedding a seat's local z=0 (girdle plane) inside
# the nominal outer band surface -- guarantees genuine volumetric overlap with
# the (always-at-least-as-thick) true local band, independent of accent_gap.
ACCENT_EMBED = 0.3

# Channel-wall rail tube minor radius -> wall = 2*WALL_MINOR ~= 0.9mm (> 0.8
# floor), the same margin discipline as gallery.RAIL_MINOR.
WALL_MINOR = max(MIN_WALL * 0.5, 0.45)
# Fixed embed depth for the wall rail's major radius (mirrors ACCENT_EMBED).
WALL_EMBED = 0.3


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


def _accent_loc(c: dict, angle_deg: float) -> Location:
    """Rigid placement for one accent seat: local +Z (radially outward, via
    the shared `Rot(0, 90, 0)` convention) embedded `ACCENT_EMBED` inside the
    nominal outer band surface, at ring-angle `angle_deg`."""
    r = _band_outer_r(c) - ACCENT_EMBED
    return Rot(0, 0, angle_deg) * Pos(r, 0, 0) * Rot(0, 90, 0)


def _wall_span(spec, c: dict, sign: float) -> tuple[float, float]:
    """One shoulder's wall arc span (deg), padded by the accent radius (arc
    length -> angle, same conversion `_dphi_deg` uses) past the first/last
    accent so the rails retain the end stones' girdles."""
    angles = _accent_angles(spec, c, sign)
    accent_r = spec.side_stone.accent_stone_diameter / 2
    pad = math.degrees(accent_r / _band_outer_r(c))
    lo, hi = min(angles) - pad, max(angles) + pad
    return lo, hi


def _wall(c: dict, lo_deg: float, hi_deg: float, z: float):
    """One channel-wall rail: a partial `Torus` arc over `[lo_deg, hi_deg]`,
    embedded `WALL_EMBED` inside the nominal outer band surface at width
    edge `z`.

    `align=None` is load-bearing: the default CENTER align re-centers a
    partial-angle Torus's (asymmetric) bounding box on the origin, which
    un-anchors the arc from the ring's actual center. `align=None` keeps the
    natural sweep, whose minor circle starts flush at ring-angle 0 (global
    +X) and revolves counter-clockwise by `major_angle` -- the same +X /
    counter-clockwise convention `_accent_loc`'s `Rot(0, 0, angle_deg)` uses.
    """
    r = _band_outer_r(c) - WALL_EMBED
    torus = Torus(r, WALL_MINOR, major_angle=hi_deg - lo_deg, align=None)
    return Pos(0, 0, z) * (Rot(0, 0, lo_deg) * torus)


def _shoulder_parts(spec, c: dict, sign: float) -> list:
    """One shoulder's leaves: `[*seats, wall_top, wall_bottom]` -- UN-fused."""
    height = spec.side_stone.accent_stone_height
    accent_r = spec.side_stone.accent_stone_diameter / 2
    seats = [
        accent_seat(accent_r, height, _accent_loc(c, a))
        for a in _accent_angles(spec, c, sign)
    ]
    lo, hi = _wall_span(spec, c, sign)
    z = c["bw"] / 2
    walls = [_wall(c, lo, hi, z), _wall(c, lo, hi, -z)]
    return seats + walls


def side_stone_parts(spec, c: dict | None = None) -> list:
    """The side-stone row's leaf solids UN-fused, both shoulders symmetric
    about the centre: `[*seats_l, wall_l_top, wall_l_bot, *seats_r,
    wall_r_top, wall_r_bot]`.

    `compose` fuses these leaves alongside the centre modules' leaves in ONE
    general fuse (the RNG-17/halo robustness lesson).
    """
    c = c if c is not None else clamps(spec)
    return _shoulder_parts(spec, c, -1.0) + _shoulder_parts(spec, c, 1.0)


def side_stone(spec, c: dict | None = None):
    """Both shoulders' accent rows + channel walls for a SideStoneSpec -> one
    fused solid."""
    parts = side_stone_parts(spec, c)
    return parts[0].fuse(*parts[1:])
