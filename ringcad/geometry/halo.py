"""halo() — the halo composition module (RNG-9 CP3).

Rings N `accent_seat` beads at angles `theta_k = 2*pi*k/N` and N shared prongs at
the gap midpoints `theta_k + pi/N` on a `gallery`, fused into ONE watertight body.

Connectivity is watertight BY CONSTRUCTION, not by luck. OCCT booleans slice
cleanly through *transversal* overlaps but sliver / drop bodies on *tangential*
grazes of two curved surfaces, so every joint here is transversal or a deep
volumetric overlap — never a graze:

  1. The gallery rail is the backbone. Each `accent_seat`'s bearing cylinder
     plunges `RAIL_OVERLAP` into the 360 degree gallery rail tube, so the rail
     welds every seat into the continuous accent ring on its own. (An earlier
     design added a SECOND `Torus` bead-rail beside the seats; that curved-on-
     curved seat interface was the sole source of the CP3 non-manifold edges —
     it welded nothing the gallery rail didn't already weld, so it was removed.
     The gallery is CP3's sanctioned connectivity standard; one rail, not two.)

  2. Transversal prongs. Each shared prong joins the rail through a flat-faced
     `Box` FOOT buried in the rail-tube core (flat planes cut the torus along
     clean seams, exactly like the gallery's Box bridge struts). The visible claw
     is a tapered `Cone` that sits ABOVE the girdle, so no curved prong surface
     ever grazes the rail torus. The claw tip holds at the `MIN_PRONG_TIP` floor.

Local +Z setting frame laid onto the global +X head axis via `placement(c)` (the
one sanctioned map), applied last — identical contract to the CP2 primitives.
"""
from __future__ import annotations

import math

from build123d import Align, Box, Cone, Location, Pos

from ._common import (
    ACCENT_FUSE_EPS, MIN_PRONG_TIP, MIN_WALL, clamps, placement,
)
from .accent_seat import accent_seat
from .gallery import RAIL_MINOR, gallery

# Rail-top <-> seat-well vertical interpenetration (> ACCENT_FUSE_EPS): how deep
# every accent bearing plunges into the gallery rail tube, welding the seats.
RAIL_OVERLAP = 0.2
# Shared-prong claw base/tip radii: base = mult * tip, tapering to the tip floor.
PRONG_BASE_MULT = 2.0
# How far the prong Box foot plunges below the rail-tube centre into its core.
PRONG_PLUNGE = 0.3
# How far the Box foot rises above the girdle before the Cone claw begins, so the
# claw base never grazes the rail torus.
FOOT_RISE = 0.15
# Minimum visible claw rise above the foot (guarantees a positive-height claw on
# low settings where the girdle nearly meets the stone crown).
MIN_CLAW_RISE = 0.3


def _ring_angles(n: int) -> tuple[list[float], list[float]]:
    """The N seat angles + N shared-prong midpoint angles (radians).

    Seats sit at `2*pi*k/N`; each prong bisects the gap to the next seat
    (`+ pi/N`), so the last prong wraps closed between seat N-1 and seat 0.
    """
    seats = [2 * math.pi * k / n for k in range(n)]
    prongs = [theta + math.pi / n for theta in seats]
    return seats, prongs


def _prong(base_r: float, tip_r: float, foot_w: float, foot_h: float,
           claw_h: float, loc: Location):
    """One shared claw: a flat-faced Box foot (transversal join into the gallery
    rail core) topped by a tapered Cone claw that sits ABOVE the rail. Authored at
    the local origin (foot base at z=0), placed by rigid `loc` applied last."""
    _MIN = (Align.CENTER, Align.CENTER, Align.MIN)
    foot = Box(foot_w, foot_w, foot_h, align=_MIN)
    # Overlap the claw base into the foot so the local fuse is volumetric.
    claw = Pos(0, 0, foot_h - ACCENT_FUSE_EPS) * Cone(
        base_r, tip_r, claw_h + ACCENT_FUSE_EPS, align=_MIN
    )
    return loc * foot.fuse(claw)


def halo_parts(spec, c: dict | None = None) -> list:
    """The halo's leaf solids UN-fused: [gallery, *seats, *prongs].

    `compose` fuses these leaves alongside the center modules' leaves in ONE
    general fuse. A single general fuse over many small solids is robust where
    iterative pairwise fusing of pre-fused COMPOUNDS is not: OCCT silently drops
    a boolean when a heavy pre-fused body (the whole halo) meets the center's
    swept claws, but resolves all interpenetrations cleanly when they enter the
    same fuse as loose parts (RNG-17 risk #1). The gallery is itself a fused
    sub-solid -- that pre-fusion is fine; only the FULL-halo pre-fusion breaks
    the downstream center fuse.
    """
    c = c if c is not None else clamps(spec)
    accent_r = spec.halo.halo_stone_diameter / 2
    height = spec.halo.halo_stone_height
    n = spec.halo.halo_stone_count

    R = c["stone_r"] + spec.halo.halo_gap + accent_r
    seat_z = c["ring_z"]
    depth = max(0.5 * height, MIN_WALL)
    rail_top_z = seat_z - depth + RAIL_OVERLAP
    hub_r = max(c["stone_r"] * 0.20, MIN_WALL) * 1.1
    rail_z = rail_top_z - RAIL_MINOR

    place = placement(c)
    seats, prongs = _ring_angles(n)

    # Prong geometry: Box foot buried from the rail core up past the girdle,
    # tapered Cone claw above it (never touching the rail torus).
    tip_r = MIN_PRONG_TIP / 2
    base_r = tip_r * PRONG_BASE_MULT
    foot_w = 2 * base_r
    prong_base_z = rail_z - PRONG_PLUNGE
    foot_top_z = seat_z + FOOT_RISE
    prong_top_z = max(seat_z + 0.5 * height, foot_top_z + MIN_CLAW_RISE)
    foot_h = foot_top_z - prong_base_z
    claw_h = prong_top_z - foot_top_z

    #   (1) Gallery rail backbone: every accent seat's bearing plunges RAIL_OVERLAP
    #       into the gallery rail tube, welding the ring — one rail, no bead-rail.
    #   (2) Transversal prongs: each Box-footed claw buried in the rail-tube core.
    parts = [gallery(R, rail_top_z, hub_r, loc=place)]
    for theta in seats:
        seat_loc = place * Pos(R * math.cos(theta), R * math.sin(theta), seat_z)
        parts.append(accent_seat(accent_r, height, seat_loc))
    for theta_m in prongs:
        loc = place * Pos(
            R * math.cos(theta_m), R * math.sin(theta_m), prong_base_z
        )
        parts.append(_prong(base_r, tip_r, foot_w, foot_h, claw_h, loc))
    return parts


def halo(spec, c: dict | None = None):
    """Accent ring + shared prongs on a gallery for a HaloSpec -> one fused solid.

    Fuses `halo_parts` into a single body via one general fuse (the standalone
    builder + fast-loop contract). `compose` bypasses this and fuses the leaves
    directly, for the cross-module robustness `halo_parts` documents.
    """
    parts = halo_parts(spec, c)
    return parts[0].fuse(*parts[1:])
