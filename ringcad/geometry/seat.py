"""seat() — the open seat ring (torus) at the girdle.

Split out of the spike's `_setting_solids`: the same `Torus(stone_r, collar_tr)`
authored in the local +Z frame and laid onto the global +X head axis via the
shared placement transform, so it lands identically to the peg/claws.
"""
from __future__ import annotations

from build123d import Pos

from ringcad.ringspec import RingSpec

from ._common import MIN_WALL, clamps, placement


def seat(spec: RingSpec, c: dict | None = None):
    """Seat collar following the stone's girdle → one build123d solid.

    The collar is whatever tube the outline says: a `Torus` for a round stone
    (unchanged from RNG-15), a swept ellipse for an oval. `seat` itself stays
    shape-blind.
    """
    c = c if c is not None else clamps(spec)
    ring_z = c["ring_z"]
    collar_tr = max(MIN_WALL / 2, 0.45)
    local = Pos(0, 0, ring_z) * c["outline"].tube(collar_tr)
    return placement(c) * local
