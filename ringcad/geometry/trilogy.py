"""trilogy() -- the trilogy composition module (RNG-10 CP2).

Places two symmetric side settings (`accent_seat` + 4 `accent_prong` each) on
the shank shoulder flanking the centre stone, each tied to the shank via a
short gallery-post pedestal -- the gallery's HUB alone (specs/RNG-10.md
Decision 2), not the full rail+hub+bridges gallery: a single flanking stone
has no ring to carry a rail around.

Connectivity is watertight BY CONSTRUCTION: the post shares its axis with the
side accent_seat's own bearing cylinder above it, so their overlap is a
genuine axial (not tangential) interpenetration; its base embeds deep into
the shank band -- a transversal plunge, never a tangent graze (the CP3
non-manifold trap this project has hit before).

Local +Z setting frame laid onto the global +X head axis via `placement(c)`,
rotated by the derived angular offset (Decision 4) -- the same contract as
the CP2 accent primitives and the CP3 halo/gallery modules.
"""
from __future__ import annotations

import math

from build123d import Align, Cylinder, Location, Pos, Rot

from ._common import ACCENT_FUSE_EPS, MIN_WALL, clamps, placement
from .accent_prong import accent_prong
from .accent_seat import accent_seat

# Side-prong count: fixed at 4 for v1 (specs/RNG-10.md Decision 1), not a field.
SIDE_PRONG_COUNT = 4
# Post radius: a fixed construction margin off MIN_WALL, independent of
# side_stone_gap (Decision 2/5) -- mirrors the gallery hub's wall discipline.
POST_R = max(MIN_WALL * 1.1, 0.9)
# How far the post embeds into the shank band below the shoulder surface (>>
# ACCENT_FUSE_EPS; comfortably inside even the thinnest in-range band).
POST_EMBED = 0.5
# How far the post's top plunges past the accent seat's bearing floor -- a
# true transversal overlap, not a graze.
POST_OVERLAP = 0.2


def _side_loc(spec, c: dict, sign: float) -> Location:
    """Rigid placement for one side setting: `placement(c)` rotated by the
    derived angular offset (specs/RNG-10.md Decision 4). `sign` is +1.0/-1.0."""
    stone_r = c["stone_r"]
    side_r = spec.trilogy.side_stone_diameter / 2
    phi = (stone_r + spec.trilogy.side_stone_gap + side_r) / c["head_r"]
    return Rot(0, 0, sign * math.degrees(phi)) * placement(c)


def _side_locs(spec, c: dict, sign: float) -> tuple[Location, list[Location]]:
    """One side's `(seat_loc, [prong_locs])`, shared by the builder and
    `_castability.check_trilogy` so build and check never drift apart."""
    side_r = spec.trilogy.side_stone_diameter / 2
    seat_loc = _side_loc(spec, c, sign) * Pos(0, 0, c["ring_z"])
    prong_locs = []
    for k in range(SIDE_PRONG_COUNT):
        ang = math.radians(k * 360.0 / SIDE_PRONG_COUNT)
        prong_locs.append(seat_loc * Pos(
            side_r * math.cos(ang), side_r * math.sin(ang), -ACCENT_FUSE_EPS
        ))
    return seat_loc, prong_locs


def _side_parts(spec, c: dict, sign: float) -> list:
    """One side setting's leaves: `[post, seat, *prongs]` -- UN-fused."""
    side_r = spec.trilogy.side_stone_diameter / 2
    height = spec.trilogy.side_stone_height
    seat_loc, prong_locs = _side_locs(spec, c, sign)

    depth = max(0.5 * height, MIN_WALL)
    post_top = c["ring_z"] - depth + POST_OVERLAP
    post_h = post_top + POST_EMBED
    post = _side_loc(spec, c, sign) * Pos(0, 0, -POST_EMBED) * Cylinder(
        POST_R, post_h, align=(Align.CENTER, Align.CENTER, Align.MIN)
    )

    parts = [post, accent_seat(side_r, height, seat_loc)]
    for prong_loc in prong_locs:
        parts.append(accent_prong(side_r, height, prong_loc))
    return parts


def trilogy_parts(spec, c: dict | None = None) -> list:
    """The trilogy's leaf solids UN-fused: `[post_l, seat_l, *prongs_l,
    post_r, seat_r, *prongs_r]` -- both sides symmetric about the centre.

    `compose` fuses these leaves alongside the centre modules' leaves in ONE
    general fuse (the RNG-17/halo robustness lesson: never hand `compose` a
    pre-fused compound for a heavy module).
    """
    c = c if c is not None else clamps(spec)
    return _side_parts(spec, c, -1.0) + _side_parts(spec, c, 1.0)


def trilogy(spec, c: dict | None = None):
    """Both side settings for a TrilogySpec -> one fused solid."""
    parts = trilogy_parts(spec, c)
    return parts[0].fuse(*parts[1:])
