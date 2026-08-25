"""seat() — the open seat ring (torus) at the girdle.

Split out of the spike's `_setting_solids`: the same `Torus(stone_r, collar_tr)`
authored in the local +Z frame and laid onto the global +X head axis via the
shared placement transform, so it lands identically to the peg/claws.
"""
from __future__ import annotations

from build123d import Pos

from ringcad.ringspec import RingSpec

from ._common import SEAT_COLLAR_R, clamps, placement


def seat(spec: RingSpec, c: dict | None = None):
    """Seat collar following the stone's girdle → one build123d solid.

    The collar is whatever the OUTLINE says, because how a seat is made depends
    on the girdle: a `Torus` for a round stone (unchanged from RNG-15), a swept
    ellipse for an oval, and for a cornered or pointed cut a bearing plate with
    the stone's own negative bored out of it (RNG-33, docs/adr/0008 -- a vertex
    has no radius, so a swept collar self-intersects at ANY section radius).

    `seat` itself stays shape-blind, which is the whole point of the seam.
    """
    c = c if c is not None else clamps(spec)
    ring_z = c["ring_z"]
    collar_tr = SEAT_COLLAR_R
    local = Pos(0, 0, ring_z) * c["outline"].seat_solid(collar_tr)
    return placement(c) * local
