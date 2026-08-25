"""prong_setting() — gallery peg + N prong claws (the peg/claw portion of the
spike's `_setting_solids`, with the seat torus split out into `seat.py`).

The peg + claw nodes/segments are authored in a local +Z frame then laid onto
the global +X head axis via the shared placement transform — identical to the
spike so the fused solid is unchanged.
"""
from __future__ import annotations

import math

from build123d import (
    Align, Cone, Cylinder, Face, Pos, Sphere, Vector, extrude,
)

from ringcad.ringspec import RingSpec
from ringcad.ringspec.cuts import ProngType

from ._common import (
    ACCENT_FUSE_EPS, MIN_PRONG_TIP, MIN_WALL, SEAT_COLLAR_R, body_solid,
    clamps, placement,
)
from .outline import GIRDLE_EMBED

# How far each claw segment is extended PAST its end nodes, so its rim sits
# inside the node spheres rather than tangent to them. Far below anything the
# viewer or the STL resolves, and it changes no designed radius.
NODE_OVERLAP = 0.03

# How far the V-cup reaches back along the girdle either side of the point it
# wraps, as a fraction of that point's own distance from centre, with a floor in
# units of the cup's own wall so a small stone still gets a cup wider than it is
# thick rather than a lump.
#
# **Ours, and unpublished.** Two research passes across eight angles found no
# figure for how far a V-tip wraps -- see docs/research/v-prong-wall-thickness.md
# and the pear/marquise note. The wrap ANGLE is not a choice, being whatever the
# girdle does either side of the vertex, but the wrap LENGTH is.
#
# Was 0.28 while the V was built as two cone arms: below a certain fork angle
# those arms lay against each other and OCCT cracked the node sphere's tangency,
# and widening the reach was what opened the fork. The cup construction has no
# arms and no node sphere at the point, so that constraint died with it -- 0.28
# was left behind as a saddle running a quarter of the way down the stone. At
# 0.15 the cup wraps ~15% of the length instead of ~28%, which is a V on the
# point rather than a collar around the end.
V_CUP_REACH_FRACTION = 0.15
V_CUP_REACH_FLOOR = 1.2          # x V_CUP_WALL

# The V-cup's metal, as ONE wall of one thickness positioned across the girdle
# -- not an outer thickness with a lip stacked on top of it.
#
# That distinction is the research finding, and it is structural rather than
# numeric (docs/research/v-prong-wall-thickness.md). No source publishes a V-tip
# wall thickness; two passes across eight angles agree, and the absence is the
# result rather than a gap to fill. What the sources DO show is how the closest
# analogue is made: a bezel -- which is what a V-cup is, a wall wrapping part of
# the girdle with an inward fold -- is ONE continuous strip at ONE gauge, folded
# over. Never a wall thickness plus a separately-sized lip added to it. We built
# it additively (0.65mm outside the girdle PLUS 0.30mm inside = 0.95mm) and it
# read as chunky, which no amount of tuning either number would have fixed.
#
# `V_CUP_WALL` is the TOTAL; `V_CUP_LIP` is how much of it sits inside the
# girdle as the retaining fold, so the outer face falls out as `WALL - LIP`.
#
# **0.70mm is the PRONG floor, not the wall floor.** A V-tip is a prong -- a
# discrete retaining feature -- rather than a structural wall, so MIN_PRONG_TIP
# governs it and MIN_WALL does not. That distinction is the only thing licensing
# a value below 0.80mm, and it is worth stating because the two floors are easy
# to confuse and only one applies here.
#
# It does not go lower. Stuller allows 0.2mm for polishing, so 0.70 modelled
# finishes near 0.50 -- already close to their 0.45mm prong minimum, and the
# reason specs/RNG-33.md set our tip floor at 0.70 rather than at theirs. The
# trade's own bezel gauges (28-24ga, 0.25-0.51mm) are thinner still, but those
# are hand-fabricated from sheet, not cast.
V_CUP_WALL = 0.70
V_CUP_LIP = 0.22

# How far the cup rises above the girdle, as a fraction of the claw rise. OURS,
# and unpublished like every other V-tip dimension. 0.70 puts it 1.75mm up
# against claws reaching 2.50mm: clearly a prong rather than a rim, without
# competing with the claws.
V_CUP_RISE = 0.70

