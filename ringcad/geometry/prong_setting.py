"""prong_setting() — gallery peg + N prong claws (the peg/claw portion of the
spike's `_setting_solids`, with the seat torus split out into `seat.py`).

The peg + claw nodes/segments are authored in a local +Z frame then laid onto
the global +X head axis via the shared placement transform — identical to the
spike so the fused solid is unchanged.
"""
from __future__ import annotations

import math

from build123d import Align, Cone, Pos, Sphere, Vector

from ringcad.ringspec import RingSpec
from ringcad.ringspec.cuts import ProngType

from ._common import (
    MIN_PRONG_TIP, MIN_WALL, body_solid, clamps, placement,
)

# How far each claw segment is extended PAST its end nodes, so its rim sits
# inside the node spheres rather than tangent to them. Far below anything the
# viewer or the STL resolves, and it changes no designed radius.
NODE_OVERLAP = 0.03

# How far each arm of a V-prong reaches back along the girdle from the vertex
# it wraps, as a fraction of that vertex's own reach from centre, with a floor
# in units of the claw's wire radius so a small stone still gets a V that reads
# as one rather than as a thickened claw.
#
# **Ours, and the spec says so.** The V-prong's WRAP ANGLE is not a choice --
# it is whatever the outline's own girdle does either side of the vertex, which
# is why the arms are found by walking the girdle rather than by rotating a
# bisector through a guessed angle. The wrap LENGTH has no published trade
# figure (see specs/RNG-33.md, "Invented"), so it is pinned to the metal's own
# scale and the next reader may move it freely.
V_ARM_REACH_FRACTION = 0.28
V_ARM_REACH_FLOOR = 2.2          # x wire_r

# Raised from 0.20 in the 2026-08-24 research pass, and NOT for looks. Giving
# the pear a convex wing (see `PearProfile`) flattens the girdle either side of
# its point, which narrows the angle the two arms of the V leave at. Below a
# certain fork angle the arms lie against each other and OCCT resolves the
# node sphere's tangency as a crack rather than a surface: measured at
# length_ratio 2.10, 15 non-manifold edges in a single watertight-reporting
# body, every one of them within 0.001mm of the tip's node sphere equator --
# the exact tangency failure RNG-19 documents in the claw comment below.
#
# 0.26 is where it clears; 0.28 is that with margin, and 0.32 is also clean, so
# this is a floor with room above it rather than a fitted value. Marquise and
# emerald are unaffected either way -- their forks were already wide enough.

# How far a tip leans in over the stone, as a fraction of its girdle reach.
# The round setting's original figure, now shared by every tip including a
# V-prong's two arms.
TIP_LEAN = 0.88

# Widest polar sweep the girdle walk will consider when looking for an arm end.
# Comfortably past any arm length the fraction above can ask for, and short of
# the neighbouring prong on every cut in the catalogue.
_WALK_LIMIT = math.pi / 3


def _along_girdle(outline, theta: float, reach: float, sign: int) -> float:
    """The girdle ANGLE `reach` mm (straight-line) from the vertex at `theta`,
    walking in direction `sign`.

    Found by walking the OUTLINE rather than by rotating the vertex normal
    through some wrap angle, and that is the whole point: on a marquise or a
    pear the two runs meeting at a point are ARCS, so a V built off a rotated
    bisector would lift away from the stone the further out it reached. Walking
    the girdle makes the wrap angle a consequence of the cut's own geometry --
    the one thing specs/RNG-33.md insists must not be guessed -- and needs no
    new method on `StoneOutline`, which is what keeps the round and oval
    outlines free of a code path nothing calls (docs/adr/0002).

    Bisection rather than a closed form because `frame_at` is all the protocol
    offers, and chord distance from the vertex rises monotonically with polar
    offset over `_WALK_LIMIT` on every outline in the catalogue.
    """
    vertex, _ = outline.frame_at(theta)
    lo, hi = 0.0, _WALK_LIMIT
    for _ in range(40):
        mid = (lo + hi) / 2
        p, _ = outline.frame_at(theta + sign * mid)
        if (p - vertex).length < reach:
            lo = mid
        else:
            hi = mid
    return theta + sign * hi


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
    for theta, kind in outline.placements(int(c["prong_n"])):
        point, _ = outline.frame_at(theta)
        radial = Vector(point.X, point.Y, 0).normalized()
        reach_r = Vector(point.X, point.Y, 0).length

        A = radial * base_r
        B = Vector(point.X, point.Y, ring_z)
        # A V-prong lays one arm back along each of the two girdle runs that
        # meet at the vertex, so the tips are a LIST and a claw is simply the
        # one-tip case.
        if kind is ProngType.V:
            arm = max(V_ARM_REACH_FLOOR * wire_r,
                      V_ARM_REACH_FRACTION * reach_r)
            # Each arm leans in along the girdle's OWN outward normal, not
            # along the radial. On a circle those are the same direction, which
            # is why the claw below can keep the literal 0.88 the round setting
            # has always used; at a point they are not, and leaning both arms
            # radially pulls them TOGETHER -- measured, a marquise V closed from
            # a 100 degree girdle wedge to a 33 degree fork and a pear's to 17,
            # which is two rods lying against each other rather than a V.
            lean = (1 - TIP_LEAN) * reach_r
            tips = []
            for sign in (1, -1):
                end, out = outline.frame_at(
                    _along_girdle(outline, theta, arm, sign))
                tips.append(Vector(end.X - out.X * lean,
                                   end.Y - out.Y * lean,
                                   ring_z + claw_rise))
        else:
            # The tip leans inward over the stone: pull it along the radial by
            # the same 0.88 fraction the round setting used.
            tip_xy = radial * (reach_r * TIP_LEAN)
            tips = [Vector(tip_xy.X, tip_xy.Y, ring_z + claw_rise)]

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
        node_r = wire_r * 0.92
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
        #
        # A V's two arms are therefore built as two COMPLETE claw chains that
        # share a shaft, never as a fan of cones off one node. Fanning is the
        # same construction on paper and is not the same construction in OCCT:
        # measured, the seven-part n-ary fuse of a fan silently DROPPED a whole
        # arm on ONE of a marquise's two mirror-image V-prongs (4.866mm3 against
        # its twin's 6.524) -- watertight, single-solid, no warning, no error,
        # and asymmetric on a symmetric stone. Fusing two proven chains gives
        # 7.961 for both. docs/adr/0005, third sighting.
        chains = []
        for t in tips:
            nodes = [(A, wire_r), (B, node_r), (t, tip_r)]
            edges = [(A, wire_r, B, node_r), (B, node_r, t, tip_r)]
            sub = [Pos(*v) * Sphere(r) for v, r in nodes]
            sub += [body_solid(*e) for e in edges]
            chains.append(sub[0].fuse(*sub[1:]))
        parts = chains
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
