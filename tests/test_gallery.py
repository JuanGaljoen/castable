"""RNG-9 CP3 — reusable `gallery` primitive (RED).

CP3-1: `gallery(ring_r, rail_top_z, hub_r, ...)` is the connective understructure
for elevated settings — a 360° rail + radial bridges + central hub fused into ONE
watertight solid, PARAMETRIC (not halo-hardcoded) so RNG-10 can reuse it. Its
in-kernel rail wall must clear the 0.8mm min-wall floor by construction, and the
builder must stay a plain builder (NOT a registered MODULE / ARCHETYPES entry).

These FAIL today with an ImportError because `ringcad.geometry.gallery` does not
exist yet — that missing feature is the RED signal, not a broken test. Per the
RNG-17 reframing, `.solids() == 1` + positive B-rep volume is asserted BEFORE
`raw_validate` (tests/conftest.py routes through `to_stl_bytes` WITHOUT
`validate_and_repair`), so a fuse-count failure is disambiguated from a
watertightness failure.
"""
from __future__ import annotations

import pytest
from build123d import Location, Plane, Pos, Rot

from ringcad.geometry.gallery import RAIL_MINOR, gallery
from ringcad.geometry.module import ARCHETYPES, MODULES
from ringcad.mesh_validator import MIN_WALL_MM

# (ring_r, rail_top_z, hub_r): the golden halo-derived config plus off-halo
# values, to prove the builder is parametric rather than halo-tuned.
GALLERY_GRID = [
    (4.4, 2.4, 0.88),   # golden halo-derived (R, rail_top_z, hub_r)
    (6.0, 2.0, 1.0),
    (8.0, 3.0, 1.5),
    (3.0, 1.5, 0.6),
]


def _assert_castable(result, label: str) -> None:
    """The RNG-17 raw bar (copied from tests/test_geometry_watertight.py)."""
    assert result.body_count == 1, (
        f"{label}: body_count={result.body_count} (want 1)"
    )
    assert result.non_manifold_edges == 0, (
        f"{label}: non_manifold_edges={result.non_manifold_edges} (want 0)"
    )
    assert result.is_watertight, f"{label}: raw mesh is not watertight"


def _rail_wall(solid, ring_r, rail_z, rail_minor):
    """Radial wall of the rail tube via a diametral XZ section.

    Isolates the two rail-tube cross-sections (bbox center at radius ~= ring_r
    AND z ~= rail_z), excluding the hub (near axis) and bridges (mid radius);
    returns the smallest non-zero cross-section dimension (= 2*rail_minor)."""
    section = solid.intersect(Plane.XZ)
    if section is None:
        return None
    walls = []
    for f in section.faces():
        bb = f.bounding_box()
        cx = (bb.min.X + bb.max.X) / 2
        cz = (bb.min.Z + bb.max.Z) / 2
        if abs(abs(cx) - ring_r) < rail_minor and abs(cz - rail_z) < rail_minor:
            dims = [d for d in (bb.size.X, bb.size.Y, bb.size.Z) if d > 1e-9]
            if dims:
                walls.append(min(dims))
    return min(walls) if walls else None


@pytest.mark.parametrize("ring_r,rail_top_z,hub_r", GALLERY_GRID)
def test_gallery_single_body_and_watertight(raw_validate, ring_r, rail_top_z, hub_r):
    """CP3-1: a gallery over the grid is one positive-volume B-rep body whose raw
    STL is a single watertight manifold."""
    solid = gallery(ring_r, rail_top_z, hub_r)
    label = f"gallery(ring_r={ring_r}, rail_top_z={rail_top_z}, hub_r={hub_r})"
    assert len(solid.solids()) == 1, f"{label}: expected exactly one B-rep body"
    assert solid.volume > 0, f"{label}: non-positive B-rep volume"
    _assert_castable(raw_validate(solid), label)


def test_gallery_reusable_standalone(raw_validate):
    """CP3-1: a NON-halo config placed at an OFF-AXIS loc is still one watertight
    body — proves the builder is parametric AND placement-agnostic (RNG-10 reuse).
    """
    loc = Pos(20, 5, -3) * Rot(30, 15, 0)
    solid = gallery(ring_r=6.0, rail_top_z=2.0, hub_r=1.0, loc=loc)
    label = "gallery(standalone non-halo, off-axis loc)"
    assert len(solid.solids()) == 1, f"{label}: expected exactly one B-rep body"
    assert solid.volume > 0, f"{label}: non-positive B-rep volume"
    _assert_castable(raw_validate(solid), label)


def test_gallery_rail_meets_wall_floor():
    """CP3-1: an in-range gallery rail wall is >= MIN_WALL by construction; a
    deliberately sub-floor rail_minor=0.3 build yields a rail wall < MIN_WALL,
    proving the rail thickness is a real, measurable geometric feature."""
    ring_r, rail_top_z, hub_r = 6.0, 2.0, 1.0

    ok = gallery(ring_r, rail_top_z, hub_r)
    wall_ok = _rail_wall(ok, ring_r, rail_top_z - RAIL_MINOR, RAIL_MINOR)
    assert wall_ok is not None, "in-range rail tube not found in XZ section"
    assert wall_ok >= MIN_WALL_MM, f"in-range rail wall {wall_ok:.3f} < MIN_WALL"

    thin = gallery(ring_r, rail_top_z, hub_r, rail_minor=0.3)
    wall_thin = _rail_wall(thin, ring_r, rail_top_z - 0.3, 0.3)
    assert wall_thin is not None, "sub-floor rail tube not found in XZ section"
    assert wall_thin < MIN_WALL_MM, (
        f"sub-floor rail wall {wall_thin:.3f} unexpectedly >= MIN_WALL"
    )


def test_gallery_absent_from_modules():
    """CP3-1: `gallery` is a reusable BUILDER, not a composable MODULE — it is
    absent from MODULES and from every ARCHETYPES module list."""
    assert "gallery" not in MODULES
    for name, mods in ARCHETYPES.items():
        assert "gallery" not in mods, f"gallery wired into archetype {name!r}"
