"""prong_setting() — gallery peg + N prong claws (the peg/claw portion of the
spike's `_setting_solids`, with the seat torus split out into `seat.py`).

The peg + claw nodes/segments are authored in a local +Z frame then laid onto
the global +X head axis via the shared placement transform — identical to the
spike so the fused solid is unchanged.
"""
from __future__ import annotations

from build123d import Align, Cone, Pos, Sphere, Vector

from ringcad.ringspec import RingSpec

from ._common import (
    MIN_PRONG_TIP, MIN_WALL, body_solid, clamps, placement,
)


def prong_setting(spec: RingSpec, c: dict | None = None):
    """Gallery peg + claws for a RingSpec → one fused build123d solid."""
    c = c if c is not None else clamps(spec)
    ring_z, claw_rise = c["ring_z"], c["claw_rise"]
    outline = c["outline"]
    wire_r = max(MIN_WALL / 2 + 0.1, 0.5)
    tip_r = max(MIN_PRONG_TIP / 2, 0.4)
    # Peg radius is a SCALE value, not a girdle-following one, so it still comes
    # from the short-axis half-width rather than from the outline.
    base_r = max(c["stone_r"] * 0.20, MIN_WALL)

    local = []
    peg_h = max(ring_z * 0.4, 1.0) + 0.4
    local.append(Cone(base_r + wire_r, base_r, peg_h,
                      align=(Align.CENTER, Align.CENTER, Align.MIN)))
    # One claw per outline-chosen angle. Each claw runs peg -> girdle -> tip, so
    # its nodes are built AT the girdle point rather than at a fixed radius and
    # rotated: on an ellipse the reach varies with angle. For a round outline the
    # points are exactly the old `Rot(0, 0, i * 360/n)` positions.
    for theta in outline.prong_angles(int(c["prong_n"])):
        point, _ = outline.frame_at(theta)
        radial = Vector(point.X, point.Y, 0).normalized()
        girdle_r = Vector(point.X, point.Y, 0).length

        A = radial * base_r
        B = Vector(point.X, point.Y, ring_z)
        C = Vector(point.X, point.Y, ring_z + claw_rise * 0.55)
        # The tip leans inward over the stone: pull it along the radial by the
        # same 0.88 fraction the round setting used.
        tip_xy = radial * (girdle_r * 0.88)
        D = Vector(tip_xy.X, tip_xy.Y, ring_z + claw_rise)

        nodes = [(A, wire_r), (B, wire_r), (C, wire_r * 0.92),
                 (D, tip_r * 1.45)]
        edges = [(A, wire_r, B, wire_r), (B, wire_r, C, wire_r * 0.92),
                 (C, wire_r * 0.92, D, tip_r)]
        parts = [Pos(*v) * Sphere(r) for v, r in nodes]
        parts += [body_solid(*e) for e in edges]
        # Fuse each claw on its own FIRST. A single n-ary fuse over every node and
        # segment of every claw can fail silently in OCCT -- not raising, not
        # producing open edges, but quietly DROPPING bodies: a 6-prong oval at
        # length_ratio 1.3 came back as the bare peg (volume 5.65 against an
        # expected 39.02) while still reporting watertight with zero non-manifold
        # edges. Fusing claw-by-claw and then into the peg keeps each boolean
        # small enough to survive, and is bit-identical on every configuration
        # that already worked.
        local.append(parts[0].fuse(*parts[1:]))

    place = placement(c)
    solids = [place * s for s in local]
    out = solids[0]
    for s in solids[1:]:
        out = out.fuse(s)
    return out
