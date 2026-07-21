"""gallery() — the reusable understructure for elevated settings (RNG-9 CP3).

A `gallery` ties a raised setting (halo, and later trilogy / cathedral) to the
shank/center as a single watertight manifold: a continuous 360 degree `Torus`
rail beneath the setting, `n_bridges` radial strut cylinders, and a central hub
cylinder, all fused into ONE body. It is a *builder*, not a registered MODULE —
it carries no spec slice; the consumer derives its three geometric params
(`ring_r`, `rail_top_z`, `hub_r`) and supplies a rigid placement `loc`.

Authored in a LOCAL +Z frame (setting axis = local +Z) with `loc` applied LAST
(`loc * local`), matching the CP2 accent-primitive contract. Every part
volumetrically interpenetrates its neighbour (bridge ends embedded `_OV` into
hub and rail) so the single `fuse` yields one watertight B-rep body by
construction — no tangency, no `.clean()` needed.
"""
from __future__ import annotations

import math

from build123d import Align, Box, Cylinder, Location, Pos, Rot

from ._common import ACCENT_FUSE_EPS, MIN_WALL
from .outline import RoundOutline

# Rail tube minor radius -> rail wall = 2*RAIL_MINOR ~= 1.2mm (> 0.8 floor).
RAIL_MINOR = max(MIN_WALL * 0.75, 0.6)
# Bridge half-width -> bridge wall = 2*BRIDGE_R ~= 1.0mm (> 0.8 floor).
BRIDGE_R = max(MIN_WALL * 0.6, 0.5)
# Bridge-end embed depth into hub / rail (>> OCCT confusion, << MIN_WALL).
_OV = ACCENT_FUSE_EPS * 4


def gallery(ring_r: float, rail_top_z: float, hub_r: float, *,
            hub_bottom_z: float = 0.0, n_bridges: int = 4,
            rail_minor: float = RAIL_MINOR, bridge_r: float = BRIDGE_R,
            outline=None, loc: Location = Location()):
    """One fused gallery solid, placed by rigid `loc`.

    Args:
        ring_r: radius of the rail circle (mm). Ignored when `outline` is given.
        outline: optional StoneOutline the rail should FOLLOW instead of a circle
            (RNG-23) -- an oval centre stone needs an oval gallery under its halo.
            Omitted means a circle of radius `ring_r`, which is what
            `RoundOutline(ring_r)` builds anyway, so round output is unchanged.
        rail_top_z: local +Z of the rail tube's top (where seats seat).
        hub_r: central hub cylinder radius (mm); must overlap the center peg.
        hub_bottom_z: local +Z of the hub base (default 0, the shank plane).
        n_bridges: radial box struts tying the rail to the hub.
        rail_minor: rail tube minor radius (drives rail wall thickness).
        bridge_r: bridge strut half-width (drives bridge wall thickness).
        loc: rigid Location (rot+trans) applied last.
    """
    ring = outline if outline is not None else RoundOutline(ring_r)
    rail_z = rail_top_z - rail_minor
    # RoundOutline.tube() IS `Torus(ring_r, rail_minor)`, so the circular gallery
    # is bit-identical to pre-RNG-23.
    rail = Pos(0, 0, rail_z) * ring.tube(rail_minor)
    hub = Pos(0, 0, hub_bottom_z) * Cylinder(
        hub_r, rail_top_z - hub_bottom_z,
        align=(Align.CENTER, Align.CENTER, Align.MIN),
    )

    # Bridges are BOX struts, not cylinders: a box's flat faces cut the curved
    # torus tube along clean seams, where a thin cylinder grazes it tangentially
    # and leaves sliver/degenerate triangles (open STL edges). The inner end
    # embeds `_OV` into the hub; the outer end punches PAST the tube centre
    # (radius `ring_r`) into its far half so the whole strut is buried in the
    # tube core. Angles are half-stepped so no strut lies in a symmetry plane.
    # On a non-circular rail each strut has its own reach, so the outer end is
    # derived per bridge from where the rail actually is at that angle.
    inner = hub_r - _OV
    bridges = []
    for theta in ring.angles_by_arc(n_bridges, offset=0.5):
        point, _ = ring.frame_at(theta)
        # The geometric bearing of the point, which for an ellipse is NOT the
        # parametric angle; the strut must be rotated to where the rail IS.
        bearing = math.degrees(math.atan2(point.Y, point.X))
        outer = math.hypot(point.X, point.Y) + rail_minor * 0.5
        length = outer - inner
        strut = Pos(inner + length / 2, 0, rail_z) * Box(
            length, 2 * bridge_r, 2 * bridge_r
        )
        bridges.append(Rot(0, 0, bearing) * strut)

    g = rail.fuse(hub, *bridges)
    return loc * g
