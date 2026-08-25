"""Shared geometry helpers for the build123d solitaire (RNG-15).

Faithful port of the arithmetic in `spikes/rng13/b123d_solitaire.py`. Casting
constants are imported from `ringcad.mesh_validator` (single source of truth),
not re-declared. Clamps, the band cross-section, and the claw primitives live
here so the shank / prong_setting / seat modules share one copy.
"""
from __future__ import annotations

import math
from typing import Mapping

from build123d import (
    Align, Cone, Cylinder, Ellipse, Location, Plane, Pos, Rot, Vector, loft,
)

from ringcad.mesh_validator import MIN_PRONG_TIP_MM, MIN_WALL_MM
from ringcad.ringspec import RingSpec, to_params
from ringcad.ringspec.models import SHANK_THICKNESS_TAPER, SHANK_WIDTH_TAPER

from .outline import outline_for

# Re-exported under the historic name; the schema owns the value so the
# castability checks derive `head_r` identically (docs/adr/0002).
SHANK_TAPER = SHANK_WIDTH_TAPER
NA = 96  # sections around the ring (matches the spike)


def _head_t(a_deg: float) -> float:
    return ((1 + math.cos(math.radians(a_deg))) / 2) ** 1.5


def _lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def _clamps(
    p: Mapping[str, object],
    taper: float = SHANK_TAPER,
    t_taper: float = SHANK_THICKNESS_TAPER,
) -> dict:
    id_c = max(float(p["inner_diameter"]), 5.0)
    bt_c = max(float(p["band_thickness"]), MIN_WALL_MM)
    bw_c = max(float(p["band_width"]), MIN_WALL_MM)
    sd_c = max(float(p["stone_diameter"]), 1.0)
    gh_c = max(float(p["setting_height"]), MIN_WALL_MM)
    taper = max(taper, 1.0)
    t_taper = max(t_taper, 1.0)
    inner_r = id_c / 2
    return {
        "inner_r": inner_r,
        "bt": bt_c,
        "bw": bw_c,
        "stone_r": sd_c / 2,
        "gh": gh_c,
        "taper": taper,        # WIDTH flare toward the head
        "t_taper": t_taper,    # thickness rise toward the head (near-flat)
        # `head_r` is the band's outer radius AT THE HEAD, so it follows the
        # thickness taper. `placement()` welds every setting at `head_r - 0.4`;
        # if these two disagree the setting floats clear of the band.
        "head_r": inner_r + bt_c * t_taper,
        "ring_z": gh_c * 0.5,
        "claw_rise": gh_c * 0.5,
    }


# The side-stone band is FLAT by construction (specs/RNG-11.md): channel/
# side-stone accents are traditionally set along a straight shoulder, not up a
# tapered shank (the taper is a solitaire feature that flares the shank to cradle
# the centre stone). A flat band also makes the accent row's outer surface a
# constant radius, so the seats/walls sit ON the surface instead of buried inside
# the taper. Intrinsic to the archetype, not a user knob.
FLAT_TAPER = 1.0


def clamps(spec: RingSpec) -> dict:
    """Derive the casting clamps for a RingSpec (with `prong_n` and the centre
    stone's `outline` resolved).

    `stone_r` is retained as the SHORT-axis half-width (unchanged meaning for a
    round stone). Modules that place geometry around the girdle should read
    `outline` instead; `stone_r` remains only for scale-derived values such as
    peg and hub radii, which are not girdle-following.
    """
    p = to_params(spec)
    flat = getattr(spec, "archetype", None) == "side_stone"
    taper = FLAT_TAPER if flat else SHANK_TAPER
    # A flat band is flat on BOTH axes — the side-stone row needs a constant
    # outer radius for its seats and rails to sit ON the surface (RNG-11).
    t_taper = FLAT_TAPER if flat else SHANK_THICKNESS_TAPER
    c = _clamps(p, taper, t_taper)
    pc = int(p["prong_count"])
    c["prong_n"] = pc if pc in (4, 6) else 4
    stones = getattr(spec, "stones", None)
    c["outline"] = outline_for(
        getattr(stones, "shape", "round"),
        c["stone_r"],
        getattr(stones, "length_ratio", 1.0),
    )
    return c


