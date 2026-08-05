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

# How far each claw segment is extended PAST its end nodes, so its rim sits
# inside the node spheres rather than tangent to them. Far below anything the
# viewer or the STL resolves, and it changes no designed radius.
NODE_OVERLAP = 0.03


def _seg(p, r_p, q, r_q):
    """One claw segment, extended `NODE_OVERLAP` past both nodes.

    Radii are extrapolated along the same taper so the cone's profile through
    the original nodes is exactly `r_p` -> `r_q`; only the stubs poking into the
    node spheres lie outside that span.
    """
    axis = q - p
    length = axis.length
    u = axis.normalized()
    slope = (r_q - r_p) / length
    d = NODE_OVERLAP
    return (p - u * d, r_p - slope * d, q + u * d, r_q + slope * d)


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

        # RNG-19: radii step DOWN continuously from base to tip, and each node's
        # sphere matches the radius of the cones meeting there. Previously every
        # node carried the same `wire_r` and the tip node was `tip_r * 1.45` —
        # a ball WIDER than its own shaft, so the claw was thickest at the one
        # place a real claw is thinnest. Cross-sections up the length ran
        # 4.58 / 4.18 / 3.80 / 4.71 / 6.32 mm2: a taper, then a balloon.
        #
        # The base radius is unchanged: ~1.0mm diameter is already correct trade
        # practice (docs/jewelry-design-principles.md), so this sheds metal from
        # the upper claw rather than adding any.
        girdle_r = wire_r * 0.92
        nodes = [(A, wire_r), (B, girdle_r), (D, tip_r)]
        # Node radii EQUAL the cone radii meeting there, and the mid node is
        # gone: the claw is base -> girdle -> tip, which is what a cast claw
        # actually does (grip at the girdle, then fold over the stone).
        #
        # The equal radii are load-bearing, not incidental. A sphere whose radius
        # matches its cone's rim is TANGENT, and OCCT merges the two surfaces
        # into one smooth face. Give them a genuine intersection -- by thinning
        # the cone radially OR by extending it past the node -- and the B-rep
        # stays valid and single-solid while the STL tessellator cracks along the
        # intersection circles (measured: 265 non-manifold edges off a perfectly
        # valid 74-face B-rep; nearly the whole parameter grid once every joint
        # had one). So this construction DEPENDS on tangency to tessellate, and
        # the way to make it robust is fewer joints, not better-overlapped ones.
        #
        # Dropping the mid node also removes the joint that actually failed: with
        # the old oversized tip ball gone (1.16mm across a 0.92mm gap at a 2mm
        # stone, which welded all six claws into a ring), the mid joint lost its
        # redundant connection and OCCT resolved that one tangency as a seam,
        # splitting a claw's upper half off as its own solid -- watertight, and
        # still wrong (docs/adr/0005).
        edges = [(A, wire_r, B, girdle_r), (B, girdle_r, D, tip_r)]
        parts = [Pos(*v) * Sphere(r) for v, r in nodes]
        parts += [body_solid(*e) for e in edges]
        # Pre-fuse each claw into ONE body before the final fuse. A single n-ary
        # fuse over every node and segment of every claw at once can fail silently
        # in OCCT -- not raising, not producing open edges, but quietly DROPPING
        # bodies: a 6-prong oval at length_ratio 1.3 came back as the bare peg
        # (volume 5.65 against an expected 39.02) while still reporting watertight
        # with zero non-manifold edges. See docs/adr/0005.
        #
        # Per-claw grouping is the module's own internal pre-fusion, which
        # docs/adr/0001 sanctions; what that ADR forbids -- pairwise-fusing
        # pre-fused bodies one at a time -- is avoided by the single general fuse
        # below. Both orderings give identical volumes; this one keeps to the ADR.
        local.append(parts[0].fuse(*parts[1:]))

    place = placement(c)
    solids = [place * s for s in local]
    return solids[0].fuse(*solids[1:])
