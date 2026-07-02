"""accent_prong() — a single small closed prong (shaft cylinder + domed tip).

RNG-9 CP2 accent primitive. Authored in a LOCAL +Z frame with the shaft base at
z=0 rising to a rounded tip at z=height, then laid into place by a caller-supplied
rigid `loc` applied LAST (`loc * local`). `loc` is rigid (rot+trans only) so
`check_accent_prong` can undo it exactly.

Unlike the center claw bodies (`_common.body_solid`, an OPEN cone), the shaft is
a CLOSED `Cylinder`; the tip sphere overlaps it by `_EPS` so the single `fuse`
yields one watertight B-rep body by construction.
"""
from __future__ import annotations

from build123d import Align, Cylinder, Location, Pos, Sphere

from ._common import ACCENT_FUSE_EPS as _EPS, MIN_PRONG_TIP


def accent_prong(accent_r: float, height: float, loc: Location):
    """One fused accent-prong solid, placed by rigid `loc`.

    Args:
        accent_r: accent stone radius (mm); nudges the shaft radius.
        height: prong height (mm) along local +Z.
        loc: rigid Location (rot+trans) applied last.
    """
    tip_r = MIN_PRONG_TIP / 2
    shaft_r = max(tip_r, accent_r * 0.18)

    shaft = Cylinder(
        shaft_r, height, align=(Align.CENTER, Align.CENTER, Align.MIN)
    )
    tip = Pos(0, 0, height - _EPS) * Sphere(tip_r)
    local = shaft.fuse(tip)
    return loc * local
