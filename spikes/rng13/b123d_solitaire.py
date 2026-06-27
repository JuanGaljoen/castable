"""build123d port of the solitaire (RNG-13 parity spike).

Faithful B-rep reproduction of scad/solitaire.scad using the same 7 params and
the same casting clamps. Structure mirrors the SCAD modules:

  band()    tapered oval-section shank, built by lofting oval sections around
            the ring (the B-rep analog of the SCAD swept polyhedron)
  gallery() small convergence peg under the basket
  seat()    open seat ring (torus) at the girdle
  prongs()  N claw wires, each a chain of tapered capsules + a tip bead

Everything fuses into one solid. Orientation matches the SCAD: finger axis = Z,
setting points along +X.
"""
from __future__ import annotations

import math
from typing import Mapping

from build123d import (
    Align, Cone, Ellipse, Location, Plane, Pos, Rot, Sphere,
    Torus, Vector, loft,
)

MIN_WALL = 0.8
MIN_PRONG_TIP = 0.7
SHANK_TAPER = 1.7
NA = 96  # sections around the ring (matches SCAD RES_A at $fn=64 → ~141; 96 is plenty)


def _head_t(a_deg: float) -> float:
    return ((1 + math.cos(math.radians(a_deg))) / 2) ** 1.5


def _lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def _clamps(p: Mapping[str, object]) -> dict:
    id_c = max(float(p["inner_diameter"]), 5.0)
    bt_c = max(float(p["band_thickness"]), MIN_WALL)
    bw_c = max(float(p["band_width"]), MIN_WALL)
    sd_c = max(float(p["stone_diameter"]), 1.0)
    gh_c = max(float(p["setting_height"]), MIN_WALL)
    taper = max(SHANK_TAPER, 1.0)
    inner_r = id_c / 2
    return {
        "inner_r": inner_r,
        "bt": bt_c,
        "bw": bw_c,
        "stone_r": sd_c / 2,
        "gh": gh_c,
        "taper": taper,
        "head_r": inner_r + bt_c * taper,
        "ring_z": gh_c * 0.5,
        "claw_rise": gh_c * 0.5,
    }


def _band_section(c: dict, a_deg: float):
    """One oval cross-section face at ring angle `a` (deg). The section's plane
    normal is the sweep tangent, so the ellipse lies in the (radial, axial-Z)
    plane — getting this wrong collapses the section into a flat disk and the
    loft returns zero volume."""
    r = math.radians(a_deg)
    t = _head_t(a_deg)
    th = _lerp(c["bt"], c["bt"] * c["taper"], t)
    w = _lerp(c["bw"], c["bw"] * c["taper"], t)
    rc = c["inner_r"] + th / 2
    origin = Vector(rc * math.cos(r), rc * math.sin(r), 0)
    x_dir = Vector(math.cos(r), math.sin(r), 0)            # radial
    z_dir = Vector(-math.sin(r), math.cos(r), 0)           # sweep tangent (normal)
    return Plane(origin=origin, x_dir=x_dir, z_dir=z_dir) * Ellipse(th / 2, w / 2)


def _band(c: dict):
    """Tapered oval-section shank, built as pairwise lofts between adjacent
    sections fused into one solid — the B-rep analog of the SCAD swept
    polyhedron. (OCCT can't loft a closed loop, nor multisection-sweep the
    varying ellipses, in one call; segment-by-segment is the robust path.)"""
    secs = [_band_section(c, i * 360.0 / NA) for i in range(NA + 1)]
    wedges = [loft([secs[i], secs[i + 1]]) for i in range(NA)]
    return wedges[0].fuse(*wedges[1:])


def _body_solid(v1, r1, v2, r2):
    """The cone/cylinder body of a claw segment (no end caps — node spheres are
    placed once per node so consecutive segments don't leave coincident caps)."""
    from build123d import Cylinder
    axis = v2 - v1
    length = axis.length
    rot = _rot_between(Vector(0, 0, 1), axis.normalized())
    align = (Align.CENTER, Align.CENTER, Align.MIN)
    body = Cylinder(r1, length, align=align) if abs(r1 - r2) < 1e-6 \
        else Cone(r1, r2, length, align=align)
    return Pos(v1) * (rot * body)


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


def _setting_solids(c: dict) -> list:
    """Gallery peg + seat ring + prong wires as a flat list of solids, authored
    in a local +Z frame then laid onto global +X. Returned unfused so the whole
    ring fuses in a single boolean (avoids seams from incremental unions)."""
    stone_r, ring_z, claw_rise = c["stone_r"], c["ring_z"], c["claw_rise"]
    wire_r = max(MIN_WALL / 2 + 0.1, 0.5)
    tip_r = max(MIN_PRONG_TIP / 2, 0.4)
    base_r = max(stone_r * 0.20, MIN_WALL)
    collar_tr = max(MIN_WALL / 2, 0.45)

    local = []
    peg_h = max(ring_z * 0.4, 1.0) + 0.4
    local.append(Cone(base_r + wire_r, base_r, peg_h,
                      align=(Align.CENTER, Align.CENTER, Align.MIN)))
    local.append(Pos(0, 0, ring_z) * Torus(stone_r, collar_tr))
    # Claw nodes (one sphere each) + segment bodies between them.
    A, B = Vector(base_r, 0, 0), Vector(stone_r, 0, ring_z)
    C = Vector(stone_r, 0, ring_z + claw_rise * 0.55)
    D = Vector(stone_r * 0.88, 0, ring_z + claw_rise)
    nodes = [(A, wire_r), (B, wire_r), (C, wire_r * 0.92), (D, tip_r * 1.45)]
    edges = [(A, wire_r, B, wire_r), (B, wire_r, C, wire_r * 0.92),
             (C, wire_r * 0.92, D, tip_r)]
    n = int(c["prong_n"])
    for i in range(n):
        rot = Rot(0, 0, i * 360.0 / n)
        for v, r in nodes:
            local.append(rot * (Pos(*v) * Sphere(r)))
        for v1, r1, v2, r2 in edges:
            local.append(rot * _body_solid(v1, r1, v2, r2))
    place = Pos(c["head_r"] - 0.4, 0, 0) * Rot(0, 90, 0)
    return [place * s for s in local]


def build_solitaire(p: Mapping[str, object]):
    """RingSpec-7 (solitaire) → one watertight build123d solid."""
    c = _clamps(p)
    pc = int(p["prong_count"])
    c["prong_n"] = pc if pc in (4, 6) else 4
    solids = [_band(c), *_setting_solids(c)]
    return solids[0].fuse(*solids[1:])