# How far the setting frame sits INSIDE the band's outer surface at the head, so
# the setting is welded into metal rather than balanced on it. Named because
# `trilogy._side_loc` needs the same radius while decoupling its own tilt.
HEAD_INSET = 0.4


def placement(c: dict) -> Location:
    """Local +Z setting frame laid onto the global +X head axis (the spike's
    `place` transform). Shared so peg, claws and seat torus land identically."""
    return Pos(c["head_r"] - HEAD_INSET, 0, 0) * Rot(0, 90, 0)


def _band_section(c: dict, a_deg: float):
    """One oval cross-section face at ring angle `a` (deg)."""
    r = math.radians(a_deg)
    t = _head_t(a_deg)
    # Width flares toward the head; thickness only rises slightly. Real shanks
    # taper in width (docs/jewelry-design-principles.md) — one factor on both
    # axes gave a band 3.4mm wide AND 3.06mm thick at the head.
    th = _lerp(c["bt"], c["bt"] * c["t_taper"], t)
    w = _lerp(c["bw"], c["bw"] * c["taper"], t)
    rc = c["inner_r"] + th / 2
    origin = Vector(rc * math.cos(r), rc * math.sin(r), 0)
    x_dir = Vector(math.cos(r), math.sin(r), 0)            # radial
    z_dir = Vector(-math.sin(r), math.cos(r), 0)           # sweep tangent
    return Plane(origin=origin, x_dir=x_dir, z_dir=z_dir) * Ellipse(th / 2, w / 2)


def band(c: dict):
    """Tapered oval-section shank, pairwise-lofted and fused into one solid."""
    secs = [_band_section(c, i * 360.0 / NA) for i in range(NA + 1)]
    wedges = [loft([secs[i], secs[i + 1]]) for i in range(NA)]
    return wedges[0].fuse(*wedges[1:])


def _rot_between(a: Vector, b: Vector) -> Location:
    a, b = a.normalized(), b.normalized()
    dot = max(-1.0, min(1.0, a.dot(b)))
    ang = math.degrees(math.acos(dot))
    if ang < 1e-6:
        return Location()
    if ang > 180 - 1e-6:
        return Rot(180, 0, 0)
    axis = a.cross(b).normalized()
    return Location((0, 0, 0), (axis.X, axis.Y, axis.Z), ang)


def body_solid(v1, r1, v2, r2):
    """Cone/cylinder body of a claw segment (no end caps)."""
    axis = v2 - v1
    length = axis.length
    rot = _rot_between(Vector(0, 0, 1), axis.normalized())
    align = (Align.CENTER, Align.CENTER, Align.MIN)
    body = Cylinder(r1, length, align=align) if abs(r1 - r2) < 1e-6 \
        else Cone(r1, r2, length, align=align)
    return Pos(v1) * (rot * body)


# Re-export casting constants under the spike's local names for porting clarity.
MIN_WALL = MIN_WALL_MM
MIN_PRONG_TIP = MIN_PRONG_TIP_MM

# Section radius of the seat collar, and so the half-height of the seat plate.
# Shared because `prong_setting`'s V-cup rises out of that plate and has to
# start at its underside: two copies of this number would drift the first time
# one moved, which is the failure docs/adr/0002 is about.
SEAT_COLLAR_R = max(MIN_WALL_MM / 2, 0.45)

# Volumetric overlap for accent-primitive fuses: >> OCCT Precision::Confusion
# (clean single watertight B-rep body) yet << MIN_WALL (no castability impact).
ACCENT_FUSE_EPS = 0.05
