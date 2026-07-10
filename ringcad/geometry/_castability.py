"""Per-module in-kernel castability self-checks (RNG-16 AC4).

Each `check_*(solid, spec, clamps) -> list[Violation]` probes the *actual*
build123d geometry a module produced (not the spec fields) against the lost-wax
casting floors. Limits are single-sourced from `ringcad.mesh_validator`
(MIN_WALL_MM / MIN_PRONG_TIP_MM) and the structured `Violation` is reused from
`ringcad.ringspec` — never redefined, never a hardcoded literal.

These self-checks AUGMENT the post-geometry `validate_and_repair` mesh gate;
they do not replace it.
"""
from __future__ import annotations

from build123d import Location, Plane, Rot

from ringcad.mesh_validator import MIN_PRONG_TIP_MM, MIN_WALL_MM
from ringcad.ringspec import RingSpec, Violation

from ._common import MIN_WALL, placement
from .accent_prong import accent_prong
from .accent_seat import accent_seat
from .gallery import RAIL_MINOR
from .halo import RAIL_OVERLAP
from .side_stone import _accent_angles, _accent_loc, _wall, _wall_span
from .trilogy import _side_locs


def _section_sizes(solid, plane: Plane) -> list:
    """Bounding-box sizes of every face of `solid` cut by `plane`.

    When `plane` misses the solid's bounds, `intersect` returns None; a check
    must measure nothing (return []) rather than crash on `.faces()`.
    """
    section = solid.intersect(plane)
    return [f.bounding_box().size for f in section.faces()] if section else []


def _min_nonzero(size) -> float | None:
    """Smallest non-zero dimension of a bounding-box size Vector."""
    dims = [d for d in (size.X, size.Y, size.Z) if d > 1e-9]
    return min(dims) if dims else None


def check_shank(solid, spec: RingSpec, clamps: dict) -> list[Violation]:
    """Radial band wall via an XZ section through the ring's top/bottom."""
    radial = [s.X for s in _section_sizes(solid, Plane.XZ) if s.X > 1e-9]
    if not radial:
        return []
    wall = min(radial)
    if wall < MIN_WALL_MM:
        return [Violation(
            code="min_wall",
            field="shank.band_thickness",
            message=f"Shank radial wall {wall:.3f}mm is below the "
            f"{MIN_WALL_MM}mm minimum wall thickness for lost-wax casting.",
            limit_mm=MIN_WALL_MM,
            actual_mm=wall,
        )]
    return []


def check_seat(solid, spec: RingSpec, clamps: dict) -> list[Violation]:
    """Seat-collar tube thickness via an XZ section through the torus."""
    sizes = [_min_nonzero(s) for s in _section_sizes(solid, Plane.XZ)]
    sizes = [s for s in sizes if s is not None]
    if not sizes:
        return []
    wall = min(sizes)
    if wall < MIN_WALL_MM:
        return [Violation(
            code="min_wall",
            field="setting.setting_height",
            message=f"Seat collar tube {wall:.3f}mm is below the "
            f"{MIN_WALL_MM}mm minimum wall thickness for lost-wax casting.",
            limit_mm=MIN_WALL_MM,
            actual_mm=wall,
        )]
    return []


def check_prong_setting(solid, spec: RingSpec, clamps: dict) -> list[Violation]:
    """Prong-tip feature size via a section just below the claw tips.

    Claws point along the global +X head axis; section perpendicular to it a
    short way below the tips and read the smallest claw cross-section.
    """
    bb = solid.bounding_box()
    sizes = [_min_nonzero(s)
             for s in _section_sizes(solid, Plane.YZ.offset(bb.max.X - 0.3))]
    sizes = [s for s in sizes if s is not None]
    if not sizes:
        return []
    tip = min(sizes)
    if tip < MIN_PRONG_TIP_MM:
        return [Violation(
            code="min_prong_tip",
            field="setting.prong_count",
            message=f"Prong-tip feature {tip:.3f}mm is below the "
            f"{MIN_PRONG_TIP_MM}mm minimum prong-tip diameter.",
            limit_mm=MIN_PRONG_TIP_MM,
            actual_mm=tip,
        )]
    return []


def check_accent_seat(
    solid, accent_r: float, height: float, loc: Location
) -> list[Violation]:
    """Accent-seat collar wall via an XZ section in the LOCAL frame.

    Undo the caller's rigid `loc` (`loc.inverse() * solid`) so the check reads
    placement-corrected geometry, then section the collar tube in the canonical
    XZ plane. Placement-invariant by construction.
    """
    local = loc.inverse() * solid
    sizes = [_min_nonzero(s) for s in _section_sizes(local, Plane.XZ)]
    sizes = [s for s in sizes if s is not None]
    if not sizes:
        return []
    wall = min(sizes)
    if wall < MIN_WALL_MM:
        return [Violation(
            code="min_wall",
            field="halo.halo_stone_height",
            message=f"Accent-seat collar wall {wall:.3f}mm is below the "
            f"{MIN_WALL_MM}mm minimum wall thickness for lost-wax casting.",
            limit_mm=MIN_WALL_MM,
            actual_mm=wall,
        )]
    return []


