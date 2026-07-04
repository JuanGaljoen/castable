"""RNG-9 CP2 — accent castability self-checks + isolation (RED).

`check_accent_seat` / `check_accent_prong` probe the REAL produced geometry and
return `[]` in-range or a structured `Violation` (single-sourced MIN_WALL_MM /
MIN_PRONG_TIP_MM) when starved. Unlike the center `check_*` (which section
against GLOBAL planes because every center module shares one fixed placement),
the accent checks take an arbitrary `loc` and must be placement-invariant.

These FAIL today with an ImportError: `check_accent_seat` / `check_accent_prong`
do not exist in `ringcad.geometry._castability` yet — that is the RED signal.

The starved cases feed deliberately-thin REAL solids (no mocks) through the real
check to prove it reads geometry rather than returning a null slice.
"""
from __future__ import annotations

import pytest
from build123d import Align, Box, Cylinder, Location, Pos, Rot

from ringcad.geometry._castability import check_accent_prong, check_accent_seat
from ringcad.geometry.accent_prong import accent_prong
from ringcad.geometry.accent_seat import accent_seat
from ringcad.geometry.module import ARCHETYPES, MODULES

DIAMETERS = (0.9, 1.3, 2.5)
HEIGHTS = (0.8, 1.2, 3.0)

# Location(), a pure translation, an OFF-AXIS tilt (tilts the prong +Z axis so a
# broken global-axis check can't trivially pass), and a compound placement.
LOCS = [
    Location(),
    Pos(20, 5, -3),
    Rot(30, 0, 0),
    Pos(20, 5, -3) * Rot(30, 15, 0),
]


# ---------------------------------------------------------------- CP2-2b
@pytest.mark.parametrize("dia", DIAMETERS)
@pytest.mark.parametrize("height", HEIGHTS)
def test_accent_prong_tip_floor_in_band(dia, height):
    """CP2-2b: across the in-range band the built prong tip is >= floor by
    construction, so check_accent_prong returns []."""
    accent_r = dia / 2
    solid = accent_prong(accent_r, height, Location())
    assert check_accent_prong(solid, accent_r, height, Location()) == [], (
        f"in-range accent_prong(dia={dia}, h={height}) unexpectedly flagged"
    )


# ---------------------------------------------------------------- CP2-3 in-range invariance
def test_accent_seat_check_invariant_in_range():
    """CP2-3: an in-range accent_seat returns the same [] verdict at every loc."""
    accent_r, height = 1.3 / 2, 1.2
    for loc in LOCS:
        solid = accent_seat(accent_r, height, loc)
        assert check_accent_seat(solid, accent_r, height, loc) == [], (
            f"in-range accent_seat flagged at loc={loc}"
        )


def test_accent_prong_check_invariant_in_range():
    """CP2-3: an in-range accent_prong returns the same [] verdict at every loc."""
    accent_r, height = 1.3 / 2, 1.2
    for loc in LOCS:
        solid = accent_prong(accent_r, height, loc)
        assert check_accent_prong(solid, accent_r, height, loc) == [], (
            f"in-range accent_prong flagged at loc={loc}"
        )


# ---------------------------------------------------------------- CP2-3 starved + invariance
def test_accent_seat_starved_violation_invariant():
    """CP2-3: a seat whose wall is driven below MIN_WALL yields a named Violation
    (field halo.halo_stone_height) identically at every loc, with actual_mm equal
    across locs within 1e-3 — proving the check reads real, placement-corrected
    geometry, not a null slice."""
    accent_r, height = 1.3 / 2, 1.2
    # 0.4mm-thin local slab (< MIN_WALL 0.8); XZ section reads the 0.4 thickness.
    starved_local = Box(0.4, 5.0, 5.0)

    actuals = []
    for loc in LOCS:
        placed = loc * starved_local
        vs = check_accent_seat(placed, accent_r, height, loc)
        assert len(vs) == 1, f"expected exactly one Violation at loc={loc}, got {vs}"
        assert vs[0].field == "halo.halo_stone_height", (
            f"wrong field at loc={loc}: {vs[0].field}"
        )
        actuals.append(vs[0].actual_mm)

    spread = max(actuals) - min(actuals)
    assert spread < 1e-3, f"actual_mm not placement-invariant: {actuals}"


def test_accent_prong_starved_violation_invariant():
    """CP2-3: a prong tip driven below MIN_PRONG_TIP yields a named Violation
    (field halo.halo_stone_diameter) identically at every loc, with actual_mm
    equal across locs within 1e-3."""
    accent_r, height = 1.3 / 2, 2.0
    # 0.4mm-diameter local shaft along +Z (< MIN_PRONG_TIP 0.7). The tip probe
    # sits 0.2*height below the top and reads the 0.4 diameter.
    starved_local = Cylinder(
        0.2, 2.0, align=(Align.CENTER, Align.CENTER, Align.MIN)
    )

    actuals = []
    for loc in LOCS:
        placed = loc * starved_local
        vs = check_accent_prong(placed, accent_r, height, loc)
        assert len(vs) == 1, f"expected exactly one Violation at loc={loc}, got {vs}"
        assert vs[0].field == "halo.halo_stone_diameter", (
            f"wrong field at loc={loc}: {vs[0].field}"
        )
        actuals.append(vs[0].actual_mm)

    spread = max(actuals) - min(actuals)
    assert spread < 1e-3, f"actual_mm not placement-invariant: {actuals}"


# ---------------------------------------------------------------- CP2-5 isolation
def test_accent_builders_absent_from_every_archetype():
    """CP2-5: no ARCHETYPES module list references the accent builders."""
    for name, mods in ARCHETYPES.items():
        assert "accent_seat" not in mods, f"accent_seat wired into archetype {name!r}"
        assert "accent_prong" not in mods, f"accent_prong wired into archetype {name!r}"


def test_accent_builders_not_registered_as_modules():
    """CP2-5: the accent builders are NOT top-level MODULES entries (they are
    caller-placed primitives, not archetype modules)."""
    assert "accent_seat" not in MODULES
    assert "accent_prong" not in MODULES


def test_accent_primitives_importable():
    """CP2-5: import smoke — builders and checks are importable callables."""
    assert callable(accent_seat)
    assert callable(accent_prong)
    assert callable(check_accent_seat)
    assert callable(check_accent_prong)
