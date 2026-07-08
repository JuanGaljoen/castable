"""RNG-9 CP3 — halo/gallery castability self-checks (RED).

CP3-4: `check_gallery(solid, spec, clamps)` (the `MODULES["halo"]._check`) probes
the REAL rail geometry and returns `[]` in-range or a single single-sourced
`min_wall` `Violation` when the rail is starved. Like the CP2 accent checks it is
placement-invariant, but it reconstructs the LOCAL frame via `placement(clamps)`
(the derived halo placement), not an arbitrary caller loc. The accent self-checks
(reused from CP2) must also stay clean across the halo band — the shared prong
tip legitimately sits at the 0.7mm floor (allowed; the check flags `< floor`).

These FAIL today with an ImportError because `check_gallery` /
`ringcad.geometry.gallery` / `ringcad.geometry.halo` do not exist yet — that
missing feature is the RED signal, not a broken test.
"""
from __future__ import annotations

from build123d import Location

from ringcad.geometry._castability import (
    check_accent_prong,
    check_accent_seat,
    check_gallery,
)
from ringcad.geometry._common import clamps, placement
from ringcad.geometry.accent_prong import accent_prong
from ringcad.geometry.accent_seat import accent_seat
from ringcad.geometry.gallery import gallery
from ringcad.geometry.halo import halo
from ringcad.mesh_validator import MIN_WALL_MM
from ringcad.ringspec import Halo, HaloSpec, Setting, Shank, Stones

# rail-top <-> seat-well interpenetration (halo.py RAIL_OVERLAP; plan constant).
RAIL_OVERLAP = 0.2

# Curated castable band (mirrors tests/test_halo_watertight.py::BAND) — accent
# sizes only, for the placement-invariant accent self-checks.
BAND = [
    (0.9, 8, 0.3, 0.8, 6.5, 3.0),
    (1.3, 14, 0.5, 1.2, 6.5, 6.0),
    (2.5, 8, 1.5, 3.0, 10.0, 6.0),
    (1.3, 24, 0.5, 1.2, 10.0, 6.0),
    (0.9, 24, 0.3, 0.8, 10.0, 3.0),
    (2.5, 14, 1.5, 3.0, 6.5, 3.0),
    (1.3, 8, 1.5, 0.8, 6.5, 6.0),
    (0.9, 14, 0.5, 3.0, 10.0, 3.0),
]


def _halo_spec(*, inner_diameter=16.5, h_dia=1.3, h_count=14, h_gap=0.5,
               h_height=1.2, stone_dia=6.5, setting_h=6.0):
    return HaloSpec(
        shank=Shank(inner_diameter=inner_diameter, band_width=2.2,
                    band_thickness=1.9),
        setting=Setting(prong_count=6, setting_height=setting_h),
        stones=Stones(stone_diameter=stone_dia, stone_height=4.0),
        halo=Halo(halo_stone_diameter=h_dia, halo_stone_count=h_count,
                  halo_gap=h_gap, halo_stone_height=h_height),
    )


def _halo_gallery(spec, c, **over):
    """A gallery built at the halo placement, mirroring halo.py's derivation, so
    the check can be exercised on a halo-placed rail independent of the module."""
    accent_r = spec.halo.halo_stone_diameter / 2
    ring_r = c["stone_r"] + spec.halo.halo_gap + accent_r
    seat_z = c["ring_z"]
    depth = max(0.5 * spec.halo.halo_stone_height, MIN_WALL_MM)
    rail_top_z = seat_z - depth + RAIL_OVERLAP
    hub_r = max(c["stone_r"] * 0.20, MIN_WALL_MM) * 1.1
    return gallery(ring_r, rail_top_z, hub_r, loc=placement(c), **over)


def test_check_gallery_clean_on_golden():
    """CP3-4: the golden halo's rail clears the min-wall floor by construction."""
    spec = _halo_spec()
    c = clamps(spec)
    assert check_gallery(halo(spec, c), spec, c) == []


def test_check_gallery_signature():
    """CP3-4: `check_gallery` returns a list and every Violation limit is the
    single-sourced MIN_WALL_MM (no hardcoded floor)."""
    spec = _halo_spec()
    c = clamps(spec)
    result = check_gallery(halo(spec, c), spec, c)
    assert isinstance(result, list)
    assert all(v.limit_mm == MIN_WALL_MM for v in result)


def test_check_gallery_starved():
    """CP3-4: a halo-placed gallery whose rail_minor is driven below the floor
    yields exactly one `min_wall` Violation with the single-sourced limit —
    proving the check reads real geometry, not a null slice."""
    spec = _halo_spec()
    c = clamps(spec)
    starved = _halo_gallery(spec, c, rail_minor=0.3)
    vs = check_gallery(starved, spec, c)
    assert len(vs) == 1, f"expected exactly one Violation, got {vs}"
    assert vs[0].code == "min_wall"
    assert vs[0].limit_mm == MIN_WALL_MM


def test_check_gallery_invariant_off_axis():
    """CP3-4: an in-range gallery placed at two DIFFERENT center placements (two
    specs whose head axis differs via inner_diameter) reconstructs to the same
    local frame and returns the same [] verdict — placement-invariance."""
    spec_a = _halo_spec(inner_diameter=16.5)
    spec_b = _halo_spec(inner_diameter=22.0)
    ca, cb = clamps(spec_a), clamps(spec_b)
    ga = _halo_gallery(spec_a, ca)
    gb = _halo_gallery(spec_b, cb)
    va = check_gallery(ga, spec_a, ca)
    vb = check_gallery(gb, spec_b, cb)
    assert va == [] and vb == [], f"in-range gallery flagged: {va} / {vb}"


def test_accents_clean_across_band():
    """CP3-4: across the curated band the reused CP2 accent self-checks return no
    violations — accent sizes are castable and the shared-prong tip sits at (not
    below) the 0.7mm floor."""
    for combo in BAND:
        h_dia, _h_count, _h_gap, h_height, _sd, _gh = combo
        accent_r = h_dia / 2
        seat = accent_seat(accent_r, h_height, Location())
        assert check_accent_seat(seat, accent_r, h_height, Location()) == [], (
            f"accent_seat flagged for band combo {combo}"
        )
        prong = accent_prong(accent_r, h_height, Location())
        assert check_accent_prong(prong, accent_r, h_height, Location()) == [], (
            f"accent_prong flagged for band combo {combo}"
        )