# How far a CLAW's tip leans in over the stone, as a fraction of its girdle
# reach -- the round setting's original figure, unchanged since RNG-15. It no
# longer applies to a V, which is a cup wrapping the point rather than a tip
# folding over it.
TIP_LEAN = 0.88



def _v_cup(outline, theta: float, reach: float, ring_z: float,
           claw_rise: float):
    """The chevron cup that cradles a point, as metal minus the stone.

    One wall of `V_CUP_WALL`, straddling the girdle with `V_CUP_LIP` of it
    inside as the fold that retains the stone. Trimmed to a cylinder about the
    vertex so only the point is wrapped and the rest of the girdle is left to
    the claws.

    The outer face lands INSIDE the seat plate's rim, which also happens to be
    what keeps the boolean honest. An earlier version put it exactly flush with
    that rim, making the two the SAME surface -- and a coincident face is not a
    fuse OCCT can resolve: at length_ratio 2.50 it left a 0.0008mm3 lamina of
    357 faces and 205 non-manifold edges, every one just past the tip at the
    girdle plane. Thinning the wall removed the coincidence outright rather than
    nudging it apart with a tolerance.
    """
    vertex, _ = outline.frame_at(theta)
    base = ring_z - SEAT_COLLAR_R
    amount = SEAT_COLLAR_R + claw_rise * V_CUP_RISE
    outer = extrude(
        Face(outline.expanded(V_CUP_WALL - V_CUP_LIP).wire()), amount=amount)
    # Cut oversize in height so the bore breaks through both faces: a bore that
    # lands flush leaves a lid, and a lid here is a sealed void that still
    # reports watertight (docs/adr/0008's trap, docs/adr/0005's sibling).
    bore = extrude(Face(outline.expanded(-V_CUP_LIP).wire()), amount=amount + 1.0)
    wall = Pos(0, 0, base) * (outer - Pos(0, 0, -0.5) * bore)
    region = Pos(vertex.X, vertex.Y, base - 0.5) * Cylinder(
        reach, amount + 1.0, align=(Align.CENTER, Align.CENTER, Align.MIN))
    return wall & region


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
            # A V-prong is a CUP, not a fork. Built as the negative of the
            # stone's own point (docs/adr/0008 again): a wall of metal following
            # the girdle, rising out of the seat plate and folding inward over
            # the stone, kept only within reach of the vertex. In plan view that
            # is a chevron whose inside face IS the stone's outline, so the
            # point beds into it exactly.
            #
            # It replaced two tapering cones fanned off the girdle node. That
            # built a V in plan and read as a tuning fork in metal -- two rods
            # meeting in mid-air with nothing between them for the point to sit
            # ON, where a real V-tip is a solid trough the corner drops into.
            # Caught by looking at a render beside a photograph.
            reach = max(V_CUP_REACH_FLOOR * V_CUP_WALL,
                        V_CUP_REACH_FRACTION * reach_r)
            # No shaft. The cup welds into the seat plate, and the plate is
            # already carried to the peg by the CLAWS at the other placements --
            # every cut in the catalogue has at least one (a marquise at four
            # prongs is 2 V + 2 claws; emerald went to all-claws in CP4).
            #
            # It used to run one, and the shaft was where the pimple came from.
            # At a sharp point `expanded` under-offsets (RNG-40), so a pear's cup
            # front face sits only 0.288mm beyond the girdle against a nominal
            # 0.48 -- and the metal band there is THINNER THAN THE SHAFT, so
            # neither the claw's 0.460 node sphere (0.172mm proud) nor a 0.400
            # cone end could fit inside it. Aiming the shaft at the cup's centre
            # of mass instead of the girdle helped and did not fix it. The band
            # is the constraint, and the answer was that nothing needed to be
            # threaded through it.
            #
            # `test_a_v_prong_is_carried_by_the_seat_not_by_its_own_shaft` pins
            # the connectivity this leans on, so a future all-V cut fails loudly
            # rather than shipping in pieces.
            local.append(_v_cup(outline, theta, reach, ring_z, claw_rise))
            continue
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
