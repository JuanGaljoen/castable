"""RNG-9 CP2 — accent primitive watertight-by-construction (RED).

These pin the RNG-17 bar at accent scale: each primitive (`accent_seat`,
`accent_prong`) must be a SINGLE B-rep body whose RAW STL (no repair) is a
watertight, zero-non-manifold-edge manifold, and two adjacent seats must FUSE
into one such body.

They FAIL today with an ImportError because
`ringcad.geometry.accent_seat` / `accent_prong` do not exist yet — that missing
feature is the RED signal, not a broken test.

Per the RNG-17 reframing, `.solids() == 1` + positive B-rep volume is the
PRIMARY single-body signal and is asserted BEFORE `raw_validate`, so a fuse-count
failure is disambiguated from an exporter/watertight failure. `raw_validate`
(tests/conftest.py) routes through `to_stl_bytes` WITHOUT `validate_and_repair`.
"""
from __future__ import annotations

import pytest
from build123d import Location, Pos

from ringcad.geometry.accent_prong import accent_prong
from ringcad.geometry.accent_seat import accent_seat
from ringcad.mesh_validator import MIN_WALL_MM

# Halo schema ranges: halo_stone_diameter 0.9-2.5 (accent_r = dia/2),
# halo_stone_height 0.8-3.0. Grid the corners + a mid.
DIAMETERS = (0.9, 1.3, 2.5)
HEIGHTS = (0.8, 1.2, 3.0)


def _assert_castable(result, label: str) -> None:
    """Copied from tests/test_geometry_watertight.py — the RNG-17 raw bar."""
    assert result.body_count == 1, (
        f"{label}: body_count={result.body_count} (want 1)"
    )
    assert result.non_manifold_edges == 0, (
        f"{label}: non_manifold_edges={result.non_manifold_edges} (want 0)"
    )
    assert result.is_watertight, f"{label}: raw mesh is not watertight"


@pytest.mark.parametrize("dia", DIAMETERS)
@pytest.mark.parametrize("height", HEIGHTS)
def test_accent_seat_single_body_and_watertight(raw_validate, dia, height):
    """CP2-1: an accent_seat over the in-range band is one positive-volume B-rep
    body whose raw STL is a single watertight manifold."""
    accent_r = dia / 2
    solid = accent_seat(accent_r, height, Location())
    label = f"accent_seat(dia={dia}, h={height})"
    assert len(solid.solids()) == 1, f"{label}: expected exactly one B-rep body"
    assert solid.volume > 0, f"{label}: non-positive B-rep volume"
    _assert_castable(raw_validate(solid), label)


def test_accent_prong_watertight_at_min(raw_validate):
    """CP2-2a: at the schema MINIMUM (dia 0.9 / height 0.8) an accent_prong is a
    single watertight solid. Watertightness ONLY — no tip-floor assertion here
    (the min tip is legitimately allowed to sit at the floor; CP2-2b covers it)."""
    accent_r, height = 0.9 / 2, 0.8
    solid = accent_prong(accent_r, height, Location())
    label = "accent_prong(min: dia=0.9, h=0.8)"
    assert len(solid.solids()) == 1, f"{label}: expected exactly one B-rep body"
    assert solid.volume > 0, f"{label}: non-positive B-rep volume"
    _assert_castable(raw_validate(solid), label)


def test_accent_seat_adjacency_fuses_single_watertight(raw_validate):
    """CP2-4: two accent_seat beads with real volumetric bead overlap fuse into a
    single watertight manifold (an adjacency smoke for CP3's ring placement).

    Beads are centered (2*bearing_r - 0.3) apart — a 0.3mm interpenetration well
    above the fuse epsilon — so `fuse` must return exactly one body."""
    dia, height = 1.3, 1.2
    accent_r = dia / 2
    collar_tr = max(MIN_WALL_MM / 2, 0.35)
    bearing_r = max(accent_r, collar_tr + 0.05)
    spacing = 2 * bearing_r - 0.3

    a = accent_seat(accent_r, height, Location())
    b = accent_seat(accent_r, height, Pos(spacing, 0, 0))
    fused = a.fuse(b)

    label = f"accent_seat x2 fused (spacing={spacing:.3f})"
    assert len(fused.solids()) == 1, (
        f"{label}: fuse produced {len(fused.solids())} bodies (want 1)"
    )
    _assert_castable(raw_validate(fused), label)
