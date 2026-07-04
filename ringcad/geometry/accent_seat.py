"""accent_seat() — a single small stone seat bead (collar torus + bearing well).

RNG-9 CP2 accent primitive. Authored in a LOCAL +Z frame with the stone girdle
at z=0 and the seat well toward -Z, then laid into place by a caller-supplied
rigid `loc` applied LAST (`loc * local`). `loc` is a rigid Location (rotation +
translation only) — no scale/skew, so downstream `check_accent_seat` can undo it
exactly with `loc.inverse()`.

The collar torus tube and the bearing cylinder interpenetrate by `_EPS` (true
volumetric overlap, >> OCCT confusion, << MIN_WALL) so the single `fuse` returns
one watertight B-rep body by construction — the RNG-17 bar at accent scale.
"""
from __future__ import annotations

from build123d import Align, Cylinder, Location, Pos, Torus

from ._common import ACCENT_FUSE_EPS as _EPS, MIN_WALL


def accent_seat(accent_r: float, height: float, loc: Location):
    """One fused accent-seat solid, placed by rigid `loc`.

    Args:
        accent_r: accent stone radius (mm).
        height: accent stone height (mm); drives the bearing well depth.
        loc: rigid Location (rot+trans) applied last.
    """
    collar_tr = max(MIN_WALL / 2, 0.35)
    bearing_r = max(accent_r, collar_tr + _EPS)
    depth = max(0.5 * height, MIN_WALL)

    collar = Pos(0, 0, 0) * Torus(bearing_r, collar_tr)
    bearing = Pos(0, 0, _EPS) * Cylinder(
        bearing_r, depth, align=(Align.CENTER, Align.CENTER, Align.MAX)
    )
    local = collar.fuse(bearing)
    return loc * local
