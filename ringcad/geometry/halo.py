"""halo() — the halo composition module (RNG-9 CP3).

Rings N `accent_seat` beads along the centre stone's outline, grown outward by
`halo_gap + accent_r`, with N shared prongs at the gap midpoints, all on a
`gallery`, fused into ONE watertight body. Accents are spaced by ARC LENGTH so an
oval halo does not bunch them at the tips (RNG-23); on a circle that is the same
as the original `2*pi*k/N`.

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

from build123d import (
    Align, Cone, Cylinder, Face, Location, Pos, Sphere, extrude,
)

from ringcad.ringspec.models import (
    HALO_PLATE_INNER_BITE, HALO_PLATE_RIM, HALO_WELL_BACK_RATIO,
    halo_seat_depth,
)

from ._common import (
    ACCENT_FUSE_EPS, MIN_PRONG_TIP, MIN_WALL, clamps, placement,
)
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


# --- CP4 plate constants ----------------------------------------------------
# Bead radius: the small prong settings between adjacent stones in the sketch.
# Held at the casting floor -- these are the finest features on the ring.
BEAD_R = MIN_PRONG_TIP / 2
# How far a bead's centre sits BELOW the plate top, so it is welded volumetrically
# into the plate rather than balanced tangent on it (ADR-0001 prefer-overlap).
BEAD_SINK = BEAD_R * 0.5
# How far the well's crown cylinder rises past the plate top, and how far the
# bore runs past the plate bottom, so it breaks BOTH surfaces cleanly instead of
# landing tangent to either.
WELL_OVERSHOOT = 0.4



def _plate(ring, inner, accent_r: float, top_z: float, thickness: float, loc):
    """The halo body: ONE continuous annular plate (docs/reference/halo.png).

    From the centre-stone opening out to the accent ring plus `HALO_PLATE_RIM`,
    which gives the crisp outer edge the sketch shows. Built as a solid disc
    minus the centre opening -- two extrusions and one boolean -- rather than a
    face with a hole, because a disc difference is the more robust of the two in
    OCCT and follows the outline for an oval halo unchanged.

    Replaces RNG-9's ring of N `accent_seat` collars. Those were torus tubes
    pinned at `max(MIN_WALL/2, 0.35)`, so on a 1.2mm accent the metal was two
    thirds the stone's own diameter and read as lumpy tubing; being at the
    casting floor, no tuning could make them finer. A plate's metal is instead
    whatever the bores leave.
    """
    outer = ring.expanded(accent_r + HALO_PLATE_RIM)
    # The opening reaches INSIDE the centre girdle so the centre claws, which
    # rise through this plate's height at exactly that radius, are embedded in
    # it. That weld is what carries the halo -- see `halo_parts`.
    disc = extrude(Face(outer.wire()), amount=thickness)
    hole = extrude(Face(inner.expanded(-HALO_PLATE_INNER_BITE).wire()),
                   amount=thickness)
    return loc * Pos(0, 0, top_z - thickness) * (disc - hole)


def _bead(point, top_z: float, loc):
    """One small prong setting: a bead at the junction between adjacent stones,
    sunk into the plate so the fuse is volumetric."""
    return loc * Pos(point.X, point.Y, top_z - BEAD_SINK) * Sphere(BEAD_R)


def _well(point, accent_r: float, depth: float, top_z: float, loc):
    """One accent seat, BORED rather than built: a pavilion cone below the
    girdle plus a crown cylinder breaking out through the plate top.

    The RNG-19 CP3 move, second customer. Cutting the stone out of the metal
    means the web between adjacent seats is what the bores leave, and the seat
    is the stone's own negative -- which is exactly what a metal-only render of
    a semi-mount should show.
    """
    pavilion = depth
    back_r = accent_r * HALO_WELL_BACK_RATIO
    # ONE tapered cone, extended past the plate top rather than a cone capped by
    # a crown cylinder. A two-piece tool put its own junction exactly on the
    # plate's top plane; OCCT resolved that coplanar case by leaving a lid, so
    # every seat became a sealed internal cavity — 15 enclosed voids in a solid
    # that still reported watertight (docs/adr/0005, caught by mesh BODY COUNT).
    slope = (accent_r - back_r) / pavilion
    top_r = accent_r + slope * WELL_OVERSHOOT
    bore = Cone(
        back_r, top_r, pavilion + WELL_OVERSHOOT,
        align=(Align.CENTER, Align.CENTER, Align.MAX),
    )
    return loc * Pos(point.X, point.Y, top_z + WELL_OVERSHOOT) * bore


def _halo_geometry(spec, c: dict):
    """Shared derivation for `halo_parts` and `halo_cuts`, so the plate and the
    bores it receives can never be computed from drifting numbers."""
    accent_r = spec.halo.halo_stone_diameter / 2
    height = spec.halo.halo_stone_height
    n = spec.halo.halo_stone_count

    ring = c["outline"].expanded(spec.halo.halo_gap + accent_r)
    R = c["stone_r"] + spec.halo.halo_gap + accent_r
    seat_z = c["ring_z"]
    # Seat depth is clamped by the room the setting actually leaves (see
    # `halo_seat_depth`); the plate is that plus its floor.
    seat_depth = halo_seat_depth(height, seat_z, MIN_WALL)
    depth = seat_depth + MIN_WALL
    rail_top_z = seat_z - depth + RAIL_OVERLAP
    hub_r = max(c["stone_r"] * 0.20, MIN_WALL) * 1.1

    return {
        "accent_r": accent_r, "height": height, "n": n, "ring": ring, "R": R,
        "seat_z": seat_z, "plate_t": depth, "seat_depth": seat_depth, "rail_top_z": rail_top_z,
        "hub_r": hub_r, "place": placement(c),
        # Spaced by ARC LENGTH, not by angle: on an ellipse equal angles crowd
        # the accents toward the tips (RNG-23). Beads bisect each gap.
        "seats": ring.angles_by_arc(n),
        "beads": ring.angles_by_arc(n, offset=0.5),
    }


def halo_parts(spec, c: dict | None = None) -> list:
    """The halo's METAL leaves un-fused: [gallery, plate, *beads].

    `compose` fuses these alongside the centre modules' leaves in ONE general
    fuse, then applies `halo_cuts`. A single general fuse over loose parts is
    robust where iteratively fusing pre-fused COMPOUNDS is not: OCCT silently
    drops a boolean when a heavy pre-fused body meets the centre's swept claws,
    but resolves cleanly when everything enters the same fuse (RNG-17 risk #1).

    The plate's bottom sits `RAIL_OVERLAP` inside the gallery rail tube, so the
    rail welds the whole halo body in one -- the same weld RNG-9's individual
    accent bearings used, now to a single plate instead of N collars.
    """
    c = c if c is not None else clamps(spec)
    g = _halo_geometry(spec, c)
    plate = _plate(g["ring"], c["outline"], g["accent_r"], g["seat_z"],
                   g["plate_t"], g["place"])
    # Bore the seats HERE, into the bare plate, rather than declaring them as
    # module cuts. Two reasons, both found the hard way:
    #   - the beads must NOT be cut. Set nearly touching, the bores would trim
    #     each bead to a sliver; boring first lets the beads be fused on top,
    #     overhanging the seat rims exactly as a set bead does.
    #   - the bores must not meet the gallery. Cutting after the gallery joined
    #     put cone against rail torus, which would not tessellate.
    plate = plate.cut(*_wells(spec, c, g))
    # NO gallery. RNG-9 needed one because N loose collars had nothing holding
    # them together or to the centre; the plate is now a single ring, and it
    # hangs off the CENTRE CLAWS, which pass through its own height and are
    # embedded by `HALO_PLATE_INNER_BITE`. A gallery on top of that is a second
    # skeleton -- it read as a hub-and-spokes cross slung beneath the halo.
    parts = [plate]
    for theta in g["beads"]:
        point, _ = g["ring"].frame_at(theta)
        parts.append(_bead(point, g["seat_z"], g["place"]))
    return parts


def _wells(spec, c: dict, g: dict) -> list:
    """The accent seats as cutting tools, in the plate's own frame."""
    out = []
    for theta in g["seats"]:
        point, _ = g["ring"].frame_at(theta)
        out.append(_well(point, g["accent_r"], g["seat_depth"], g["seat_z"],
                         g["place"]))
    return out


def halo_cuts(spec, c: dict | None = None) -> list:
    """Kept for tests/introspection: the seats bored into the plate. NOT
    declared to `compose` -- see `halo_parts` for why they are cut locally."""
    c = c if c is not None else clamps(spec)
    return _wells(spec, c, _halo_geometry(spec, c))


def halo(spec, c: dict | None = None):
    """Plate + beads on a gallery, seats bored -> one solid.

    Fuses `halo_parts` then subtracts `halo_cuts` (the standalone builder + fast
    loop contract). `compose` bypasses this and handles leaves and cuts itself,
    for the cross-module robustness `halo_parts` documents.
    """
    parts = halo_parts(spec, c)
    return parts[0].fuse(*parts[1:])