def check_accent_prong(
    solid, accent_r: float, height: float, loc: Location
) -> list[Violation]:
    """Accent-prong tip feature via a section just below the tip, LOCAL frame.

    Undo `loc`, then section perpendicular to local +Z at `0.2*height` below the
    functional tip (the full-diameter shaft top at z=height, NOT the rounded dome
    apex at bb.max.Z) and read the smallest tip cross-section. Placement-invariant
    by construction.
    """
    local = loc.inverse() * solid
    bb = local.bounding_box()
    plane = Plane.XY.offset(bb.min.Z + 0.8 * height)
    sizes = [_min_nonzero(s) for s in _section_sizes(local, plane)]
    sizes = [s for s in sizes if s is not None]
    if not sizes:
        return []
    tip = min(sizes)
    if tip < MIN_PRONG_TIP_MM:
        return [Violation(
            code="min_prong_tip",
            field="halo.halo_stone_diameter",
            message=f"Accent-prong tip {tip:.3f}mm is below the "
            f"{MIN_PRONG_TIP_MM}mm minimum prong-tip diameter.",
            limit_mm=MIN_PRONG_TIP_MM,
            actual_mm=tip,
        )]
    return []


def check_gallery(solid, spec: RingSpec, clamps: dict) -> list[Violation]:
    """Gallery rail radial wall via a diametral XZ section, LOCAL frame.

    The halo module's `_check`. Reconstruct the local +Z frame by undoing the
    derived halo placement (`placement(clamps).inverse() * solid`), section the
    fused halo in the canonical XZ plane, and keep only the rail-tube
    cross-sections (bbox center at radius ~= R AND z ~= rail_z, both re-derived
    from the spec). Excludes the hub (near axis), bridges (mid radius), accent
    seats (higher z) and prong shafts (start above rail_z). Placement-invariant.
    """
    if getattr(spec, "archetype", None) != "halo" or getattr(
        spec, "halo", None
    ) is None:
        return []
    local = placement(clamps).inverse() * solid
    accent_r = spec.halo.halo_stone_diameter / 2
    ring_r = clamps["stone_r"] + spec.halo.halo_gap + accent_r
    depth = max(0.5 * spec.halo.halo_stone_height, MIN_WALL)
    rail_top_z = clamps["ring_z"] - depth + RAIL_OVERLAP
    rail_z = rail_top_z - RAIL_MINOR

    section = local.intersect(Plane.XZ)
    if section is None:
        return []
    walls: list[float] = []
    for f in section.faces():
        bb = f.bounding_box()
        cx = (bb.min.X + bb.max.X) / 2
        cz = (bb.min.Z + bb.max.Z) / 2
        if abs(abs(cx) - ring_r) < RAIL_MINOR and abs(cz - rail_z) < RAIL_MINOR:
            w = _min_nonzero(bb.size)
            if w is not None:
                walls.append(w)
    if not walls:
        return []
    wall = min(walls)
    if wall < MIN_WALL_MM:
        return [Violation(
            code="min_wall",
            field="setting.setting_height",
            message=f"Gallery rail wall {wall:.3f}mm is below the "
            f"{MIN_WALL_MM}mm minimum wall thickness for lost-wax casting.",
            limit_mm=MIN_WALL_MM,
            actual_mm=wall,
        )]
    return []


def check_trilogy(solid, spec: RingSpec, clamps: dict) -> list[Violation]:
    """Both side settings' accent floors, LOCAL frame per side (RNG-10 CP2).

    The trilogy module's `_check`. Reuses `check_accent_seat`/
    `check_accent_prong` over both sides at the shared `trilogy._side_locs`
    positions -- the same real construction `trilogy._side_parts` uses, so
    build and check can never drift apart. Unlike `check_gallery` (which
    sections the fused compound directly, filtering by absolute position),
    the accent checks derive their probe plane from the SOLID's OWN bounding
    box, which is only meaningful for an isolated leaf -- against the fused
    multi-accent `solid` it would read the whole compound's extent instead of
    one prong's. So each accent is rebuilt in isolation at its real location
    before checking; this is the same deterministic geometry `trilogy()`
    fuses, just probed pre-fuse.
    """
    if getattr(spec, "archetype", None) != "trilogy" or getattr(
        spec, "trilogy", None
    ) is None:
        return []
    side_r = spec.trilogy.side_stone_diameter / 2
    height = spec.trilogy.side_stone_height
    violations: list[Violation] = []
    for sign in (-1.0, 1.0):
        seat_loc, prong_locs = _side_locs(spec, clamps, sign)
        seat_solid = accent_seat(side_r, height, seat_loc)
        violations += check_accent_seat(seat_solid, side_r, height, seat_loc)
        for prong_loc in prong_locs:
            prong_solid = accent_prong(side_r, height, prong_loc)
            violations += check_accent_prong(prong_solid, side_r, height, prong_loc)
    return violations


def _check_wall(wall_solid, lo_deg: float) -> list[Violation]:
    """Channel-wall rail tube thickness via the wall's own flush starting
    cross-section.

    A partial-angle `Torus` (`side_stone._wall`) sweeps from ring-angle 0, so
    its tube's minor circle at the START of the sweep lies flush in a plane
    through the Z-axis -- undo the wall's own `Rot(0, 0, lo_deg)` placement to
    bring that flush cross-section back onto the canonical `Plane.XZ`, the
    same axis-aligned convention every other check here uses. (A section at
    an arbitrary rotated angle would still cut a true circle, but measuring
    it via a GLOBAL-axis bounding box under-reads its diameter, since the
    circle is tilted relative to X/Y/Z.)
    """
    local = Rot(0, 0, -lo_deg) * wall_solid
    sizes = [_min_nonzero(s) for s in _section_sizes(local, Plane.XZ)]
    sizes = [s for s in sizes if s is not None]
    if not sizes:
        return []
    wall = min(sizes)
    if wall < MIN_WALL_MM:
        return [Violation(
            code="min_wall",
            field="side_stone.accent_stone_diameter",
            message=f"Channel-wall rail {wall:.3f}mm is below the "
            f"{MIN_WALL_MM}mm minimum wall thickness for lost-wax casting.",
            limit_mm=MIN_WALL_MM,
            actual_mm=wall,
        )]
    return []


def check_side_stone(solid, spec: RingSpec, clamps: dict) -> list[Violation]:
    """Both shoulders' accent-seat floors + channel-wall floors (RNG-11 CP2).

    The side_stone module's `_check`. Mirrors `check_trilogy`: each accent
    seat is rebuilt in isolation at its real `side_stone._accent_loc` before
    `check_accent_seat` (the solid's own bbox is only meaningful for an
    isolated leaf, not the fused multi-accent compound), and each channel-wall
    rail is rebuilt at its real span before `_check_wall`. Uses the same
    `side_stone` construction helpers `side_stone_parts` uses, so build and
    check can never drift apart.
    """
    if getattr(spec, "archetype", None) != "side_stone" or getattr(
        spec, "side_stone", None
    ) is None:
        return []
    ss = spec.side_stone
    accent_r = ss.accent_stone_diameter / 2
    height = ss.accent_stone_height
    violations: list[Violation] = []
    for sign in (-1.0, 1.0):
        for angle in _accent_angles(spec, clamps, sign):
            loc = _accent_loc(clamps, angle)
            seat_solid = accent_seat(accent_r, height, loc)
            violations += check_accent_seat(seat_solid, accent_r, height, loc)
        lo, hi = _wall_span(spec, clamps, sign)
        z = clamps["bw"] / 2
        for wz in (z, -z):
            wall_solid = _wall(clamps, lo, hi, wz)
            violations += _check_wall(wall_solid, lo)
    return violations


def check_bezel(solid, spec: RingSpec, clamps: dict) -> list[Violation]:
    """Bezel-collar radial wall via the annulus in an upper cross-axis section.

    The collar axis is the global +X head axis; section the pure-annulus region
    above the base and read wall = outer_radius - inner_radius from the two
    circular edges.
    """
    bb = solid.bounding_box()
    x = bb.max.X - 0.30 * (bb.max.X - bb.min.X)
    radii: list[float] = []
    for f in solid.intersect(Plane.YZ.offset(x)).faces():
        for e in f.edges():
            try:
                radii.append(e.radius)
            except Exception:
                pass
    if len(radii) < 2:
        return []
    wall = max(radii) - min(radii)
    if wall < MIN_WALL_MM:
        return [Violation(
            code="min_wall",
            field="setting.setting_height",
            message=f"Bezel collar wall {wall:.3f}mm is below the "
            f"{MIN_WALL_MM}mm minimum wall thickness for lost-wax casting.",
            limit_mm=MIN_WALL_MM,
            actual_mm=wall,
        )]
    return []
